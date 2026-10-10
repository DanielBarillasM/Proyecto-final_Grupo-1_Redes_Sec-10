"""Genera las figuras vectoriales del informe de Fase 1."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "fase-1" / "assets" / "diagrams"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#0B1F33"
BLUE = "#16697A"
CYAN = "#2EC4B6"
SKY = "#4EA8DE"
AMBER = "#F4A261"
RED = "#E76F51"
GREEN = "#2A9D8F"
PALE = "#EDF6F9"
GRAY = "#5C677D"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titleweight": "bold",
        "axes.titlesize": 16,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{name}.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def box(ax, xy, width, height, title, subtitle="", color=BLUE, fc="white", lw=1.8):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y), width, height,
        boxstyle="round,pad=0.018,rounding_size=0.025",
        edgecolor=color, facecolor=fc, linewidth=lw,
    )
    ax.add_patch(patch)
    ax.text(x + width / 2, y + height * 0.63, title, ha="center", va="center", weight="bold", color=NAVY, fontsize=10)
    if subtitle:
        ax.text(x + width / 2, y + height * 0.30, subtitle, ha="center", va="center", color=GRAY, fontsize=8)
    return patch


def arrow(ax, start, end, color=SKY, style="-|>", lw=1.8, rad=0.0, dashed=False):
    patch = FancyArrowPatch(
        start,
        end,
        arrowstyle=style,
        mutation_scale=12,
        linewidth=lw,
        color=color,
        linestyle="--" if dashed else "-",
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(patch)
    return patch


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(13.5, 7.6), constrained_layout=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Arquitectura lógica propuesta en Amazon VPC", color=NAVY, pad=14)

    ax.add_patch(FancyBboxPatch((0.02, 0.04), 0.96, 0.84, boxstyle="round,pad=0.02", ec=BLUE, fc="#F7FBFC", lw=2.2))
    ax.text(0.04, 0.845, "VPC 10.10.0.0/24 · una zona de disponibilidad para el prototipo", color=BLUE, weight="bold", fontsize=11)

    box(ax, (0.39, 0.91), 0.22, 0.065, "Internet", "origen de administración", AMBER, "#FFF8EC")
    box(ax, (0.41, 0.76), 0.18, 0.075, "Internet Gateway", "ruta pública 0.0.0.0/0", AMBER, "#FFF8EC")
    arrow(ax, (0.50, 0.91), (0.50, 0.835), AMBER)

    ax.add_patch(FancyBboxPatch((0.055, 0.11), 0.37, 0.62, boxstyle="round,pad=0.015", ec=AMBER, fc="#FFF9EF", lw=1.8))
    ax.text(0.075, 0.69, "ZONA PÚBLICA", color="#B5651D", weight="bold", fontsize=10)
    box(ax, (0.08, 0.48), 0.31, 0.14, "Visitas", "10.10.0.0/26 · 59 IP asignables", AMBER, "white")
    box(ax, (0.08, 0.24), 0.31, 0.16, "Administración", "10.10.0.176/28 · bastión temporal", AMBER, "white")
    arrow(ax, (0.44, 0.76), (0.31, 0.62), AMBER, rad=0.1)
    arrow(ax, (0.47, 0.76), (0.31, 0.40), AMBER, rad=0.1)

    ax.add_patch(FancyBboxPatch((0.46, 0.11), 0.48, 0.62, boxstyle="round,pad=0.015", ec=GREEN, fc="#EFFAF7", lw=1.8))
    ax.text(0.48, 0.69, "ZONA PRIVADA · sin ruta directa a Internet", color=GREEN, weight="bold", fontsize=10)
    box(ax, (0.49, 0.48), 0.19, 0.14, "Ventas", "10.10.0.64/26", GREEN, "white")
    box(ax, (0.72, 0.48), 0.19, 0.14, "TI", "10.10.0.128/27", GREEN, "white")
    box(ax, (0.49, 0.23), 0.19, 0.14, "Data Center", "10.10.0.160/28", GREEN, "white")
    box(ax, (0.72, 0.23), 0.19, 0.14, "Reserva", "10.10.0.192/26", GRAY, "#F2F4F7")
    ax.text(0.585, 0.535, "EC2 A   ⇄   EC2 B", ha="center", va="center", fontsize=8.5, color=BLUE, weight="bold")

    arrow(ax, (0.39, 0.32), (0.49, 0.53), SKY, dashed=True)
    ax.text(0.425, 0.43, "SSH", color=SKY, fontsize=8, weight="bold")
    arrow(ax, (0.68, 0.55), (0.72, 0.55), CYAN, style="<->")
    arrow(ax, (0.59, 0.48), (0.59, 0.37), CYAN)
    arrow(ax, (0.77, 0.48), (0.64, 0.37), CYAN)
    ax.text(0.70, 0.405, "rutas locales + reglas SG", color=GREEN, fontsize=7.8, ha="center")

    ax.text(0.5, 0.065, "Separación por tablas de rutas y grupos de seguridad · mínimo privilegio · recursos etiquetados", ha="center", color=GRAY, fontsize=9)
    save(fig, "arquitectura-vpc")


def cidr_map() -> None:
    fig, ax = plt.subplots(figsize=(13.2, 4.4), constrained_layout=True)
    ax.set_xlim(0, 256)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Distribución VLSM del bloque 10.10.0.0/24", color=NAVY, pad=15)
    segments = [
        (0, 64, "Visitas\n10.10.0.0/26\n64 totales · 59 asignables", AMBER),
        (64, 64, "Ventas\n10.10.0.64/26\n64 totales · 59 asignables", BLUE),
        (128, 32, "TI\n10.10.0.128/27\n32 · 27", CYAN),
        (160, 16, "Data Center\n/28\n16 · 11", GREEN),
        (176, 16, "Admin.\n/28\n16 · 11", RED),
        (192, 64, "Reserva\n10.10.0.192/26\n64 direcciones", GRAY),
    ]
    for start, size, label, color in segments:
        ax.add_patch(Rectangle((start, 0.35), size, 0.34, facecolor=color, edgecolor="white", linewidth=2))
        fontsize = 8 if size <= 16 else 9
        ax.text(start + size / 2, 0.52, label, ha="center", va="center", color="white", weight="bold", fontsize=fontsize)
        ax.text(start, 0.28, f".{start}", ha="center", va="top", fontsize=8, color=NAVY)
    ax.text(256, 0.28, ".255", ha="center", va="top", fontsize=8, color=NAVY)
    ax.plot([0, 256], [0.31, 0.31], color=NAVY, linewidth=1)
    ax.text(128, 0.10, "Los bloques están contenidos en /24, son canónicos y no se superponen.", ha="center", color=GRAY, fontsize=10)
    save(fig, "mapa-cidr")


def security_matrix() -> None:
    labels = ["Visitas", "Ventas", "TI", "Data Center", "Administración"]
    matrix = np.array([
        [1, 0, 0, 0, 0],
        [0, 1, 0, 2, 0],
        [0, 2, 1, 2, 0],
        [0, 0, 0, 1, 0],
        [0, 2, 2, 2, 1],
    ])
    colors = ["#E9ECEF", "#B7E4C7", "#FFE8A1"]
    from matplotlib.colors import ListedColormap

    fig, ax = plt.subplots(figsize=(9.5, 6.2), constrained_layout=True)
    ax.imshow(matrix, cmap=ListedColormap(colors), vmin=0, vmax=2)
    ax.set_xticks(range(len(labels)), labels=labels, rotation=25, ha="right")
    ax.set_yticks(range(len(labels)), labels=labels)
    ax.set_xlabel("Destino")
    ax.set_ylabel("Origen")
    ax.set_title("Matriz de comunicación prevista", color=NAVY, pad=16)
    descriptions = {0: "Denegado", 1: "Local", 2: "Permitido\ncontrolado"}
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, descriptions[int(matrix[i, j])], ha="center", va="center", fontsize=8.5, color=NAVY, weight="bold")
    for edge in np.arange(-0.5, 5.5, 1):
        ax.axhline(edge, color="white", lw=2)
        ax.axvline(edge, color="white", lw=2)
    ax.text(0.5, -0.20, "Internet para Visitas se controla en la tabla de rutas; no implica acceso a segmentos internos.", transform=ax.transAxes, ha="center", color=GRAY, fontsize=9)
    save(fig, "matriz-seguridad")


def workflow() -> None:
    fig, ax = plt.subplots(figsize=(13.2, 4.7), constrained_layout=True)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_title("Flujo reproducible de implementación y verificación", color=NAVY, pad=14)
    steps = [
        ("1", "Validar", "credenciales, región\ny presupuesto"),
        ("2", "Planificar", "terraform fmt\nvalidate y plan"),
        ("3", "Desplegar", "VPC, subredes,\nrutas, SG y EC2"),
        ("4", "Probar", "ping privado, rutas\ny aislamiento"),
        ("5", "Evidenciar", "capturas, salidas\ny trazabilidad"),
        ("6", "Destruir", "terraform destroy\ny auditoría final"),
    ]
    xs = np.linspace(0.04, 0.84, len(steps))
    for i, ((num, title, sub), x) in enumerate(zip(steps, xs)):
        color = [BLUE, SKY, CYAN, GREEN, AMBER, RED][i]
        box(ax, (x, 0.34), 0.12, 0.30, f"{num} · {title}", sub, color, "white", 2)
        if i < len(steps) - 1:
            arrow(ax, (x + 0.12, 0.49), (xs[i + 1], 0.49), GRAY, lw=1.5)
    ax.text(0.5, 0.16, "Puerta de salida: no quedan instancias, volúmenes, direcciones públicas ni gateways cobrables.", ha="center", color=GRAY, fontsize=10)
    save(fig, "flujo-implementacion")


def provider_matrix() -> None:
    providers = ["AWS", "Azure", "Google Cloud", "DigitalOcean"]
    criteria = ["Ajuste de red", "Beneficio académico", "Documentación", "IaC", "Control de costo"]
    weights = np.array([0.30, 0.25, 0.20, 0.15, 0.10])
    scores = np.array([
        [5, 4, 5, 5, 4],
        [4, 4, 5, 5, 4],
        [4, 4, 4, 5, 4],
        [3, 4, 4, 4, 5],
    ])
    totals = scores @ weights
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.4), gridspec_kw={"width_ratios": [1.45, 1]}, constrained_layout=True)
    im = axes[0].imshow(scores, cmap="Blues", vmin=1, vmax=5, aspect="auto")
    axes[0].set_xticks(range(len(criteria)), [f"{c}\n({w:.0%})" for c, w in zip(criteria, weights)], rotation=18, ha="right")
    axes[0].set_yticks(range(len(providers)), providers)
    axes[0].set_title("Puntuaciones 1–5 y ponderaciones", color=NAVY)
    for i in range(scores.shape[0]):
        for j in range(scores.shape[1]):
            axes[0].text(j, i, str(scores[i, j]), ha="center", va="center", color="white" if scores[i, j] >= 4 else NAVY, weight="bold")
    fig.colorbar(im, ax=axes[0], fraction=0.035, pad=0.02)
    order = np.argsort(totals)
    bars = axes[1].barh(np.array(providers)[order], totals[order], color=[GRAY, SKY, CYAN, BLUE])
    axes[1].set_xlim(0, 5)
    axes[1].set_xlabel("Puntaje ponderado / 5")
    axes[1].set_title("Resultado", color=NAVY)
    axes[1].grid(axis="x", alpha=0.2)
    for bar, value in zip(bars, totals[order]):
        axes[1].text(value + 0.06, bar.get_y() + bar.get_height() / 2, f"{value:.2f}", va="center", weight="bold", color=NAVY)
    fig.suptitle("Matriz de selección del proveedor", color=NAVY, weight="bold", fontsize=16)
    save(fig, "matriz-proveedores")


def gantt() -> None:
    tasks = [
        ("Aprobación y alcance", 0, 2, BLUE),
        ("Investigación", 2, 2, SKY),
        ("Subneteo y arquitectura", 4, 3, CYAN),
        ("Terraform y seguridad", 7, 2, GREEN),
        ("Despliegue y pruebas", 9, 2, AMBER),
        ("Redacción e integración", 10, 3, BLUE),
        ("Revisión y entrega", 13, 2, RED),
    ]
    fig, ax = plt.subplots(figsize=(12.5, 5.2), constrained_layout=True)
    y = np.arange(len(tasks))
    for idx, (label, start, duration, color) in enumerate(tasks):
        ax.barh(idx, duration, left=start, color=color, edgecolor="white", height=0.62)
        ax.text(start + duration / 2, idx, f"{duration} d", ha="center", va="center", color="white", weight="bold", fontsize=8)
    ax.set_yticks(y, [t[0] for t in tasks])
    ax.invert_yaxis()
    ax.set_xticks(range(15), [str(d) for d in range(5, 20)])
    ax.set_xlabel("Octubre de 2026")
    ax.set_title("Cronograma de ejecución de la Fase 1", color=NAVY, pad=14)
    ax.grid(axis="x", alpha=0.2)
    ax.axvline(14, color=RED, lw=1.5, linestyle="--")
    ax.set_ylim(len(tasks) - 0.35, -0.8)
    ax.text(14, -0.52, "Entrega: 19/oct", va="center", ha="center", color=RED, fontsize=8, weight="bold")
    save(fig, "cronograma")


def main() -> None:
    architecture()
    cidr_map()
    security_matrix()
    workflow()
    provider_matrix()
    gantt()
    print(f"Figuras generadas en {OUT}")


if __name__ == "__main__":
    main()
