"""Convierte salidas reales de validación en una captura legible para el informe."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch


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
    text = (
        "$ python scripts/validate-network.py\n"
        + read(CIDR)
        + "\n\n$ terraform validate -no-color\n"
        + read(TERRAFORM)
    )
    fig, ax = plt.subplots(figsize=(13.2, 7.2), constrained_layout=True)
    fig.patch.set_facecolor("#E9EEF3")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    panel = FancyBboxPatch(
        (0.025, 0.035), 0.95, 0.93,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        facecolor="#0B1F33", edgecolor="#2EC4B6", linewidth=2,
    )
    ax.add_patch(panel)
    for x, color in [(0.055, "#E76F51"), (0.078, "#F4A261"), (0.101, "#2EC4B6")]:
        ax.add_patch(plt.Circle((x, 0.925), 0.008, color=color))
    ax.text(0.5, 0.925, "validación local · Grupo 1", ha="center", va="center", color="#C9D6E2", fontsize=11, family="DejaVu Sans Mono")
    ax.text(0.055, 0.88, text, ha="left", va="top", color="#EAF4F4", fontsize=8.8, family="DejaVu Sans Mono", linespacing=1.32)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=220, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Captura generada: {OUT}")


if __name__ == "__main__":
    main()
