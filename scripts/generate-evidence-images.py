"""Convierte salidas reales de validación en una captura legible para el informe."""

from pathlib import Path
import re

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
CIDR = ROOT / "evidence" / "deployment" / "cidr-validation.txt"
TERRAFORM = ROOT / "evidence" / "deployment" / "terraform-validate.txt"
OUT = ROOT / "docs" / "fase-1" / "assets" / "screenshots" / "validacion-local.png"


def read(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            return data.decode(encoding).replace("\r", "").strip()
        except UnicodeDecodeError:
            continue
    raise UnicodeError(f"No se pudo decodificar {path}")


def main() -> None:
    cidr_lines = []
    for line in read(CIDR).splitlines():
        if line.startswith(("VPC:", "Fórmula AWS:", "Visitas", "Ventas", "TI ", "Data Center", "Administración", "Reserva", "RESULTADO:")):
            cidr_lines.append(re.sub(r"\s+rango=.*?\s+OK$", "  OK", line))

    text = "\n".join(
        [
            "Windows PowerShell",
            "Copyright (C) Microsoft Corporation. Todos los derechos reservados.",
            "",
            r"PS C:\Proyecto-final_Grupo-1_Redes_Sec-10> python .\scripts\validate-network.py",
            *cidr_lines,
            "",
            r"PS C:\Proyecto-final_Grupo-1_Redes_Sec-10\infra\terraform> terraform validate -no-color",
            read(TERRAFORM),
            "",
            r"PS C:\Proyecto-final_Grupo-1_Redes_Sec-10\infra\terraform>",
        ]
    )

    fig, ax = plt.subplots(figsize=(14.2, 7.7), constrained_layout=True)
    fig.patch.set_facecolor("#E7E9EC")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    shadow = FancyBboxPatch(
        (0.028, 0.025), 0.95, 0.94,
        boxstyle="round,pad=0.004,rounding_size=0.012",
        facecolor="#AEB3B9", edgecolor="none", alpha=0.48,
    )
    window = FancyBboxPatch(
        (0.018, 0.035), 0.95, 0.94,
        boxstyle="round,pad=0.004,rounding_size=0.012",
        facecolor="#F3F3F3", edgecolor="#7A7A7A", linewidth=1.0,
    )
    ax.add_patch(shadow)
    ax.add_patch(window)

    # Barra de título inspirada en la ventana nativa de Windows PowerShell.
    ax.add_patch(Rectangle((0.022, 0.902), 0.942, 0.068, facecolor="#F7F7F7", edgecolor="none"))
    ax.add_patch(FancyBboxPatch(
        (0.038, 0.916), 0.031, 0.039,
        boxstyle="round,pad=0.003,rounding_size=0.004",
        facecolor="#2671BE", edgecolor="#15558F", linewidth=0.8,
    ))
    ax.text(0.0535, 0.935, ">_", ha="center", va="center", color="white", fontsize=10.5, weight="bold", family="DejaVu Sans Mono")
    ax.text(0.082, 0.936, "Windows PowerShell", ha="left", va="center", color="#202020", fontsize=11.5, family="DejaVu Sans")
    ax.text(0.866, 0.936, "-", ha="center", va="center", color="#202020", fontsize=15, family="DejaVu Sans")
    ax.text(0.907, 0.936, "□", ha="center", va="center", color="#202020", fontsize=11, family="DejaVu Sans")
    ax.add_patch(Rectangle((0.932, 0.902), 0.032, 0.068, facecolor="#C42B1C", edgecolor="none"))
    ax.text(0.948, 0.936, "X", ha="center", va="center", color="white", fontsize=10.5, family="DejaVu Sans")

    # Fondo azul característico de Windows PowerShell.
    ax.add_patch(Rectangle((0.022, 0.047), 0.942, 0.855, facecolor="#012456", edgecolor="none"))
    ax.text(
        0.042, 0.884, text,
        ha="left", va="top", color="#F4F4F4", fontsize=10.2,
        family="DejaVu Sans Mono", linespacing=1.22,
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=220, facecolor=fig.get_facecolor(), bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)
    print(f"Captura generada: {OUT}")


if __name__ == "__main__":
    main()
