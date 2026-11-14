"""Genera diagramas reproducibles para la arquitectura de Fase 2."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "fase-final" / "assets" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#0B1F33"
BLUE = "#16697A"
CYAN = "#2EC4B6"
SKY = "#4EA8DE"
AMBER = "#F4A261"
RED = "#E76F51"
GREEN = "#2A9D8F"
GRAY = "#5C677D"
PALE = "#F7FBFC"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def box(ax, xy, size, title, subtitle, edge, fill="white"):
    x, y = xy
    width, height = size
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.014,rounding_size=0.018",
        edgecolor=edge,
        facecolor=fill,
        linewidth=1.7,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height * 0.64,
        title,
        ha="center",
        va="center",
        color=NAVY,
        weight="bold",
        fontsize=9.2,
    )
    ax.text(
        x + width / 2,
        y + height * 0.29,
        subtitle,
        ha="center",
        va="center",
        color=GRAY,
        fontsize=7.3,
    )


def arrow(ax, start, end, color=SKY, dashed=False, width=1.5):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=11,
        linewidth=width,
        color=color,
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(patch)


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(14.2, 8.2), constrained_layout=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title(
        "RedNova GT · Arquitectura acumulativa de Fase 2",
        color=NAVY,
        fontsize=17,
        weight="bold",
        pad=12,
    )

    box(ax, (0.40, 0.91), (0.20, 0.055), "Internet", "clientes y operador", AMBER, "#FFF8EC")
    box(ax, (0.415, 0.81), (0.17, 0.055), "Internet Gateway", "ruta 0.0.0.0/0", AMBER, "#FFF8EC")
    arrow(ax, (0.50, 0.91), (0.50, 0.865), AMBER)

    ax.add_patch(
        FancyBboxPatch(
            (0.025, 0.07),
            0.95,
            0.69,
            boxstyle="round,pad=0.018",
            edgecolor=BLUE,
            facecolor=PALE,
            linewidth=2.1,
        )
    )
    ax.text(0.045, 0.725, "VPC 10.10.0.0/24 · us-east-1", color=BLUE, weight="bold", fontsize=11)

    ax.add_patch(
        FancyBboxPatch(
            (0.055, 0.43),
            0.89,
            0.25,
            boxstyle="round,pad=0.012",
            edgecolor=AMBER,
            facecolor="#FFF9EF",
            linewidth=1.5,
        )
    )
    ax.text(0.075, 0.645, "SEGMENTOS PÚBLICOS", color="#A85D16", weight="bold")
    box(ax, (0.08, 0.49), (0.23, 0.105), "Visitas", "10.10.0.0/26 · Internet aislado", AMBER)
    box(ax, (0.385, 0.49), (0.23, 0.105), "Administración", "10.10.0.176/28 · bastión", AMBER)
    box(ax, (0.69, 0.49), (0.23, 0.105), "DMZ", "10.10.0.192/27 · web pública", RED, "#FFF5F2")

    ax.add_patch(
        FancyBboxPatch(
            (0.055, 0.14),
            0.89,
            0.23,
            boxstyle="round,pad=0.012",
            edgecolor=GREEN,
            facecolor="#EFFAF7",
            linewidth=1.5,
        )
    )
    ax.text(0.075, 0.335, "SEGMENTOS PRIVADOS", color=GREEN, weight="bold")
    box(ax, (0.08, 0.19), (0.20, 0.095), "Ventas", "10.10.0.64/26", GREEN)
    box(ax, (0.31, 0.19), (0.20, 0.095), "TI", "10.10.0.128/27", GREEN)
    box(ax, (0.54, 0.19), (0.20, 0.095), "Data Center", "10.10.0.160/28 · DNS/RR. HH.", GREEN)
    box(ax, (0.77, 0.19), (0.15, 0.095), "Reserva", "10.10.0.224/27", GRAY, "#F2F4F7")

    arrow(ax, (0.45, 0.81), (0.20, 0.68), AMBER)
    arrow(ax, (0.50, 0.81), (0.50, 0.68), AMBER)
    arrow(ax, (0.55, 0.81), (0.805, 0.68), AMBER)
    arrow(ax, (0.805, 0.595), (0.805, 0.49), RED)
    ax.text(0.817, 0.535, "HTTP/HTTPS", color=RED, fontsize=7.5, weight="bold")

    arrow(ax, (0.50, 0.49), (0.64, 0.285), SKY, dashed=True)
    arrow(ax, (0.50, 0.49), (0.41, 0.285), SKY, dashed=True)
    ax.text(0.505, 0.405, "SSH administrado", color=SKY, fontsize=7.5, weight="bold")

    arrow(ax, (0.41, 0.285), (0.18, 0.285), CYAN, dashed=True)
    arrow(ax, (0.41, 0.285), (0.64, 0.285), CYAN, dashed=True)
    arrow(ax, (0.41, 0.285), (0.805, 0.49), CYAN, dashed=True)
    ax.text(0.355, 0.305, "TI inicia pruebas", color=GREEN, fontsize=7.3, weight="bold")

    ax.text(
        0.5,
        0.09,
        "Security Groups stateful + NACL stateless · cómputo deshabilitado por defecto · sin NAT Gateway",
        ha="center",
        color=GRAY,
        fontsize=9,
    )

    fig.savefig(OUT / "arquitectura-fase2.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / "arquitectura-fase2.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    architecture()
    print(f"Figuras de Fase 2 generadas en {OUT}")


if __name__ == "__main__":
    main()
