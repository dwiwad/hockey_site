"""Hockey Decoded figure style for the career-tenure post.

Values taken from the two most recent deep-dive scripts:
  scripts/depth-and-goaltending/figs_for_deepdive.py
  scripts/nhl-player-demographics/2. Time_Series_Descriptives.py

transparent=True matters: the site background is --bg-cream #fbf8f1, so a
figure saved on white renders as a white slab on a cream page.
"""
import os
import textwrap

import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns

mpl.rcParams["font.family"] = "Charter"

COL_BLUE_PALE = "#3B4B64"
COL_BLUE_DARK = "#041E42"
COL_OIL_ORANGE = "#FF4C00"
COL_GRAY = "#9AA3AF"
COL_WHITE = "#FFFFFF"

FIGSIZE = (12, 7)
FS_TITLE = 20
FS_SUBTITLE = 14
FS_AXIS_LABEL = 18
FS_XAXIS_LABEL = 16
FS_TICK = 14
FS_LEGEND = 14
FS_NOTE = 10

TOP = 0.85           # subplots_adjust(top=) for a one-line subtitle
Y_TITLE = 0.97
Y_SUBTITLE = 0.87
LINE_H = 0.042       # vertical step per extra wrapped subtitle line
SUB_WRAP = 96


def finish(fig, ax, title, subtitle, note, path, wrap=SUB_WRAP, title_x=None):
    """Apply the house header/footer and save.

    Departs from the site template in exactly one way: the subtitle wraps
    instead of running as a single line. A one-line subtitle reproduces the
    site layout precisely; each extra line lowers the axes by LINE_H.

    title_x overrides the left alignment. The house rule aligns the title with
    ax.get_position().x0, which assumes the axes spine is the leftmost thing on
    the page. On a horizontal bar chart with long category labels the spine
    sits well right of the visible content - pass title_x there.
    """
    sns.despine(ax=ax)
    ax.grid(False)
    ax.tick_params(axis="both", labelsize=FS_TICK)

    lines = textwrap.wrap(subtitle, wrap) or [""]
    if len(lines) > 2:
        raise ValueError(
            f"subtitle wraps to {len(lines)} lines (max 2): {subtitle[:60]}...")
    left_x = ax.get_position().x0 if title_x is None else title_x
    fig.subplots_adjust(top=TOP - LINE_H * (len(lines) - 1))

    fig.suptitle(title, fontsize=FS_TITLE, weight="bold",
                 x=left_x, ha="left", y=Y_TITLE)
    for i, line in enumerate(lines):
        fig.text(left_x, Y_SUBTITLE - LINE_H * i, line,
                 fontsize=FS_SUBTITLE, ha="left")
    fig.text(0.9, 0.01, note, fontsize=FS_NOTE, style="italic", ha="right")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight", transparent=True)
    print(f"  saved {os.path.basename(path)}  ({len(lines)}-line subtitle)")
    plt.close(fig)


def legend(ax, *args, **kw):
    """House legend: no frame, fontsize 14. Passes positional args through."""
    kw.setdefault("frameon", False)
    kw.setdefault("fontsize", FS_LEGEND)
    return ax.legend(*args, **kw)