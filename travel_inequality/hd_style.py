"""Hockey Decoded figure style, vendored for the travel-inequality analysis.

Copied verbatim from scripts/career-player-tenure/hd_style.py so this folder
stands alone and can be deleted without touching the site. TEAM_COLORS and
TEAM_NAMES are copied from app/config/team_colors.py for the same reason;
DIVISION / CONFERENCE are new here.

transparent=True matters: the site background is --bg-cream #fbf8f1, so a
figure saved on white renders as a white slab on a cream page.
"""
import os
import textwrap

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

try:
    import seaborn as sns
except ImportError:                     # the repo .venv has no seaborn
    class _Sns:
        @staticmethod
        def despine(ax=None, top=True, right=True, left=False, bottom=False):
            ax = ax or plt.gca()
            for side, off in (("top", top), ("right", right),
                              ("left", left), ("bottom", bottom)):
                if off:
                    ax.spines[side].set_visible(False)
    sns = _Sns()

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


def readable(hex_color, max_lum=0.52):
    """Darken a team colour until it reads against a light background.

    The house team palette is deliberately muted, and several colours - Los
    Angeles silver, Utah pale blue, Pittsburgh and Boston gold - sit at almost
    exactly the luminance of a cream page or a grey percentile band. Scaling RGB
    down preserves the hue while forcing enough contrast to see the line.
    """
    import matplotlib.colors as mcolors
    r, g, b = mcolors.to_rgb(hex_color)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    if lum <= max_lum:
        return hex_color
    f = max_lum / lum
    return mcolors.to_hex((r * f, g * f, b * f))


def distinct_colors(teams, max_lum=0.52, min_sep=0.14):
    """Team colours for a highlighted set, with near-duplicates pulled apart.

    The house palette was built for one-team-at-a-time use, so several clubs
    share a shade: Pittsburgh #E6BD50 and Boston #E6C760 are the same gold,
    Montreal and Calgary the same dusty red, Buffalo and Toronto the same navy.
    Put two of a pair on one chart and the lines are genuinely ambiguous
    wherever they cross.

    Each colour keeps its hue and is darkened only as far as needed to clear
    `min_sep` in RGB distance from every colour already assigned - so the first
    team of a pair looks exactly as it should, and the second reads as a darker
    shade of the same colour rather than a different one.
    """
    import matplotlib.colors as mcolors
    out = {}
    for t in teams:
        c = readable(TEAM_COLORS[t], max_lum)
        for _ in range(12):
            rgb = np.array(mcolors.to_rgb(c))
            if all(np.linalg.norm(rgb - np.array(mcolors.to_rgb(o))) >= min_sep
                   for o in out.values()):
                break
            c = mcolors.to_hex(tuple(rgb * 0.82))
        out[t] = c
    return out


def legend(ax, *args, **kw):
    """House legend: no frame, fontsize 14. Passes positional args through."""
    kw.setdefault("frameon", False)
    kw.setdefault("fontsize", FS_LEGEND)
    return ax.legend(*args, **kw)

# team reference ------------------------------------------------------------
# TEAM_COLORS / TEAM_NAMES copied from app/config/team_colors.py. ARI is
# dropped: the franchise is UTA as of 2024-25 and cannot appear in a 2026-27
# schedule.

TEAM_COLORS = {
    "ANA": "#D9614B", "BOS": "#E6C760", "BUF": "#3A4F73", "CGY": "#CF5D65",
    "CAR": "#3D3D3D", "CHI": "#D05160", "COL": "#9A5161", "CBJ": "#3A4B6F",
    "DAL": "#3D7A6C", "DET": "#D54E54", "EDM": "#E76F2B", "FLA": "#C59F40",
    "LAK": "#B5BDC0", "MTL": "#B55560", "MIN": "#3D735E", "NSH": "#E6C560",
    "NYR": "#4378B0", "NYI": "#3D68A3", "NJD": "#CF5D65", "OTT": "#D2546A",
    "PHI": "#E08363", "PIT": "#E6BD50", "SJS": "#3D8896", "STL": "#3D7ABD",
    "TBL": "#3D5C8C", "TOR": "#3D5B88", "VAN": "#3A567E", "WSH": "#C14E5C",
    "WPG": "#3A4F73", "VGK": "#9A8968", "SEA": "#A1DBDB", "UTA": "#8AB9E8",
}

TEAM_NAMES = {
    "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
    "CGY": "Calgary Flames", "CAR": "Carolina Hurricanes",
    "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche",
    "CBJ": "Columbus Blue Jackets", "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers",
    "FLA": "Florida Panthers", "LAK": "Los Angeles Kings",
    "MTL": "Montreal Canadiens", "MIN": "Minnesota Wild",
    "NSH": "Nashville Predators", "NYR": "New York Rangers",
    "NYI": "New York Islanders", "NJD": "New Jersey Devils",
    "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins", "SEA": "Seattle Kraken",
    "SJS": "San Jose Sharks", "STL": "St. Louis Blues",
    "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs",
    "VAN": "Vancouver Canucks", "WSH": "Washington Capitals",
    "WPG": "Winnipeg Jets", "VGK": "Vegas Golden Knights",
    "UTA": "Utah Mammoth",
}

DIVISION = {
    # Eastern
    "BOS": "Atlantic", "BUF": "Atlantic", "DET": "Atlantic", "FLA": "Atlantic",
    "MTL": "Atlantic", "OTT": "Atlantic", "TBL": "Atlantic", "TOR": "Atlantic",
    "CAR": "Metropolitan", "CBJ": "Metropolitan", "NJD": "Metropolitan",
    "NYI": "Metropolitan", "NYR": "Metropolitan", "PHI": "Metropolitan",
    "PIT": "Metropolitan", "WSH": "Metropolitan",
    # Western
    "CHI": "Central", "COL": "Central", "DAL": "Central", "MIN": "Central",
    "NSH": "Central", "STL": "Central", "UTA": "Central", "WPG": "Central",
    "ANA": "Pacific", "CGY": "Pacific", "EDM": "Pacific", "LAK": "Pacific",
    "SJS": "Pacific", "SEA": "Pacific", "VAN": "Pacific", "VGK": "Pacific",
}

CONFERENCE = {t: ("Eastern" if d in ("Atlantic", "Metropolitan") else "Western")
              for t, d in DIVISION.items()}

DIVISION_ORDER = ["Atlantic", "Metropolitan", "Central", "Pacific"]
CONF_COLORS = {"Eastern": COL_BLUE_PALE, "Western": COL_OIL_ORANGE}
DIV_COLORS = {"Atlantic": COL_BLUE_DARK, "Metropolitan": COL_BLUE_PALE,
              "Central": COL_GRAY, "Pacific": COL_OIL_ORANGE}
