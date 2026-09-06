"""Shared chart style. One place so every figure in the submission reads as one system.

Rules enforced here (see the project's viz standards):
  - never a dual-axis chart; two measures of different scale get small multiples or indexing
  - categorical hues assigned in fixed slot order, never cycled; max 3 slots on scatter/all-pairs
  - sequential = one hue light->dark; status colors only when the color *means* good/bad
  - thin marks, hairline solid (never dashed) recessive grid, selective direct labels
  - text wears ink tokens, never the series colour
"""
import matplotlib as mpl
import matplotlib.pyplot as plt

# ── categorical slots (fixed order) ───────────────────────────────────────────
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"      # blue, orange, aqua
C4, C5, C6 = "#eda100", "#e87ba4", "#008300"      # yellow, magenta, green
C7, C8     = "#4a3aa7", "#e34948"                 # violet, red
SERIES = [C1, C2, C3, C4, C5, C6, C7, C8]

# ── sequential blue ramp (light -> dark) ──────────────────────────────────────
SEQ = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
       "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]

# ── status (reserved: only when the colour MEANS good/bad) ────────────────────
GOOD, WARNING, SERIOUS, CRITICAL = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"

# ── chrome & ink ──────────────────────────────────────────────────────────────
SURFACE   = "#fcfcfb"
INK       = "#0b0b0b"
INK_2     = "#52514e"
MUTED     = "#898781"
GRID      = "#e1e0d9"
BASELINE  = "#c3c2b7"

FONT = ["Segoe UI", "system-ui", "DejaVu Sans", "sans-serif"]


def apply():
    mpl.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "sans-serif", "font.sans-serif": FONT, "font.size": 10,
        "text.color": INK, "axes.labelcolor": INK_2, "axes.titlecolor": INK,
        "xtick.color": MUTED, "ytick.color": MUTED,
        "xtick.labelcolor": INK_2, "ytick.labelcolor": INK_2,
        "axes.edgecolor": BASELINE, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.grid.axis": "y",
        "grid.color": GRID, "grid.linewidth": 0.7, "grid.linestyle": "-", "grid.alpha": 1.0,
        "axes.axisbelow": True,
        "xtick.major.size": 0, "ytick.major.size": 0,
        "axes.titlesize": 13, "axes.titleweight": "600", "axes.titlepad": 14,
        "figure.dpi": 120, "savefig.dpi": 200, "savefig.bbox": "tight",
        "legend.frameon": False, "legend.fontsize": 9,
    })


def title(ax, headline, sub=None):
    """Headline states the finding; subtitle carries the method/units."""
    ax.set_title(headline, loc="left", pad=18 if sub else 14)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9.5, color=MUTED, va="bottom")


def note(fig, text):
    fig.text(0.0, -0.02, text, fontsize=8.5, color=MUTED, ha="left", va="top")


def save(fig, name, outdir="figures"):
    import pathlib
    p = pathlib.Path(outdir); p.mkdir(parents=True, exist_ok=True)
    fig.savefig(p / f"{name}.png", bbox_inches="tight")
    plt.close(fig)
    print(f"    figure -> {outdir}/{name}.png")
