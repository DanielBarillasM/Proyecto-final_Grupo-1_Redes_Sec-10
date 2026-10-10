"""Valida matemáticamente el plan CIDR y genera evidencia legible."""

from __future__ import annotations

import ipaddress
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "deployment" / "cidr-validation.txt"
VPC = ipaddress.ip_network("10.10.0.0/24")
SUBNETS = {
    "Visitas": ("10.10.0.0/26", 30),
    "Ventas": ("10.10.0.64/26", 25),
    "TI": ("10.10.0.128/27", 15),
    "Data Center": ("10.10.0.160/28", 5),
    "Administración": ("10.10.0.176/28", 3),
}
RESERVE = ipaddress.ip_network("10.10.0.192/26")


def aws_assignable(network: ipaddress.IPv4Network) -> int:
    return network.num_addresses - 5


def main() -> None:
    networks: list[ipaddress.IPv4Network] = []
    lines = [
        "VALIDACIÓN DEL PLAN CIDR - CC3067 FASE 1",
        f"VPC: {VPC} ({VPC.num_addresses} direcciones)",
        "Fórmula AWS: asignables = 2^(32-prefijo) - 5",
        "",
    ]

    for name, (cidr, required) in SUBNETS.items():
        network = ipaddress.ip_network(cidr)
        assert network.subnet_of(VPC), f"{network} no está dentro de {VPC}"
        assert aws_assignable(network) >= required, f"{name} no tiene capacidad"
        for previous in networks:
            assert not network.overlaps(previous), f"Solapamiento: {network} y {previous}"
        networks.append(network)
        first_assignable = network.network_address + 4
        last_assignable = network.broadcast_address - 1
        lines.append(
            f"{name:15} {str(network):18} total={network.num_addresses:3} "
            f"AWS={aws_assignable(network):3} requeridas={required:2} "
            f"rango={first_assignable}-{last_assignable} OK"
        )

    assert RESERVE.subnet_of(VPC)
    assert all(not RESERVE.overlaps(n) for n in networks)
    lines.extend(
        [
            f"Reserva         {str(RESERVE):18} total={RESERVE.num_addresses:3} sin asignar OK",
            "",
            "RESULTADO: todos los bloques son canónicos, suficientes, contenidos y no se superponen.",
        ]
    )
    EVIDENCE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
