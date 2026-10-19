import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def make_logo(path, agency_name, colors):
    """Sample logo: three ascending bars + serif wordmark with spaced small caps."""
    first, _, rest = agency_name.partition(" ")
    fig, ax = plt.subplots(figsize=(4, 1.0), dpi=300)
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for i, h in enumerate([0.24, 0.40, 0.58]):
        ax.add_patch(Rectangle((0.06 + i * 0.17, 0.20), 0.09, h,
                               fc=colors["accent"] if i == 2 else colors["primary"], ec="none"))
    ax.text(0.78, 0.58, first, fontsize=26, fontweight="bold", family="serif",
            color=colors["primary"], va="center")
    ax.text(0.80, 0.17, " ".join((rest or "").upper().replace(" ", "")), fontsize=8.5,
            fontweight="bold", color=colors["muted"], va="center")
    fig.savefig(path, transparent=True)
    plt.close(fig)