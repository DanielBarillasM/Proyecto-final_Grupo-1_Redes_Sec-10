"""Valida el bloque de Genser y la matriz de tráfico de Fase 2 sin consultar AWS.

Además de las comprobaciones estructurales de los clientes de prueba, el script lee los
Security Groups (stateful) y las Network ACL (stateless) directamente de Terraform y evalúa
cada flujo de la matriz del hand-off capa por capa:

    SG de salida del origen -> NACL de salida del origen -> NACL de entrada del destino
    -> SG de entrada del destino -> firewall del SO (nftables, si aplica)
    -> retorno por las NACL (puerto efímero o ICMP echo-reply)

Así se detecta, antes de la ventana AWS, cualquier regla que contradiga la matriz. La
evaluación modela solo lo que Terraform declara; no sustituye las pruebas reales.

Uso:  python scripts/validate-phase2.py
Salida: evidence/fase-2/connectivity/genser-validation.txt; código 1 si algo falla.
"""
from __future__ import annotations

import base64
import datetime as dt
import ipaddress
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TF = ROOT / "infra" / "terraform"
SVC = ROOT / "services"
SCRIPTS = ROOT / "scripts"
EVIDENCE = ROOT / "evidence" / "fase-2" / "connectivity" / "genser-validation.txt"

VPC = ipaddress.ip_network("10.10.0.0/24")
VISITAS_IP, TI_IP = "10.10.0.4", "10.10.0.132"
EPHEMERAL = 40000           # puerto efímero representativo de Linux (32768-60999)
INTERNET_IP = "198.51.100.20"  # equipo cualquiera en Internet (TEST-NET-2)

results: list[tuple[bool | None, str]] = []


def check(ok: bool, message: str) -> None:
    results.append((bool(ok), message))


def skip(message: str) -> None:
    results.append((None, message))


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def block(text: str, header: str) -> str:
    """Cuerpo de un bloque HCL que empieza en `header` (con llaves balanceadas)."""
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


def resources(text: str, kind: str) -> dict[str, str]:
    return {m.group(1): block(text, m.group(0)) for m in re.finditer(rf'resource\s+"{kind}"\s+"(\w+)"', text)}


def rule_blocks(body: str, direction: str) -> list[str]:
    """Reglas inline de primer nivel (dos espacios de sangría); ignora bloques dynamic."""
    return [block(body[m.start():], m.group(0)) for m in re.finditer(rf"(?m)^  {direction} \{{", body)]


def attr(body: str, name: str) -> str | None:
    m = re.search(rf"(?m)^\s*{name}\s*=\s*(\[[^\]]*\]|\"[^\"]*\"|[^\s#]+)", body)
    return m.group(1).strip().strip('"') if m else None


def list_items(value: str | None) -> list[str]:
    if not value:
        return []
    return [x.strip().strip('"') for x in value.strip("[]").replace("\n", ",").split(",") if x.strip()]


# --- Modelo de la red declarada ------------------------------------------------------------
locals_tf = read(TF / "locals.tf")
SUBNETS: dict[str, tuple[ipaddress.IPv4Network, bool]] = {
    m.group(1): (ipaddress.ip_network(m.group(2)), m.group(3) == "true")
    for m in re.finditer(r'(\w+)\s*=\s*\{\s*cidr\s*=\s*"([\d./]+)"\s*public\s*=\s*(true|false)', locals_tf)
}
variables_tf = read(TF / "variables.tf")
ADMIN_CIDR = re.search(r'variable "admin_cidr".*?default\s*=\s*"([\d./]+)"', variables_tf, re.S).group(1)


def resolve_cidr(expr: str) -> ipaddress.IPv4Network | None:
    expr = expr.strip().strip('"')
    m = re.fullmatch(r"local\.subnets\.(\w+)\.cidr", expr)
    if m:
        return SUBNETS[m.group(1)][0]
    if expr == "var.vpc_cidr":
        return VPC
    if expr == "var.admin_cidr":
        return ipaddress.ip_network(ADMIN_CIDR)
    try:
        return ipaddress.ip_network(expr)
    except ValueError:
        return None


@dataclass
class Rule:
    proto: str
    from_port: int
    to_port: int
    cidrs: list[ipaddress.IPv4Network] = field(default_factory=list)
    sgs: list[str] = field(default_factory=list)
    self_ref: bool = False
    action: str = "allow"
    rule_no: int = 0
    icmp_type: int = -1


def to_int(value: str | None, default: int = 0) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def parse_sg(body: str, direction: str) -> list[Rule]:
    rules = []
    for rb in rule_blocks(body, direction):
        rules.append(Rule(
            proto=attr(rb, "protocol") or "-1",
            from_port=to_int(attr(rb, "from_port")), to_port=to_int(attr(rb, "to_port")),
            cidrs=[c for c in (resolve_cidr(x) for x in list_items(attr(rb, "cidr_blocks"))) if c],
            sgs=[re.sub(r"aws_security_group\.(\w+)\.id", r"\1", x) for x in list_items(attr(rb, "security_groups"))],
            self_ref=attr(rb, "self") == "true",
        ))
    return rules


def parse_nacl(body: str, direction: str) -> list[Rule]:
    rules = []
    for rb in rule_blocks(body, direction):
        cidr = resolve_cidr(attr(rb, "cidr_block") or "")
        rules.append(Rule(
            proto=attr(rb, "protocol") or "-1", from_port=to_int(attr(rb, "from_port")),
            to_port=to_int(attr(rb, "to_port")), cidrs=[cidr] if cidr else [],
            action=attr(rb, "action") or "deny", rule_no=to_int(attr(rb, "rule_no")),
            icmp_type=to_int(attr(rb, "icmp_type"), -1),
        ))
    return sorted(rules, key=lambda r: r.rule_no)


all_tf = "\n".join(read(p) for p in sorted(TF.glob("*.tf")))
SG_BODIES = resources(all_tf, "aws_security_group")
SGS = {name: {"ingress": parse_sg(b, "ingress"), "egress": parse_sg(b, "egress")} for name, b in SG_BODIES.items()}
NACL_BODIES = resources(all_tf, "aws_network_acl")
NACLS = {name: {"ingress": parse_nacl(b, "ingress"), "egress": parse_nacl(b, "egress")} for name, b in NACL_BODIES.items()}
SUBNET_NACL: dict[str, str] = {}
for name, b in resources(all_tf, "aws_network_acl_association").items():
    seg = re.search(r'aws_subnet\.segments\["(\w+)"\]', b)
    acl = re.search(r"aws_network_acl\.(\w+)\.id", b)
    if seg and acl:
        SUBNET_NACL[seg.group(1)] = acl.group(1)

INSTANCES = resources(all_tf, "aws_instance")
EIPS = resources(all_tf, "aws_eip")


@dataclass
class Host:
    name: str
    ip: str
    subnet: str | None = None
    sg: str | None = None
    public: bool = False
    hostfw_tcp: set[int] | None = None  # None = sin nftables; set() = solo SSH desde Administración

    @property
    def addr(self) -> ipaddress.IPv4Address:
        return ipaddress.ip_address(self.ip)


def host_from_tf(name: str, resource: str, ip: str, hostfw: set[int] | None = None) -> Host:
    body = INSTANCES.get(resource, "")
    seg = re.search(r'aws_subnet\.segments\["(\w+)"\]', body)
    sg = re.search(r"vpc_security_group_ids\s*=\s*\[aws_security_group\.(\w+)\.id\]", body)
    public = attr(body, "associate_public_ip_address") == "true" or any(
        f"aws_instance.{resource}[0].id" in e for e in EIPS.values())
    return Host(name, ip, seg.group(1) if seg else None, sg.group(1) if sg else None, public, hostfw)


HOSTS = {
    "internet": Host("internet", INTERNET_IP, public=True),
    "operador": Host("operador", ADMIN_CIDR.split("/")[0], public=True),
    "bastion": host_from_tf("bastion", "bastion", "10.10.0.180"),
    "ventas": host_from_tf("ventas", "ventas", "10.10.0.71"),
    "ti": host_from_tf("ti", "ti_client", TI_IP, set()),
    "visitas": host_from_tf("visitas", "visitas_client", VISITAS_IP, set()),
    "dns": host_from_tf("dns", "dns", "10.10.0.164"),
    "intranet": host_from_tf("intranet", "intranet", "10.10.0.165"),
    "web": host_from_tf("web", "public_web", "10.10.0.196", {80}),
}


def sg_allows(rules: list[Rule], peer: Host, this_sg: str, proto: str, port: int, icmp_type: int) -> bool:
    for r in rules:
        if r.proto not in ("-1", proto):
            continue
        if proto in ("tcp", "udp") and r.proto != "-1" and not (r.from_port <= port <= r.to_port):
            continue
        if proto == "icmp" and r.proto == "icmp" and r.from_port not in (-1, icmp_type):
            continue
        if any(peer.addr in c for c in r.cidrs) or (peer.sg and peer.sg in r.sgs) or (r.self_ref and peer.sg == this_sg):
            return True
    return False


def nacl_allows(rules: list[Rule], peer_ip: ipaddress.IPv4Address, proto: str, port: int, icmp_type: int) -> tuple[bool, str]:
    for r in rules:
        if r.proto not in ("-1", proto):
            continue
        if proto in ("tcp", "udp") and r.proto != "-1" and not (r.from_port <= port <= r.to_port):
            continue
        if proto == "icmp" and r.proto == "icmp" and r.icmp_type not in (-1, icmp_type):
            continue
        if any(peer_ip in c for c in r.cidrs):
            return r.action == "allow", f"regla {r.rule_no} {r.action}"
    return False, "regla * deny"


def nacl_of(host: Host) -> str | None:
    return SUBNET_NACL.get(host.subnet) if host.subnet else None


def flow(src: Host, dst: Host, proto: str, port: int = 0) -> tuple[bool, str]:
    """Evalúa un flujo iniciado por src hacia dst. Devuelve (permitido, motivo)."""
    if not src.subnet and dst.subnet and not dst.public:
        return False, "sin ruta: el destino no tiene IPv4 pública"
    if src.subnet and not dst.subnet and not (src.public and SUBNETS[src.subnet][1]):
        return False, "sin ruta: el origen no tiene salida a Internet"
    req_type, rep_type = 8, 0
    reply_port = EPHEMERAL
    if src.sg and not sg_allows(SGS[src.sg]["egress"], dst, src.sg, proto, port, req_type):
        return False, f"SG {src.sg} (salida)"
    same_subnet = src.subnet is not None and src.subnet == dst.subnet
    if not same_subnet:
        if nacl_of(src):
            ok, why = nacl_allows(NACLS[nacl_of(src)]["egress"], dst.addr, proto, port, req_type)
            if not ok:
                return False, f"NACL {nacl_of(src)} salida, {why}"
        if nacl_of(dst):
            ok, why = nacl_allows(NACLS[nacl_of(dst)]["ingress"], src.addr, proto, port, req_type)
            if not ok:
                return False, f"NACL {nacl_of(dst)} entrada, {why}"
    if dst.sg and not sg_allows(SGS[dst.sg]["ingress"], src, dst.sg, proto, port, req_type):
        return False, f"SG {dst.sg} (entrada)"
    if dst.hostfw_tcp is not None and proto in ("tcp", "udp"):
        admin_ok = port == 22 and src.subnet == "administracion"
        if not admin_ok and not (proto == "tcp" and port in dst.hostfw_tcp):
            return False, f"nftables de {dst.name}"
    if not same_subnet:
        rp = rep_type if proto == "icmp" else reply_port
        if nacl_of(dst):
            ok, why = nacl_allows(NACLS[nacl_of(dst)]["egress"], src.addr, proto, rp, rep_type)
            if not ok:
                return False, f"retorno bloqueado: NACL {nacl_of(dst)} salida, {why}"
        if nacl_of(src):
            ok, why = nacl_allows(NACLS[nacl_of(src)]["ingress"], dst.addr, proto, rp, rep_type)
            if not ok:
                return False, f"retorno bloqueado: NACL {nacl_of(src)} entrada, {why}"
    return True, "permitido por todas las capas"


ALLOW, DENY = True, False
H = HOSTS
MATRIX: list[tuple[str, str, Host, Host, str, int, bool]] = [
    ("M01", "Internet -> web DMZ HTTP", H["internet"], H["web"], "tcp", 80, ALLOW),
    ("M02", "Internet -> web DMZ SSH", H["internet"], H["web"], "tcp", 22, DENY),
    ("M03", "Internet -> cliente Visitas SSH", H["internet"], H["visitas"], "tcp", 22, DENY),
    ("M04", "Internet (IP no autorizada) -> bastión SSH", H["internet"], H["bastion"], "tcp", 22, DENY),
    ("M05", "IP administrativa /32 -> bastión SSH", H["operador"], H["bastion"], "tcp", 22, ALLOW),
    ("M06", "Internet -> intranet HTTP", H["internet"], H["intranet"], "tcp", 80, DENY),
    ("M07", "Internet -> TI SSH", H["internet"], H["ti"], "tcp", 22, DENY),
]
for target in ("ventas", "ti", "visitas", "dns", "intranet", "web"):
    MATRIX.append((f"M08-{target}", f"Bastión -> {target} SSH (administración)", H["bastion"], H[target], "tcp", 22, ALLOW))
MATRIX += [
    ("M09a", "Visitas -> Internet HTTPS", H["visitas"], H["internet"], "tcp", 443, ALLOW),
    ("M09b", "Visitas -> Internet HTTP", H["visitas"], H["internet"], "tcp", 80, ALLOW),
    ("M10a", "Visitas -> intranet HTTP", H["visitas"], H["intranet"], "tcp", 80, DENY),
    ("M10b", "Visitas -> DNS interno UDP/53", H["visitas"], H["dns"], "udp", 53, DENY),
    ("M10c", "Visitas -> Ventas ICMP", H["visitas"], H["ventas"], "icmp", 0, DENY),
    ("M10d", "Visitas -> TI SSH", H["visitas"], H["ti"], "tcp", 22, DENY),
    ("M10e", "Visitas -> TI ICMP", H["visitas"], H["ti"], "icmp", 0, DENY),
    ("M10f", "Visitas -> web DMZ por IP privada", H["visitas"], H["web"], "tcp", 80, DENY),
    ("M10g", "Visitas -> bastión SSH", H["visitas"], H["bastion"], "tcp", 22, DENY),
    ("M11a", "TI -> Visitas ICMP", H["ti"], H["visitas"], "icmp", 0, ALLOW),
    ("M11b", "TI -> Ventas ICMP", H["ti"], H["ventas"], "icmp", 0, ALLOW),
    ("M11c", "TI -> Administración ICMP", H["ti"], H["bastion"], "icmp", 0, ALLOW),
    ("M11d", "TI -> DNS ICMP", H["ti"], H["dns"], "icmp", 0, ALLOW),
    ("M11e", "TI -> DNS UDP/53", H["ti"], H["dns"], "udp", 53, ALLOW),
    ("M11f", "TI -> DNS TCP/53", H["ti"], H["dns"], "tcp", 53, ALLOW),
    ("M11g", "TI -> intranet ICMP", H["ti"], H["intranet"], "icmp", 0, ALLOW),
    ("M11h", "TI -> intranet HTTP", H["ti"], H["intranet"], "tcp", 80, ALLOW),
    ("M11i", "TI -> web DMZ ICMP", H["ti"], H["web"], "icmp", 0, ALLOW),
    ("M11j", "TI -> web DMZ HTTP", H["ti"], H["web"], "tcp", 80, ALLOW),
    ("M12a", "Ventas -> TI ICMP", H["ventas"], H["ti"], "icmp", 0, DENY),
    ("M12b", "Ventas -> TI SSH", H["ventas"], H["ti"], "tcp", 22, DENY),
    ("M12c", "Ventas -> TI TCP/8080", H["ventas"], H["ti"], "tcp", 8080, DENY),
    ("M12d", "Data Center (DNS) -> TI SSH", H["dns"], H["ti"], "tcp", 22, DENY),
    ("M12e", "Data Center (intranet) -> TI HTTP", H["intranet"], H["ti"], "tcp", 80, DENY),
    ("M12f", "DMZ -> TI SSH", H["web"], H["ti"], "tcp", 22, DENY),
    ("M12g", "Administración -> TI ICMP (solo se permite SSH administrativo)", H["bastion"], H["ti"], "icmp", 0, DENY),
    ("M13a", "Ventas -> DNS UDP/53", H["ventas"], H["dns"], "udp", 53, ALLOW),
    ("M13b", "Data Center (intranet) -> DNS UDP/53", H["intranet"], H["dns"], "udp", 53, ALLOW),
    ("M13c", "Administración -> DNS UDP/53", H["bastion"], H["dns"], "udp", 53, ALLOW),
    ("M13d", "DMZ -> DNS UDP/53", H["web"], H["dns"], "udp", 53, DENY),
    ("M14a", "Ventas -> intranet HTTP", H["ventas"], H["intranet"], "tcp", 80, ALLOW),
    ("M14b", "Data Center (DNS) -> intranet HTTP", H["dns"], H["intranet"], "tcp", 80, ALLOW),
    ("M14c", "Administración -> intranet HTTP", H["bastion"], H["intranet"], "tcp", 80, ALLOW),
    ("M14d", "DMZ -> intranet HTTP", H["web"], H["intranet"], "tcp", 80, DENY),
    ("M15a", "DMZ -> Ventas ICMP", H["web"], H["ventas"], "icmp", 0, DENY),
    ("M15b", "DMZ -> Ventas SSH", H["web"], H["ventas"], "tcp", 22, DENY),
    ("M15c", "DMZ -> Internet HTTPS (actualizaciones/ACME)", H["web"], H["internet"], "tcp", 443, ALLOW),
]


def render_template(tpl: str, values: dict[str, object]) -> str:
    """Render mínimo de templatefile: directivas %{ if var ~}...%{ endif ~} e interpolaciones."""
    def directive(m: re.Match[str]) -> str:
        return m.group(2) if values[m.group(1)] else ""
    tpl = re.sub(r"^%\{ if (\w+) ~\}\n(.*?)^%\{ endif ~\}\n?", directive, tpl, flags=re.S | re.M)
    tpl = tpl.replace("%%{", "%{").replace("$${", "${")
    return re.sub(r"\$\{(\w+)\}", lambda m: str(values[m.group(1)]), tpl)


def bash_syntax(label: str, content: str) -> None:
    if not shutil.which("bash"):
        skip(f"bash no disponible: se omite bash -n {label}")
        return
    proc = subprocess.run(["bash", "-n"], input=content.replace("\r\n", "\n").encode(), capture_output=True)
    out = (proc.stdout + proc.stderr).decode(errors="replace").strip()
    check(proc.returncode == 0, f"bash -n {label}: " + ("sintaxis correcta" if proc.returncode == 0 else out))


def main() -> int:
    tf = read(TF / "test-clients.tf")
    tpl = read(TF / "templates" / "test-client-user-data.tftpl")
    variables = variables_tf
    hard = read(SVC / "hardening" / "hardening.sh")
    dnsq = read(SVC / "dns" / "dnsquery.py")
    probe = read(SCRIPTS / "phase2-probe.sh")
    ps1 = read(SCRIPTS / "test-phase2.ps1")
    zone = read(SVC / "dns" / "db.rednova.internal")

    # --- Contrato de direcciones --------------------------------------------------------
    check(ipaddress.ip_address(VISITAS_IP) in SUBNETS["visitas"][0], f"Cliente Visitas {VISITAS_IP} pertenece a Visitas")
    check(ipaddress.ip_address(TI_IP) in SUBNETS["ti"][0], f"Cliente TI {TI_IP} pertenece a TI")
    check(f'visitas_client = "{VISITAS_IP}"' in variables and f'ti_client      = "{TI_IP}"' in variables,
          "variables.tf asigna 10.10.0.4 y 10.10.0.132 a los clientes")
    check(re.search(rf"ti-cliente\s+IN\s+A\s+{re.escape(TI_IP)}", zone) is not None,
          "La zona rednova.internal registra ti-cliente -> 10.10.0.132")

    # --- Clientes Terraform -------------------------------------------------------------
    for res, seg, sg, pub in (("visitas_client", "visitas", "visitas_client", "true"), ("ti_client", "ti", "ti", "false")):
        body = INSTANCES.get(res, "")
        check(bool(body), f"Existe aws_instance.{res}")
        check("count = var.enable_phase2_compute ? 1 : 0" in body, f"{res}: condicionado por enable_phase2_compute")
        check(f'aws_subnet.segments["{seg}"].id' in body, f"{res}: subred {seg}")
        check(f"local.phase2_service_ips.{res}" in body, f"{res}: IP desde local.phase2_service_ips.{res}")
        check(f"aws_security_group.{sg}.id" in body, f"{res}: Security Group {sg}")
        check(f"associate_public_ip_address = {pub}" in body, f"{res}: associate_public_ip_address = {pub}")
        check('http_tokens                 = "required"' in body, f"{res}: IMDSv2 obligatorio")
        check("encrypted   = true" in body, f"{res}: EBS cifrado")
        check("condition     = var.enable_compute" in body, f"{res}: precondición enable_compute (llave y bastión)")
        check('Owner     = "genser"' in body and 'Temporary = "true"' in body and "phase2_tags" in body,
              f"{res}: etiquetas Owner, Temporary y DeleteAfter")
    check("aws_eip" not in tf, "Visitas usa IPv4 efímera de la instancia, no una Elastic IP")
    check(re.search(r'variable\s+"enable_phase2_compute"\s*\{[^}]*default\s*=\s*false', variables, re.S) is not None,
          "enable_phase2_compute = false por defecto")
    check('output "test_clients"' in tf and "bastion_private_ip" in tf, "Output test_clients con IPs y bastión de salto")

    # --- Reglas de los clientes ---------------------------------------------------------
    vis_in = SGS["visitas_client"]["ingress"]
    check(all(not any(c.prefixlen == 0 for c in r.cidrs) for r in vis_in),
          "SG visitas_client: ninguna entrada desde Internet (0.0.0.0/0)")
    check(all(set(r.sgs) <= {"bastion", "ti"} and not r.cidrs for r in vis_in),
          "SG visitas_client: solo acepta tráfico del bastión y de TI")
    ti_in = SGS["ti"]["ingress"]
    check(len(ti_in) == 1 and ti_in[0].from_port == 22 and ti_in[0].sgs == ["bastion"],
          "SG ti: única entrada SSH desde el bastión")
    check(all(c == VPC for r in SGS["ti"]["egress"] for c in r.cidrs), "SG ti: salida limitada a la VPC")
    check(SUBNET_NACL.get("visitas") == "visitas" and SUBNET_NACL.get("ti") == "ti", "NACL asociadas a Visitas y TI")
    icmp_ti = [n for n in ("ventas", "bastion", "dns", "intranet", "public_web")
               if any(r.proto == "icmp" and r.from_port == 8 and SUBNETS["ti"][0] in r.cidrs for r in SGS[n]["ingress"])]
    check(len(icmp_ti) == 5, f"ICMP echo desde TI aceptado en ventas, bastion, dns, intranet y public_web ({icmp_ti})")
    ti_reply = [r for r in NACLS["ti"]["ingress"] if r.proto == "icmp"]
    check(bool(ti_reply) and all(r.icmp_type == 0 for r in ti_reply),
          "NACL TI: solo admite ICMP echo-reply (los echo-request hacia TI se deniegan)")

    # --- Plantilla user_data ------------------------------------------------------------
    check(tpl.startswith("#!/bin/bash\n"), "user_data de clientes comienza con #!/bin/bash")
    provided = set(re.findall(r"^\s+(\w+)\s+=", block(tf, "test_client_common = {"), re.M))
    provided |= {"role", "client_ip", "wait_for_internet", "configure_internal_dns"}
    used = set(re.findall(r"(?<!\$)\$\{(\w+)\}", tpl)) | set(re.findall(r"%\{ if (\w+) ~\}", tpl))
    check(used <= provided, f"La plantilla solo usa variables entregadas por Terraform ({sorted(used - provided) or 'ok'})")
    check("BEGIN" not in tpl and "PRIVATE KEY" not in tpl, "user_data sin llaves ni certificados")
    base = {"internal_domain": "rednova.internal", "dns_ip": "10.10.0.164",
            "hardening_b64": base64.b64encode(hard.encode()).decode(),
            "dnsquery_b64": base64.b64encode(dnsq.encode()).decode()}
    for role, ip, inet, dns in (("visitas", VISITAS_IP, True, False), ("ti", TI_IP, False, True)):
        rendered = render_template(tpl, {**base, "role": role, "client_ip": ip,
                                         "wait_for_internet": inet, "configure_internal_dns": dns})
        bash_syntax(f"user_data {role}", rendered)
        size = len(rendered.encode())
        check(size <= 15500, f"user_data {role} = {size} bytes (límite EC2 16384)")
        check(("rednova-internal.conf" in rendered) == dns, f"user_data {role}: DNS interno {'configurado' if dns else 'no configurado'}")
        check(("dnf -y install" in rendered) == inet, f"user_data {role}: dnf {'solo con salida a Internet' if inet else 'no se usa (TI sin Internet)'}")
    bash_syntax("phase2-probe.sh", probe)
    check(probe.isascii(), "phase2-probe.sh es ASCII (se envía por stdin también desde Windows)")
    crlf = [p.name for p in (TF / "templates" / "test-client-user-data.tftpl", SCRIPTS / "phase2-probe.sh",
                             SVC / "dns" / "dnsquery.py", SCRIPTS / "check-public-ports.py") if b"\r\n" in p.read_bytes()]
    check(not crlf, f"Archivos enviados a las EC2 con finales LF ({crlf or 'ok'})")

    # --- Script de pruebas --------------------------------------------------------------
    ids = set(re.findall(r"^\s+T '(F2-\d+[a-z]?)'", ps1, re.M))
    required = {"F2-03", "F2-05", "F2-06", "F2-07", "F2-08", "F2-09", "F2-11", "F2-12"}
    check(required <= {i[:5] for i in ids}, f"test-phase2.ps1 cubre F2-03, 05-09, 11 y 12 ({len(ids)} pruebas)")
    check(not re.search(r"terraform\s+(apply|destroy|import|plan)|aws\s+ec2\s+(authorize|revoke|modify)", ps1),
          "test-phase2.ps1 no ejecuta terraform ni modifica AWS")
    check("AuthorizedBy" in ps1 and "Read-Host" in ps1, "test-phase2.ps1 exige autorización explícita antes de generar tráfico")
    check("exit 1" in ps1 and "exit 2" in ps1, "test-phase2.ps1 devuelve código distinto de cero ante contradicciones")
    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if pwsh:
        cmd = ("$e=$null; [void][System.Management.Automation.Language.Parser]::ParseFile("
               f"'{SCRIPTS / 'test-phase2.ps1'}', [ref]$null, [ref]$e); if ($e) {{ $e | % {{ $_.Message }}; exit 1 }}")
        proc = subprocess.run([pwsh, "-NoProfile", "-Command", cmd], capture_output=True, text=True)
        check(proc.returncode == 0, "test-phase2.ps1 analiza sin errores de sintaxis" + ("" if proc.returncode == 0 else f": {proc.stdout.strip()}"))
    else:
        skip("PowerShell no instalado: se omite el análisis sintáctico de test-phase2.ps1")

    # --- Matriz de tráfico --------------------------------------------------------------
    matrix_lines = ["", "MATRIZ ESTÁTICA DE TRÁFICO (SG + NACL + nftables declarados en Terraform)",
                    f"{'ID':9} {'FLUJO':58} {'ESPERADO':9} {'OBTENIDO':9} MOTIVO"]
    mismatches = 0
    for mid, desc, src, dst, proto, port, expected in MATRIX:
        got, why = flow(src, dst, proto, port)
        ok = got == expected
        mismatches += not ok
        label = f"{desc} ({proto}{'/' + str(port) if proto != 'icmp' else ''})"
        matrix_lines.append(f"{mid:9} {label:58} {'permitir' if expected else 'bloquear':9} "
                            f"{'permitir' if got else 'bloquear':9} {why}{'' if ok else '  <-- CONTRADICE LA MATRIZ'}")
    check(mismatches == 0, f"Matriz estática: {len(MATRIX) - mismatches}/{len(MATRIX)} flujos coinciden con el hand-off")

    # --- Higiene del repositorio --------------------------------------------------------
    forbidden = [p for p in ROOT.rglob("*") if p.is_file() and ".terraform" not in p.parts and ".git" not in p.parts and (
        p.suffix in {".pem", ".key", ".tfstate", ".tfplan", ".tfvars"} or p.name.startswith("terraform.tfstate"))]
    check(not forbidden, f"Sin llaves, estados, planes ni .tfvars en el árbol ({[str(f.relative_to(ROOT)) for f in forbidden] or 'ok'})")
    scan = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts and ".terraform" not in p.parts
            and p.suffix in {".tf", ".tftpl", ".sh", ".ps1", ".py", ".md", ".tex", ".txt", ".csv"}]
    secret_re = re.compile(r"BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|AKIA[0-9A-Z]{16}|aws_secret_access_key\s*=")
    leaks = [str(p.relative_to(ROOT)) for p in scan if secret_re.search(p.read_text(encoding="utf-8", errors="ignore"))]
    check(not leaks, f"Sin patrones de secretos en código y evidencias ({leaks or 'ok'})")
    conflicts = [str(p.relative_to(ROOT)) for p in scan
                 if re.search(r"^(<<<<<<< |>>>>>>> )", p.read_text(encoding="utf-8", errors="ignore"), re.M)]
    check(not conflicts, f"Sin marcadores de conflicto de merge ({conflicts or 'ok'})")

    stamp = dt.datetime.now().astimezone().isoformat(timespec="seconds")
    status = {True: "OK", False: "FALLA", None: "OMITIDA"}
    lines = [f"Validación local de clientes, políticas Visitas/TI y matriz de pruebas - {stamp}", ""]
    lines += [f"[{status[ok]}] {msg}" for ok, msg in results]
    lines += matrix_lines
    passed = sum(ok is True for ok, _ in results)
    skipped = sum(ok is None for ok, _ in results)
    failed = sum(ok is False for ok, _ in results)
    lines += ["", f"Resultado: {passed} correctas, {skipped} omitidas, {failed} fallidas",
              "Nota: la matriz modela lo declarado en Terraform; la evidencia real la produce scripts/test-phase2.ps1."]
    report = "\n".join(lines) + "\n"
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(report, encoding="utf-8")
    print(report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
