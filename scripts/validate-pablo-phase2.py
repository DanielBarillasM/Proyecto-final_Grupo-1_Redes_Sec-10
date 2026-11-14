"""Valida el bloque de red de Pablo para la Fase 2 sin consultar AWS."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TERRAFORM = ROOT / "infra" / "terraform"
EVIDENCE = ROOT / "evidence" / "fase-2" / "deployment" / "pablo-validation.txt"
VPC = ipaddress.ip_network("10.10.0.0/24")


@dataclass(frozen=True)
class Segment:
    cidr: str
    required: int


SEGMENTS = {
    "visitas": Segment("10.10.0.0/26", 30),
    "ventas": Segment("10.10.0.64/26", 25),
    "ti": Segment("10.10.0.128/27", 15),
    "datacenter": Segment("10.10.0.160/28", 5),
    "administracion": Segment("10.10.0.176/28", 3),
    "dmz": Segment("10.10.0.192/27", 1),
}
RESERVE = ipaddress.ip_network("10.10.0.224/27")
SERVICE_IPS = {
    "visitas_client": ("10.10.0.4", "visitas"),
    "ti_client": ("10.10.0.132", "ti"),
    "dns": ("10.10.0.164", "datacenter"),
    "intranet": ("10.10.0.165", "datacenter"),
    "public_web": ("10.10.0.196", "dmz"),
}


def aws_assignable(network: ipaddress.IPv4Network) -> int:
    return network.num_addresses - 5


def aws_assignable_range(
    network: ipaddress.IPv4Network,
) -> tuple[ipaddress.IPv4Address, ipaddress.IPv4Address]:
    return network.network_address + 4, network.broadcast_address - 1


def require_text(path: Path, *patterns: str) -> None:
    content = path.read_text(encoding="utf-8")
    for pattern in patterns:
        if re.search(pattern, content, flags=re.MULTILINE) is None:
            raise AssertionError(f"Falta el patrón {pattern!r} en {path.relative_to(ROOT)}")


def main() -> None:
    lines = [
        "VALIDACIÓN LOCAL - BLOQUE DE PABLO - FASE 2",
        f"VPC: {VPC}",
        "",
    ]

    networks: dict[str, ipaddress.IPv4Network] = {}
    for name, segment in SEGMENTS.items():
        network = ipaddress.ip_network(segment.cidr)
        assert network.subnet_of(VPC), f"{network} no pertenece a {VPC}"
        assert aws_assignable(network) >= segment.required, f"{name} no tiene capacidad"
        for previous_name, previous in networks.items():
            assert not network.overlaps(previous), (
                f"Solapamiento entre {name} {network} y {previous_name} {previous}"
            )
        networks[name] = network
        first, last = aws_assignable_range(network)
        lines.append(
            f"{name:15} {str(network):18} asignables={aws_assignable(network):2} "
            f"rango={first}-{last} OK"
        )

    assert RESERVE.subnet_of(VPC)
    assert all(not RESERVE.overlaps(network) for network in networks.values())
    lines.append(f"{'reserva':15} {str(RESERVE):18} sin asignar OK")
    lines.append("")

    for name, (address_text, segment_name) in SERVICE_IPS.items():
        address = ipaddress.ip_address(address_text)
        network = networks[segment_name]
        first, last = aws_assignable_range(network)
        assert address in network, f"{name}={address} no pertenece a {network}"
        assert first <= address <= last, f"{name}={address} está reservada por AWS"
        lines.append(f"IP {name:16} {address} pertenece a {segment_name} OK")

    require_text(
        TERRAFORM / "locals.tf",
        r'dmz\s*=\s*\{',
        r'cidr\s*=\s*"10\.10\.0\.192/27"',
        r'phase2_reserved_cidr\s*=\s*"10\.10\.0\.224/27"',
    )
    require_text(
        TERRAFORM / "dmz.tf",
        r'resource\s+"aws_route_table"\s+"dmz_public"',
        r'cidr_block\s*=\s*"0\.0\.0\.0/0"',
        r'gateway_id\s*=\s*aws_internet_gateway\.main\.id',
    )
    require_text(
        TERRAFORM / "nacls.tf",
        r'resource\s+"aws_network_acl"\s+"visitas"',
        r'resource\s+"aws_network_acl"\s+"ti"',
        r'resource\s+"aws_network_acl"\s+"dmz"',
        r'resource\s+"aws_network_acl_association"\s+"visitas"',
        r'resource\s+"aws_network_acl_association"\s+"ti"',
        r'resource\s+"aws_network_acl_association"\s+"dmz"',
    )
    require_text(
        TERRAFORM / "variables.tf",
        r'variable\s+"enable_phase2_compute"',
        r'default\s*=\s*false',
        r'variable\s+"internal_domain"',
        r'variable\s+"public_domain"',
    )

    security_text = (TERRAFORM / "phase2-security.tf").read_text(encoding="utf-8")
    assert 'name        = "${var.phase2_project_name}-public-web-sg"' in security_text
    assert not re.search(
        r'from_port\s*=\s*22[\s\S]{0,180}cidr_blocks\s*=\s*\["0\.0\.0\.0/0"\]',
        security_text,
    ), "Se detectó SSH público en los Security Groups de Fase 2"

    lines.extend(
        [
            "",
            "Terraform estructural: DMZ, ruta, NACL, asociaciones, variables y SG OK",
            "SSH público 0.0.0.0/0: no detectado OK",
            "RESULTADO: bloque local de Pablo válido.",
        ]
    )

    output = "\n".join(lines) + "\n"
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
