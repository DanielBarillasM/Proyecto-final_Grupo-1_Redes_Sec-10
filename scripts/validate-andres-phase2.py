
from __future__ import annotations

import datetime as dt
import ipaddress
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DNS = ROOT / "services" / "dns"
WEB = ROOT / "services" / "intranet"
TF = ROOT / "infra" / "terraform"
EVIDENCE = ROOT / "evidence" / "fase-2" / "dns" / "andres-validation.txt"

DNS_IP = "10.10.0.164"
INTRANET_IP = "10.10.0.165"
DATACENTER = ipaddress.ip_network("10.10.0.160/28")
AUTHORIZED = {
    ipaddress.ip_network("10.10.0.64/26"),   # Ventas
    ipaddress.ip_network("10.10.0.128/27"),  # TI
    ipaddress.ip_network("10.10.0.160/28"),  # Data Center
    ipaddress.ip_network("10.10.0.176/28"),  # Administración
}
FORBIDDEN = {
    "Visitas": ipaddress.ip_network("10.10.0.0/26"),
    "DMZ": ipaddress.ip_network("10.10.0.192/27"),
}

results: list[tuple[bool, str]] = []


def check(ok: bool, message: str) -> None:
    results.append((ok, message))


def networks(text: str) -> set[ipaddress.IPv4Network]:
    found = re.findall(r"\b(\d{1,3}(?:\.\d{1,3}){3}/\d{1,2})\b", text)
    return {ipaddress.ip_network(c) for c in found}


def run(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def main() -> int:
    named = (DNS / "named.conf").read_text(encoding="utf-8")
    zone = (DNS / "db.rednova.internal").read_text(encoding="utf-8")
    reverse = (DNS / "db.10.10.0").read_text(encoding="utf-8")
    nginx = (WEB / "nginx.conf").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")
    variables = (TF / "variables.tf").read_text(encoding="utf-8")
    services = (TF / "services.tf").read_text(encoding="utf-8")
    security = (TF / "phase2-security.tf").read_text(encoding="utf-8")

    # Direccionamiento.
    check(ipaddress.ip_address(DNS_IP) in DATACENTER, f"DNS {DNS_IP} pertenece a Data Center {DATACENTER}")
    check(ipaddress.ip_address(INTRANET_IP) in DATACENTER, f"Intranet {INTRANET_IP} pertenece a Data Center {DATACENTER}")
    check(f'dns            = "{DNS_IP}"' in variables, "variables.tf asigna la IP del DNS")
    check(f'intranet       = "{INTRANET_IP}"' in variables, "variables.tf asigna la IP de la intranet")
    check('default     = "rednova.internal"' in variables, "variables.tf usa el dominio rednova.internal")

    # BIND9.
    acl = re.search(r'acl "redes_autorizadas" \{(.*?)\};', named, re.S)
    acl_nets = networks(acl.group(1)) if acl else set()
    check(acl_nets == AUTHORIZED, "ACL de BIND9 = Ventas, TI, Data Center y Administración")
    for label, net in FORBIDDEN.items():
        check(not any(net.overlaps(a) for a in acl_nets), f"ACL de BIND9 excluye {label} {net}")
    check(f"listen-on port 53   {{ 127.0.0.1; {DNS_IP}; }};" in named, "BIND9 escucha solo en loopback y la IP del DNS")
    check("allow-transfer      { none; };" in named, "Transferencias de zona deshabilitadas")
    check("forwarders          { 10.10.0.2; };" in named, "Reenvío al resolvedor de la VPC 10.10.0.2")
    check(re.search(rf"^rrhh\s+IN\s+A\s+{re.escape(INTRANET_IP)}", zone, re.M) is not None,
          f"rrhh.rednova.internal A {INTRANET_IP}")
    check(re.search(rf"^ns1\s+IN\s+A\s+{re.escape(DNS_IP)}", zone, re.M) is not None, f"ns1.rednova.internal A {DNS_IP}")
    check(re.search(r"^165\s+IN\s+PTR\s+rrhh\.rednova\.internal\.", reverse, re.M) is not None, "PTR 10.10.0.165 -> rrhh")

    # Nginx.
    allow_nets = {ipaddress.ip_network(c) for c in re.findall(r"allow\s+(\d[\d./]+/\d+);", nginx)}
    check(allow_nets == AUTHORIZED, "allow de Nginx = Ventas, TI, Data Center y Administración")
    check("deny  all;" in nginx, "Nginx termina con deny all")
    check("server_tokens       off;" in nginx, "Nginx oculta su versión")
    check("rrhh.rednova.internal" in nginx and INTRANET_IP in nginx, "server_name incluye el FQDN y la IP")
    check("http://" not in html.replace("http://www.w3.org", "") and "https://" not in html,
          "El HTML no depende de recursos externos")

    # Security Groups de Terraform alineados con las mismas redes.
    for sg in ("dns", "intranet"):
        block = re.search(rf'resource "aws_security_group" "{sg}" \{{(.*?)\n\}}', security, re.S)
        body = block.group(1) if block else ""
        refs = set(re.findall(r"local\.subnets\.(\w+)\.cidr", body))
        check(refs == {"ventas", "ti", "datacenter", "administracion"},
              f"SG {sg}: ingreso solo desde ventas, ti, datacenter y administracion")
        check("0.0.0.0/0" not in body, f"SG {sg}: sin reglas hacia/desde 0.0.0.0/0")
        check("aws_vpc_endpoint.s3" in body, f"SG {sg}: salida HTTPS al prefijo S3 del endpoint")

    check("associate_public_ip_address = false" in services, "EC2 de Data Center sin IP pública")
    check(services.count('http_tokens                 = "required"') == 2, "IMDSv2 obligatorio en DNS e intranet")
    check(services.count("encrypted   = true") == 2, "EBS cifrado en DNS e intranet")

    # Herramientas nativas, si existen.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "etc").mkdir()
        (root / "var" / "named" / "data").mkdir(parents=True)
        shutil.copy(DNS / "named.conf", root / "etc" / "named.conf")
        for z in ("db.rednova.internal", "db.10.10.0"):
            shutil.copy(DNS / z, root / "var" / "named" / z)
        if shutil.which("named-checkconf"):
            ok, out = run(["named-checkconf", "-t", str(root), "-z", "/etc/named.conf"])
            check(ok, "named-checkconf -z: " + (out.replace("\n", " | ") or "OK"))
        else:
            check(True, "named-checkconf no instalado: se omite (se ejecuta en user_data)")
        if shutil.which("named-checkzone"):
            for name, z in (("rednova.internal", "db.rednova.internal"), ("0.10.10.in-addr.arpa", "db.10.10.0")):
                ok, out = run(["named-checkzone", name, str(DNS / z)])
                check(ok, f"named-checkzone {name}: " + out.splitlines()[-1])
        if shutil.which("nginx"):
            conf = root / "nginx.conf"
            conf.write_text(nginx.replace("user nginx;", "# user nginx;").replace("/run/nginx.pid", str(root / "nginx.pid")))
            ok, out = run(["nginx", "-t", "-c", str(conf)])
            check(ok, "nginx -t: " + ("sintaxis correcta" if ok else out))
        else:
            check(True, "nginx no instalado: se omite (se ejecuta en user_data)")

    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    lines = [f"Validación local DNS interno e intranet - {stamp}", ""]
    lines += [f"[{'OK' if ok else 'FALLA'}] {msg}" for ok, msg in results]
    failed = sum(1 for ok, _ in results if not ok)
    lines += ["", f"Resultado: {len(results) - failed} correctas, {failed} fallidas"]
    report = "\n".join(lines) + "\n"
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(report, encoding="utf-8")
    print(report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
