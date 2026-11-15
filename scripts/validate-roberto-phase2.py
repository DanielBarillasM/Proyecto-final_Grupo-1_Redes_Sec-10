"""Valida el bloque de Roberto (web pública, hardening, dominio) sin consultar AWS."""
from __future__ import annotations

import base64
import datetime as dt
import ipaddress
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "infra" / "terraform"
SVC = ROOT / "services"
WEB = SVC / "public-web"
HARD = SVC / "hardening"
EVIDENCE = ROOT / "evidence" / "fase-2" / "public-web" / "roberto-validation.txt"

DMZ = ipaddress.ip_network("10.10.0.192/27")
WEB_IP = "10.10.0.196"
ADMIN_NET = "10.10.0.176/28"

results: list[tuple[bool | None, str]] = []


def check(ok: bool, message: str) -> None:
    results.append((ok, message))


def skip(message: str) -> None:
    results.append((None, message))


def run(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def block(text: str, header: str) -> str:
    """Devuelve el cuerpo de un bloque HCL de primer nivel que empieza en `header`."""
    start = text.find(header)
    if start < 0:
        return ""
    depth, i = 0, text.index("{", start)
    begin = i
    while i < len(text):
        depth += text[i] == "{"
        depth -= text[i] == "}"
        i += 1
        if depth == 0:
            break
    return text[begin:i]


def render_template(tpl: str, values: dict[str, str]) -> str:
    """Render mínimo de templatefile para poder revisar el script resultante."""
    tpl = re.sub(r"^%\{ if enable_https ~\}\n(.*?)^%\{ endif ~\}\n?", r"\1", tpl, flags=re.S | re.M)
    tpl = tpl.replace("%%{", "%{").replace("$${", "${")

    def sub(m: re.Match[str]) -> str:
        expr = m.group(1).strip()
        if expr.startswith("enable_https ?"):
            return "on" if values["enable_https"] == "true" else "off"
        return values[expr]

    return re.sub(r"\$\{([^}]+)\}", sub, tpl)


def main() -> int:
    tf = (TF / "public-web.tf").read_text(encoding="utf-8")
    tpl = (TF / "templates" / "public-web-user-data.tftpl").read_text(encoding="utf-8")
    nginx = (WEB / "nginx.conf").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    hard = (HARD / "hardening.sh").read_text(encoding="utf-8")
    https = (WEB / "enable-https.sh").read_text(encoding="utf-8")
    variables = (TF / "variables.tf").read_text(encoding="utf-8")
    security = (TF / "phase2-security.tf").read_text(encoding="utf-8")
    nacls = (TF / "nacls.tf").read_text(encoding="utf-8")

    # --- Contrato de red --------------------------------------------------
    check(ipaddress.ip_address(WEB_IP) in DMZ, f"Web pública {WEB_IP} pertenece a la DMZ {DMZ}")
    check(f'public_web     = "{WEB_IP}"' in variables, "variables.tf asigna 10.10.0.196 a public_web")
    inst = block(tf, 'resource "aws_instance" "public_web"')
    check(bool(inst), "Existe aws_instance.public_web")
    check('aws_subnet.segments["dmz"].id' in inst, "La EC2 usa la subred DMZ")
    check("local.phase2_service_ips.public_web" in inst, "La EC2 usa local.phase2_service_ips.public_web")
    check("aws_security_group.public_web.id" in inst, "La EC2 usa aws_security_group.public_web")
    check("count = var.enable_phase2_compute ? 1 : 0" in inst, "EC2 condicionada por enable_phase2_compute")
    check("associate_public_ip_address = false" in inst, "Sin IPv4 automática: solo la Elastic IP explícita")
    check('http_tokens                 = "required"' in inst, "IMDSv2 obligatorio")
    check("encrypted   = true" in inst, "EBS cifrado")
    check("var.enable_compute" in inst, "Precondición: requiere enable_compute (llave y bastión)")
    check("var.public_domain != \"\"" in inst, "Precondición: HTTPS exige public_domain")
    eip = block(tf, 'resource "aws_eip" "public_web"')
    check(bool(eip), "Existe aws_eip.public_web")
    check("count = var.enable_phase2_compute ? 1 : 0" in eip, "EIP condicionada por enable_phase2_compute")
    check('Temporary = "true"' in eip and "phase2_tags" in eip, "EIP etiquetada como temporal con DeleteAfter")
    check("aws_internet_gateway.main" in eip, "EIP depende del Internet Gateway")
    check('output "public_web"' in tf and 'output "public_dns_record"' in tf, "Outputs de IP, dominio y registro DNS")
    check(re.search(r'variable\s+"enable_phase2_compute"\s*\{[^}]*default\s*=\s*false', variables, re.S) is not None,
          "enable_phase2_compute = false por defecto")
    check(re.search(r'variable\s+"enable_https"\s*\{[^}]*default\s*=\s*false', variables, re.S) is not None,
          "enable_https = false por defecto")

    # --- Reglas de red que protegen la web (no se modifican; solo se revisan) --
    sg = block(security, 'resource "aws_security_group" "public_web"')
    ssh_blocks = re.findall(r"ingress\s*\{[^{}]*from_port\s*=\s*22[^{}]*\}", sg, re.S)
    check(bool(ssh_blocks) and all("0.0.0.0/0" not in b and "aws_security_group.bastion.id" in b for b in ssh_blocks),
          "SG public_web: SSH solo desde el bastión (nunca 0.0.0.0/0)")
    check(re.search(r"from_port\s*=\s*80[^{}]*0\.0\.0\.0/0", sg, re.S) is not None, "SG public_web: HTTP público")
    check("var.enable_https" in sg, "SG public_web: 443 solo cuando enable_https = true")
    dmz_nacl = block(nacls, 'resource "aws_network_acl" "dmz"')
    ssh_rules = re.findall(r"ingress\s*\{[^{}]*to_port\s*=\s*22\s*\}", dmz_nacl, re.S)
    check(bool(ssh_rules) and all("administracion" in r and "0.0.0.0/0" not in r for r in ssh_rules),
          "NACL DMZ: SSH solo desde Administración")
    check(re.search(r'egress\s*\{[^{}]*action\s*=\s*"deny"[^{}]*var\.vpc_cidr', dmz_nacl, re.S) is not None,
          "NACL DMZ: la DMZ no inicia conexiones hacia la VPC (deny antes que Internet)")

    # --- Plantilla user_data ----------------------------------------------
    tpl_call = re.search(r"templatefile\([^,]+,\s*\{(.*?)\n  \}\)", tf, re.S)
    provided = set(re.findall(r"^\s{4}(\w+)\s*=", tpl_call.group(1) if tpl_call else "", re.M))
    used = set(re.findall(r"(?<!\$)\$\{(\w+)", tpl)) - {"enable_https ?"}
    used |= {"enable_https"} if "enable_https" in tpl else set()
    check(used <= provided, f"La plantilla solo usa variables entregadas por Terraform ({sorted(used - provided) or 'ok'})")
    check("filebase64(" in tf and "public-web/index.html" in tf and "hardening/hardening.sh" in tf,
          "Terraform incrusta los archivos versionados en base64")
    check("nginx -t" in tpl and "hardening.sh" in tpl, "user_data valida Nginx y ejecuta el hardening")
    check("BEGIN" not in tpl and "PRIVATE KEY" not in tpl, "user_data sin llaves ni certificados")
    values = {
        "public_domain": "ventas.example.com", "enable_https": "false", "internal_ip": WEB_IP,
        "index_html_b64": base64.b64encode(html.encode()).decode(),
        "nginx_conf_b64": base64.b64encode(nginx.encode()).decode(),
        "hardening_b64": base64.b64encode(hard.encode()).decode(),
    }
    rendered = render_template(tpl, values)
    def bash_check(label: str, content: str) -> None:
        # Se envía por stdin: funciona igual en Linux, macOS y bash de WSL (rutas C:\\ no).
        if not shutil.which("bash"):
            skip(f"bash no disponible: se omite bash -n {label}")
            return
        # Bytes, no texto: en Windows el modo texto convertiría cada \n en \r\n y bash fallaría.
        proc = subprocess.run(["bash", "-n"], input=content.replace("\r\n", "\n").encode("utf-8"),
                              capture_output=True)
        out = (proc.stdout + proc.stderr).decode("utf-8", errors="replace").strip()
        check(proc.returncode == 0, f"bash -n {label}: " + ("sintaxis correcta" if proc.returncode == 0 else out))

    bash_check("user-data.sh", rendered)
    bash_check("hardening.sh", hard)
    bash_check("enable-https.sh", https)
    values["enable_https"] = "true"
    bash_check("user-data con enable_https = true", render_template(tpl, values))

    size = len(rendered.replace("\r\n", "\n").encode("utf-8"))
    check(size <= 15500, f"user_data renderizado = {size} bytes (límite de EC2: 16384; margen mínimo exigido: 15500)")
    crlf = [str(p.relative_to(ROOT)) for p in (WEB / "nginx.conf", WEB / "index.html", HARD / "hardening.sh",
                                                WEB / "enable-https.sh", TF / "templates" / "public-web-user-data.tftpl")
            if b"\r\n" in p.read_bytes()]
    check(not crlf, f"Archivos incrustados en la EC2 con finales de línea LF, no CRLF ({crlf or 'ok'})")

    # --- Nginx -----------------------------------------------------------
    check("server_tokens         off;" in nginx, "Nginx oculta su versión")
    check("__PUBLIC_DOMAIN__" in nginx and "server_name __PUBLIC_DOMAIN__ _;" in nginx,
          "server_name admite el dominio y el acceso por IP")
    check("limit_except GET HEAD { deny all; }" in nginx, "Solo GET y HEAD")
    check("limit_req" in nginx and "limit_conn" in nginx, "Límites de peticiones y conexiones por IP")
    check("location ~ /\\." in nginx, "Archivos ocultos denegados")
    check("listen 80" in nginx and "listen 443" not in nginx, "Nginx base escucha solo en 80 (443 lo agrega certbot)")
    check(not re.search(r"^\s*allow\s", nginx, re.M), "Nginx público no restringe por allow (es una web pública)")
    check("X-Content-Type-Options" in nginx and "Content-Security-Policy" in nginx, "Cabeceras de seguridad presentes")
    check("http://" not in html and "https://" not in html, "El HTML público no depende de recursos externos")

    # --- Hardening -------------------------------------------------------
    check("PasswordAuthentication no" in hard and "PermitRootLogin no" in hard, "SSH: sin contraseñas ni root")
    check("policy drop" in hard and ADMIN_NET in hard, f"nftables: política drop y SSH solo desde {ADMIN_NET}")
    check("nft -c -f" in hard, "nftables se valida antes de cargarse (no corta el acceso)")
    check("tcp_syncookies" in hard and "rp_filter" in hard, "Parámetros de red endurecidos (sysctl)")
    check(not re.search(r"dport\s*22[^\n]*0\.0\.0\.0/0|saddr\s*0\.0\.0\.0/0[^\n]*22", hard), "Firewall del SO sin SSH público")
    check("set -euo pipefail" in hard, "El script falla ante errores")

    # --- Higiene del repositorio -----------------------------------------
    forbidden = [p for p in ROOT.rglob("*") if p.is_file() and ".terraform" not in p.parts and (
        p.suffix in {".pem", ".key", ".tfstate", ".tfplan", ".tfvars"} or p.name.startswith("terraform.tfstate"))]
    check(not forbidden, f"Sin llaves, estados, planes ni .tfvars en el árbol ({[str(f.relative_to(ROOT)) for f in forbidden] or 'ok'})")
    scan_files = [p for p in ROOT.rglob("*") if p.is_file() and p.suffix in {".tf", ".tftpl", ".sh", ".conf", ".html", ".py", ".md", ".tex"}
                  and ".terraform" not in p.parts]
    secret_re = re.compile(r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|AKIA[0-9A-Z]{16}|aws_secret_access_key\s*=")
    leaks = [str(p.relative_to(ROOT)) for p in scan_files if secret_re.search(p.read_text(encoding="utf-8", errors="ignore"))]
    check(not leaks, f"Sin patrones de secretos en el código ({leaks or 'ok'})")
    conflicts = [str(p.relative_to(ROOT)) for p in scan_files
                 if re.search(r"^(<<<<<<< |>>>>>>> )", p.read_text(encoding="utf-8", errors="ignore"), re.M)]
    check(not conflicts, f"Sin marcadores de conflicto de merge ({conflicts or 'ok'})")

    # --- Herramientas nativas, si existen --------------------------------
    if shutil.which("nginx"):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            conf = root / "nginx.conf"
            text = nginx.replace("__PUBLIC_DOMAIN__", "ventas.example.com").replace("user nginx;", "# user nginx;")
            text = text.replace("/run/nginx.pid", str(root / "nginx.pid")).replace("/var/log/nginx/", str(root) + "/")
            text = re.sub(r"include /usr/share/nginx/modules/\*\.conf;", "", text)
            text = text.replace("include       /etc/nginx/mime.types;", "")
            conf.write_text(text, encoding="utf-8")
            ok, out = run(["nginx", "-t", "-c", str(conf)])
            check(ok, "nginx -t: " + ("sintaxis correcta" if ok else out))
    else:
        skip("nginx no instalado: se omite (se ejecuta con 'nginx -t' dentro del user_data)")
    if shutil.which("nft"):
        skip("nft disponible, pero la regla se genera en la instancia; se valida con 'nft -c' en hardening.sh")
    else:
        skip("nft no instalado: se omite (hardening.sh ejecuta 'nft -c' antes de cargar la regla)")
    try:
        import hcl2  # type: ignore

        with (TF / "public-web.tf").open(encoding="utf-8") as handle:
            hcl2.load(handle)
        check(True, "public-web.tf es HCL sintácticamente válido (python-hcl2)")
    except ImportError:
        skip("python-hcl2 no instalado: se omite el análisis HCL (use terraform validate)")
    except Exception as exc:  # noqa: BLE001
        check(False, f"public-web.tf no pudo analizarse como HCL: {exc}")

    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [f"Validación local web pública, hardening y dominio - {stamp}", ""]
    status = {True: "OK", False: "FALLA", None: "OMITIDA"}
    lines += [f"[{status[ok]}] {msg}" for ok, msg in results]
    passed = sum(1 for ok, _ in results if ok is True)
    skipped = sum(1 for ok, _ in results if ok is None)
    failed = sum(1 for ok, _ in results if ok is False)
    lines += ["", f"Resultado: {passed} correctas, {skipped} omitidas, {failed} fallidas"]
    report = "\n".join(lines) + "\n"
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(report, encoding="utf-8")
    print(report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
