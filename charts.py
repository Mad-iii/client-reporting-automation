import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, MaxNLocator

PREV = "#CFC9BB"
GRID = "#E6E1D6"
INK = "#1B2430"
MUTED = "#6B7280"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8.5, "text.color": INK,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
})


def _money(v, _=None):
    return f"${v / 1000:.0f}k" if v >= 1000 else f"${v:.0f}"


def _tidy(ax, grid="y"):
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0, labelsize=8)
    ax.set_axisbelow(True)
    ax.grid(axis=grid, color=GRID, lw=0.7)


def trend_chart(f, path, c):
    t = f["trend"]
    x = np.arange(len(t["labels"]))
    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=220)
    ends = {"revenue": t["revenue"][-1], "spend": t["spend"][-1]}
    top = max(ends.values()) or 1
    nudge = 0.07 * top if abs(ends["revenue"] - ends["spend"]) < 0.14 * top else 0
    label_y = {
        "revenue": ends["revenue"] + (nudge if ends["revenue"] >= ends["spend"] else -nudge),
        "spend": ends["spend"] + (nudge if ends["spend"] > ends["revenue"] else -nudge),
    }
    for key, color, name in (("revenue", c["primary"], "Revenue"), ("spend", c["accent"], "Ad spend")):
        ax.plot(x, t[key], color=color, lw=2.2, solid_capstyle="round")
        ax.scatter(x[-1], t[key][-1], color=color, s=26, zorder=3)
        ax.text(x[-1] + 0.2, label_y[key], f"{name}\n{_money(t[key][-1])}", color=color,
                fontsize=8, fontweight="bold", va="center")
    ax.set_xticks(x)
    ax.set_xticklabels(t["labels"])
    ax.set_xlim(-0.3, len(x) - 1 + 1.4)
    ax.set_ylim(bottom=0)
    ax.yaxis.set_major_formatter(FuncFormatter(_money))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    _tidy(ax, "y")
    fig.tight_layout()
    fig.savefig(path, transparent=True)
    plt.close(fig)


def campaigns_chart(f, path, c):
    rows = f["campaigns"]
    labels = [textwrap.fill(f"{r['campaign']}  |  {r['platform'].split()[0]}", 32) for r in rows]
    cur = [r["roas"] or 0 for r in rows]
    prev = [(r["prev"]["roas"] or 0) if r["prev"] else 0 for r in rows]
    xmax = max(cur + prev + [1.2])
    fig, ax = plt.subplots(figsize=(7.2, 0.5 * len(rows) + 1.2), dpi=220)
    y, h = np.arange(len(rows)), 0.30
    ax.barh(y - h / 2 - 0.02, prev, h, color=PREV, label="Previous week")
    ax.barh(y + h / 2 + 0.02, cur, h, color=c["primary"], label="This week")
    for yi, v in zip(y, cur):
        ax.text(v + xmax * 0.012, yi + h / 2 + 0.02, f"{v:.2f}x", va="center", fontsize=7.5,
                fontweight="bold", color=c["primary"])
    ax.axvline(1, color=c["bad"], lw=0.9, ls=(0, (4, 3)))
    ax.text(1.01, -0.8, "break-even", color=c["bad"], fontsize=7, va="center")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=7.8, color=INK)
    ax.set_xlim(0, xmax * 1.15)
    ax.set_ylim(len(rows) - 0.45, -1.0)
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0f}x"))
    ax.legend(loc="lower right", frameon=False, fontsize=7.5)
    _tidy(ax, "x")
    ax.spines["bottom"].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, transparent=True)
    plt.close(fig)


def channels_chart(f, path, c):
    rows = f["channels"]
    x, w = np.arange(len(rows)), 0.34
    fig, ax = plt.subplots(figsize=(7.2, 2.4), dpi=220)
    ax.bar(x - w / 2 - 0.01, [r["prev"] for r in rows], w, color=PREV, label="Previous week")
    ax.bar(x + w / 2 + 0.01, [r["sessions"] for r in rows], w, color=c["primary"], label="This week")
    top = max([r["sessions"] for r in rows] + [r["prev"] for r in rows] + [1])
    for xi, r in zip(x, rows):
        ax.text(xi + w / 2 + 0.01, r["sessions"] + top * 0.02, f"{r['sessions']:,.0f}", ha="center",
                fontsize=7.2, color=c["primary"], fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([r["channel"] for r in rows])
    ax.set_ylim(0, top * 1.15)
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.legend(loc="upper right", frameon=False, fontsize=7.5)
    _tidy(ax, "y")
    fig.tight_layout()
    fig.savefig(path, transparent=True)
    plt.close(fig)


def make_charts(f, out_dir, colors):
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    paths = {n: str(d / f"{n}.png") for n in ("trend", "campaigns", "channels")}
    trend_chart(f, paths["trend"], colors)
    campaigns_chart(f, paths["campaigns"], colors)
    channels_chart(f, paths["channels"], colors)
    return paths