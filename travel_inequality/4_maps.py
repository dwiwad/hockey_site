"""4_maps.py - the geographic and journey-shaped figures.

Reads  data/{stops,legs,trips,team_games,venues,team_travel,team_weeks}.parquet
Writes figures/map1..map7 .png

Written for cell-by-cell execution in Spyder (# %% markers), like the other
stages. Projection, great circles and the coastline all come from geo.py; there
is no mapping library in this environment and none is needed.

Why great circles and not straight lines: Vancouver to Toronto bows several
hundred kilometres north of the straight chord. On a map of a continent that is
plainly visible, and drawing the chord would quietly misrepresent every long
leg in the league.
"""

# %% imports and configuration
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

try:
    HERE = Path(__file__).resolve().parent
except NameError:                       # Spyder cell execution
    HERE = Path("/Users/dwiwad/dev/hockey_site/travel_inequality")
sys.path.insert(0, str(HERE))

import hd_style as hd
from hd_style import (COL_BLUE_DARK, COL_BLUE_PALE, COL_GRAY, COL_OIL_ORANGE,
                      DIVISION, DIVISION_ORDER, DIV_COLORS, TEAM_COLORS,
                      TEAM_NAMES)
from geo import albers, basemap, extent, flight_arc, load_layers

DATA, FIGS = HERE / "data", HERE / "figures"
FIGS.mkdir(parents=True, exist_ok=True)
NOTE = "Data: NHL API (club-schedule-season), 2026-27 regular season"

stops = pd.read_parquet(DATA / "stops.parquet")
legs = pd.read_parquet(DATA / "legs.parquet")
trips = pd.read_parquet(DATA / "trips.parquet")
tg = pd.read_parquet(DATA / "team_games.parquet")
ven = pd.read_parquet(DATA / "venues.parquet")
tt = pd.read_parquet(DATA / "team_travel.parquet")
weeks = pd.read_parquet(DATA / "team_weeks.parquet")

AIR = ven.drop_duplicates("iata").set_index("iata")[["lat", "lon", "city"]]
NHL_AIR = AIR.loc[sorted(set(ven.dropna(subset=["home_team"]).iata))]
load_layers("50m")                      # warm the cache before any drawing
# One extent for every map, so panels and figures are honestly comparable.
EXT = extent(NHL_AIR.lon.values, NHL_AIR.lat.values, pad=0.10)
OPP = tg.set_index(["team", "game_id"]).opp
print(f"{len(legs):,} legs, {len(NHL_AIR)} home airports")


# %% helpers
def save(fig, title, subtitle, path, x=0.045, y_title=0.982):
    """House header/footer for composite figures.

    hd_style.finish() calls subplots_adjust(top=), which squashes a gridspec
    layout, so these figures place the header themselves. Everything else -
    dpi, transparency, the italic source note - matches.

    Both lines are drawn with va="top" and the gap is derived from the figure
    height in inches, so the subtitle clears the title at any figure size.
    fig.suptitle defaults to va="top" while fig.text defaults to va="baseline",
    and mixing the two is what had the subtitle sitting on top of the title.
    """
    gap = (hd.FS_TITLE * 1.55) / (fig.get_figheight() * 72)
    fig.text(x, y_title, title, fontsize=hd.FS_TITLE, weight="bold",
             ha="left", va="top")
    fig.text(x, y_title - gap, subtitle, fontsize=hd.FS_SUBTITLE,
             ha="left", va="top")
    fig.text(0.94, 0.012, NOTE, fontsize=hd.FS_NOTE, style="italic", ha="right")
    fig.savefig(path, dpi=300, bbox_inches="tight", transparent=True)
    print(f"  saved {path.name}")
    plt.close(fig)


def arc(ax, a, b, amp=3.0, bow=0.055, **kw):
    """Draw one leg between two IATA codes as a curved flight path."""
    p, q = AIR.loc[a], AIR.loc[b]
    return ax.plot(*flight_arc(p.lon, p.lat, q.lon, q.lat, amp=amp, bow=bow), **kw)


def trip_legs(team, start):
    """The legs of one road trip, plus the flight home that ends it.

    Returns (outbound_and_between, home_leg_or_None). The trip's own km is the
    sum of the first; the flight home is charged to the next home game, so it
    is returned separately and drawn dashed.
    """
    tid = trips[(trips.team == team) & (trips.start == pd.Timestamp(start))].trip_id.iloc[0]
    away = stops[(stops.team == team) & (stops.trip_id == tid) & stops.is_away_game]
    out = legs[legs.stop_index.isin(away.index)].sort_values("stop_index")
    nxt = legs[(legs.team == team) & (legs.stop_index == away.index[-1] + 1)]
    return out, (nxt.iloc[0] if len(nxt) else None)


def place_labels(ax, pts, fontsize=10.5, color=None, pad=4.0, lead_at=30.0):
    """Annotate map points, choosing a slot that hits nothing and stays on the map.

    Airports cluster hard in this data - Los Angeles and Anaheim are 58 km
    apart, Newark and JFK 33 - so any fixed offset guarantees collisions, and
    counting neighbours and alternating above/below is not enough either: a
    label is wide enough to lie across a dot two hundred kilometres away.

    So this works in display pixels, estimates each label's box, and takes the
    first candidate slot whose box contains no other airport, overlaps no label
    already placed, AND lies inside the axes. Two rules matter:

    * Without the in-axes test a crowded label walks off the edge of the map -
      that is how "Anaheim (SNA)" ended up under the legend, labelling nothing.
    * When the only free slot is far from its dot, a leader line is drawn, the
      way an atlas does it. A distant label with no connector is worse than no
      label, because it looks like it belongs to whatever it landed next to.
    """
    color = color or COL_BLUE_DARK
    ax.figure.canvas.draw()                     # transData needs a live layout
    px_per_pt = ax.figure.dpi / 72.0
    cw, lh = fontsize * 0.56 * px_per_pt, fontsize * 1.30 * px_per_pt
    dots = [ax.transData.transform((x, y)) for x, y, _ in pts]
    ab = ax.get_window_extent()

    def box(cx, cy, w, h):
        return (cx - w / 2 - pad, cy - h / 2 - pad,
                cx + w / 2 + pad, cy + h / 2 + pad)

    def hits(b, others):
        return any(not (b[2] < o[0] or b[0] > o[2] or b[3] < o[1] or b[1] > o[3])
                   for o in others)

    def inside(b):
        return (b[0] >= ab.x0 and b[2] <= ab.x1
                and b[1] >= ab.y0 and b[3] <= ab.y1)

    placed = []
    for (dx0, dy0), (x, y, txt) in zip(dots, pts):
        w = max(len(txt), 1) * cw
        slots = []
        for ring in range(5):
            slots += [(0, -(13 + 15 * ring) * px_per_pt - lh / 2),
                      (0, (13 + 15 * ring) * px_per_pt + lh / 2),
                      ((12 + 14 * ring) * px_per_pt + w / 2, 0),
                      (-(12 + 14 * ring) * px_per_pt - w / 2, 0),
                      ((12 + 14 * ring) * px_per_pt + w / 2,
                       -(13 + 15 * ring) * px_per_pt),
                      (-(12 + 14 * ring) * px_per_pt - w / 2,
                       -(13 + 15 * ring) * px_per_pt)]
        chosen, ok = slots[0], False
        others = [box(ox, oy, 1, 1) for ox, oy in dots
                  if (ox, oy) != (dx0, dy0)]
        for dx, dy in slots:
            b = box(dx0 + dx, dy0 + dy, w, lh)
            if inside(b) and not hits(b, others) and not hits(b, placed):
                chosen, ok = (dx, dy), True
                break
        dx, dy = chosen
        placed.append(box(dx0 + dx, dy0 + dy, w, lh))
        far = np.hypot(dx, dy) / px_per_pt > lead_at
        ax.annotate(txt, (x, y), textcoords="offset points",
                    xytext=(dx / px_per_pt, dy / px_per_pt),
                    ha="center", va="center", fontsize=fontsize, color=color,
                    zorder=8,
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.7,
                                    alpha=0.55, shrinkA=2, shrinkB=6)
                    if far else None)


def rest_days(team, dates):
    """Days between consecutive games, for the timeline strip."""
    return [np.nan] + [(b - a).days for a, b in zip(dates[:-1], dates[1:])]


# %% maps 1-3 - the anatomy of one road trip
TRIPS_TO_DRAW = [
    ("TOR", "2026-12-26",
     "Toronto spends Christmas and New Year crossing the continent twice",
     "Six games in thirteen days: Montreal, then three time zones west for the "
     "California swing, then three back east."),
    ("OTT", "2026-10-27",
     "The worst road trip of the season: nine days, 8,402 km, six time zones",
     "Out three zones to Vegas, down the California coast, then straight back "
     "east to Buffalo \u2014 without going home."),
    ("TBL", "2027-03-03",
     "The league's most concentrated stretch: 1,169 km a day for six days",
     "Tampa play four games in six days across four cities, the hardest "
     "kilometres-per-day of any trip in 2026-27."),
]

for i, (team, start, title, subtitle) in enumerate(TRIPS_TO_DRAW, start=1):
    out, home_leg = trip_legs(team, start)
    col = TEAM_COLORS[team]
    home_iata = ven.loc[ven.home_team == team, "iata"].iloc[0]

    # Crop to the trip rather than to the league: the continental extent leaves
    # a transcontinental trip floating in a sea of empty Canada and Mexico.
    visited_codes = [out.iloc[0].from_iata] + list(out.to_iata) + [home_iata]
    sub = AIR.loc[sorted(set(visited_codes))]
    TEXT = extent(sub.lon.values, sub.lat.values, pad=0.21)

    # Size the figure FROM the map's aspect rather than guessing at it. An
    # equal-aspect axes shrinks its own box to honour the data ratio, so a
    # figure whose rows do not already match leaves a band of dead space above
    # and below the continent. These are inches.
    L, R, HEAD, TLINE, FOOT, LEG = 0.03, 0.97, 1.35, 2.30, 0.55, 0.42
    FIG_W = 12.5
    map_w = FIG_W * (R - L)
    map_h = map_w * (TEXT[3] - TEXT[2]) / (TEXT[1] - TEXT[0])
    FIG_H = HEAD + map_h + LEG + TLINE + FOOT

    fig = plt.figure(figsize=(FIG_W, FIG_H))
    ax = fig.add_axes([L, (FOOT + TLINE + LEG) / FIG_H, R - L, map_h / FIG_H])
    basemap(ax, res="50m")
    ax.set_xlim(TEXT[0], TEXT[1])
    ax.set_ylim(TEXT[2], TEXT[3])

    # every other NHL city, for context
    gx, gy = albers(NHL_AIR.lon.values, NHL_AIR.lat.values)
    ax.scatter(gx, gy, s=13, color=COL_GRAY, alpha=0.55, zorder=2, linewidths=0)

    # the trip itself
    for n, (_, lg) in enumerate(out.iterrows(), start=1):
        arc(ax, lg.from_iata, lg.to_iata, color=col, zorder=4,
            lw=1.5 + 2.6 * lg.km / out.km.max(), solid_capstyle="round")
    if home_leg is not None:
        arc(ax, home_leg.from_iata, home_leg.to_iata, color=col, zorder=3,
            lw=1.6, ls=(0, (4, 3)), alpha=0.85)

    visited = [out.iloc[0].from_iata] + list(out.to_iata)
    seen = {}
    for n, code in enumerate(visited):
        px, py = albers(AIR.loc[code].lon, AIR.loc[code].lat)
        first = code not in seen
        seen.setdefault(code, []).append(n)
        if first:
            is_home = code == home_iata
            ax.scatter(px, py, s=210 if is_home else 150, zorder=6,
                       color="white", edgecolor=col, linewidth=2.4,
                       marker="s" if is_home else "o")
    # order labels: a city visited twice carries both numbers. The home arena
    # is stop zero and gets the marker, not a number.
    pts = []
    for code, ns in seen.items():
        px, py = albers(AIR.loc[code].lon, AIR.loc[code].lat)
        lbl = "/".join(str(n) for n in ns if n > 0)
        if lbl:
            ax.text(px, py, lbl, ha="center", va="center", zorder=7,
                    fontsize=9.5, weight="bold", color=col)
        pts.append((float(px), float(py), f"{AIR.loc[code].city} ({code})"))
    place_labels(ax, pts)

    # ---- the timeline strip -------------------------------------------------
    tl = fig.add_axes([L + 0.02, FOOT / FIG_H, (R - L) - 0.04, TLINE / FIG_H])
    dates = list(out.date)
    kms = list(out.km)
    opps = [OPP.get((team, g)) for g in out.arrive_for_game_id]
    rests = rest_days(team, dates)
    tl.plot(dates, [0] * len(dates), color=COL_GRAY, lw=1.2, zorder=1)
    for d, k, o, r, n in zip(dates, kms, opps, rests, range(1, len(dates) + 1)):
        b2b = r == 1
        tl.scatter(d, 0, s=170, zorder=3, color=COL_OIL_ORANGE if b2b else col,
                   edgecolor="white", linewidth=1.6)
        tl.text(d, 0, str(n), ha="center", va="center", fontsize=9,
                weight="bold", color="white", zorder=4)
        tl.annotate(f"@ {o}", (d, 0), textcoords="offset points",
                    xytext=(0, 20), ha="center", fontsize=12,
                    weight="bold", color=COL_BLUE_DARK)
        tl.annotate(f"{d.strftime('%b %-d')}", (d, 0), textcoords="offset points",
                    xytext=(0, 36), ha="center", fontsize=10, color=COL_GRAY)
        tl.annotate(f"{k:,.0f} km", (d, 0), textcoords="offset points",
                    xytext=(0, -26), ha="center", fontsize=11, color=col)
        if b2b:
            tl.annotate("back-to-back", (d, 0), textcoords="offset points",
                        xytext=(0, -41), ha="center", fontsize=9.5,
                        style="italic", color=COL_OIL_ORANGE)
        elif not np.isnan(r):
            tl.annotate(f"{int(r) - 1}d rest", (d, 0), textcoords="offset points",
                        xytext=(0, -41), ha="center", fontsize=9.5,
                        color=COL_GRAY)
    span = (dates[-1] - dates[0]).days
    tl.set_xlim(dates[0] - pd.Timedelta(days=span * 0.10),
                dates[-1] + pd.Timedelta(days=span * 0.10))
    tl.set_ylim(-0.9, 0.75)
    tl.axis("off")
    tot = out.km.sum()
    tl.text(0.5, -0.28,
            f"{len(dates)} games  ·  {span + 1} days  ·  {tot:,.0f} km flown"
            f"  ·  {tot / (span + 1):,.0f} km per day",
            transform=tl.transAxes, ha="center", fontsize=13,
            weight="bold", color=COL_BLUE_DARK)

    fig.legend(handles=[
        Line2D([], [], color=col, lw=2.6, label="Leg of the road trip"),
        Line2D([], [], color=col, lw=1.6, ls=(0, (4, 3)), label="Flight home"),
        Line2D([], [], marker="s", color="white", markeredgecolor=col,
               markeredgewidth=2, markersize=10, ls="", label="Home arena"),
    ], frameon=False, fontsize=hd.FS_LEGEND, ncol=3, loc="center",
        bbox_to_anchor=(0.5, (FOOT + TLINE + LEG * 0.45) / FIG_H))
    save(fig, title, subtitle, FIGS / f"map{i}_trip_{team}.png",
         y_title=1 - 0.22 / FIG_H)

# %% map 4 - the three heaviest and three lightest seasons
# Six panels rather than all thirty-two: at grid size the 50m coastline is mud,
# and the contrast that carries the argument is between the extremes anyway.
ranked = tt.sort_values("total_km", ascending=False).team.tolist()
PICK = ranked[:3] + ranked[-3:]
fig, axes = plt.subplots(2, 3, figsize=(16.5, 10.4))
fig.subplots_adjust(top=0.845, bottom=0.075, left=0.015, right=0.985,
                    wspace=0.03, hspace=0.16)
for i, (axp, team) in enumerate(zip(axes.ravel(), PICK)):
    # Two tones by row rather than team colours: the house team palette is
    # deliberately muted, and Vegas gold and Pittsburgh yellow simply vanish
    # against the cream land. This also makes the comparison the point.
    col = COL_OIL_ORANGE if i < 3 else COL_BLUE_DARK
    basemap(axp, res="50m", lw=0.5)
    axp.set_xlim(EXT[0], EXT[1])
    axp.set_ylim(EXT[2], EXT[3])
    tl_ = legs[(legs.team == team) & (legs.km > 0)]
    for _, lg in tl_.iterrows():
        arc(axp, lg.from_iata, lg.to_iata, color=col, lw=0.85, alpha=0.42,
            zorder=4, solid_capstyle="round")
    hx, hy = albers(*AIR.loc[ven.loc[ven.home_team == team, "iata"].iloc[0],
                             ["lon", "lat"]])
    axp.scatter(hx, hy, s=95, color="white", edgecolor=col, linewidth=2.2,
                zorder=7)
    r = tt[tt.team == team].iloc[0]
    axp.set_title(f"{TEAM_NAMES[team]}", fontsize=15, weight="bold",
                  color=COL_BLUE_DARK, pad=6)
    axp.text(0.5, -0.045, f"{r.total_km:,.0f} km   ·   {int(r.n_flights)} flights"
             f"   ·   {int(r.tz_crossings)} zone-hours",
             transform=axp.transAxes, ha="center", fontsize=12.5, color=col)
for row, lab in ((0, "The three heaviest schedules"),
                 (1, "The three lightest schedules")):
    axes[row][0].text(-0.02, 0.5, lab, transform=axes[row][0].transAxes,
                      rotation=90, va="center", ha="center", fontsize=13.5,
                      weight="bold", color=COL_GRAY)
save(fig, "The same league, two completely different jobs",
     "Every 2026-27 flight for the three farthest-travelling teams and the "
     "three least, on one projection and scale.",
     FIGS / "map4_extremes_small_multiples.png")

# %% map 5 - the league's flight network
pair = (legs[legs.km > 400]
        .assign(a=np.minimum(legs.from_iata, legs.to_iata),
                b=np.maximum(legs.from_iata, legs.to_iata))
        .groupby(["a", "b"]).size().rename("n").reset_index())
traffic = (pd.concat([pair.groupby("a").n.sum(), pair.groupby("b").n.sum()])
           .groupby(level=0).sum())
fig, ax = plt.subplots(figsize=(14, 10.5))
fig.subplots_adjust(top=0.88, bottom=0.03, left=0.02, right=0.98)
basemap(ax, res="50m")
NEXT = extent(NHL_AIR.lon.values, NHL_AIR.lat.values, pad=0.05)
ax.set_xlim(NEXT[0], NEXT[1])
ax.set_ylim(NEXT[2], NEXT[3])
nmax = pair.n.max()
for _, r in pair.sort_values("n").iterrows():
    arc(ax, r.a, r.b, color=COL_BLUE_PALE, zorder=3, amp=2.0, bow=0.035,
        lw=0.35 + 2.5 * (r.n / nmax) ** 0.75,
        alpha=0.16 + 0.62 * (r.n / nmax) ** 0.6, solid_capstyle="round")
net_pts = []
for code, n in traffic.items():
    px, py = albers(AIR.loc[code].lon, AIR.loc[code].lat)
    ax.scatter(px, py, s=20 + 190 * n / traffic.max(), zorder=6,
               color=COL_OIL_ORANGE, edgecolor="white", linewidth=1.1)
    net_pts.append((float(px), float(py), code))
place_labels(ax, net_pts, fontsize=9.5)
busiest = pair.nlargest(3, "n")
ax.text(0.015, 0.035,
        "Busiest pairs:  " + "   ·   ".join(
            f"{r.a}-{r.b} {int(r.n)}" for _, r in busiest.iterrows()),
        transform=ax.transAxes, fontsize=12, color=COL_BLUE_DARK)
save(fig, "The league's air network in one season",
     f"All {int(pair.n.sum()):,} flights over 400 km, aggregated to "
     f"{len(pair)} city pairs. Line weight is how often that route is flown.",
     FIGS / "map5_league_network.png")

# %% map 6 - the season as a calendar
SEASON_START = legs.date.min()
CAL_TEAMS = [("NYI", "the lumpiest schedule in the league"),
             ("WPG", "the most evenly spread")]
cmap = LinearSegmentedColormap.from_list(
    "hd_km", ["#F4EFE6", "#F5C9A8", COL_OIL_ORANGE, "#8C2600"])
vmax = max(legs[legs.team == t].groupby("date").km.sum().max()
           for t, _ in CAL_TEAMS)

fig, axes = plt.subplots(2, 1, figsize=(15, 8.4))
fig.subplots_adjust(top=0.845, bottom=0.10, left=0.055, right=0.90, hspace=0.42)
for axp, (team, blurb) in zip(axes, CAL_TEAMS):
    day = legs[legs.team == team].groupby("date").km.sum()
    gmes = tg[tg.team == team].set_index("game_date").is_home
    days = pd.date_range(SEASON_START, legs.date.max(), freq="D")
    grid = np.full((7, (len(days) // 7) + 1), np.nan)
    for d in days:
        w, dow = (d - SEASON_START).days // 7, (d - SEASON_START).days % 7
        grid[dow, w] = day.get(d, 0.0)
    im = axp.imshow(grid, cmap=cmap, vmin=0, vmax=vmax, aspect="auto",
                    origin="upper")
    for d in days:                       # ring the days with a game
        if d not in gmes.index:
            continue
        w, dow = (d - SEASON_START).days // 7, (d - SEASON_START).days % 7
        home = bool(gmes.loc[d]) if np.isscalar(gmes.loc[d]) else bool(gmes.loc[d].iloc[0])
        axp.scatter(w, dow, s=13, zorder=4,
                    facecolor="white" if home else COL_BLUE_DARK,
                    edgecolor=COL_BLUE_DARK, linewidth=0.7)
    axp.set_yticks(range(7))
    axp.set_yticklabels(["M", "T", "W", "T", "F", "S", "S"], fontsize=10)
    ticks = [i for i, d in enumerate(days[::7]) if d.day <= 7]
    axp.set_xticks(ticks)
    axp.set_xticklabels([days[::7][i].strftime("%b") for i in ticks], fontsize=11)
    axp.tick_params(length=0)
    for s in axp.spines.values():
        s.set_visible(False)
    g = tt.loc[tt.team == team, "week_km_gini"].iloc[0]
    km = tt.loc[tt.team == team, "total_km"].iloc[0]
    axp.set_title(f"{TEAM_NAMES[team]} — {blurb}   "
                  f"(weekly Gini {g:.3f}, {km:,.0f} km)",
                  fontsize=14, weight="bold", color=COL_BLUE_DARK, loc="left",
                  pad=8)
cb = fig.colorbar(im, ax=axes, fraction=0.020, pad=0.015)
cb.set_label("Kilometres flown that day", fontsize=11)
cb.outline.set_visible(False)
fig.legend(handles=[
    Line2D([], [], marker="o", ls="", markerfacecolor="white",
           markeredgecolor=COL_BLUE_DARK, markersize=7, label="Home game"),
    Line2D([], [], marker="o", ls="", markerfacecolor=COL_BLUE_DARK,
           markeredgecolor=COL_BLUE_DARK, markersize=7, label="Road game")],
    frameon=False, fontsize=hd.FS_LEGEND, ncol=2, loc="lower left",
    bbox_to_anchor=(0.055, 0.005))
save(fig, "The same season, delivered two completely different ways",
     "Kilometres flown each day. The Islanders travel in bursts; Winnipeg "
     "grinds out a similar total almost every week.",
     FIGS / "map6_calendar_lumpiness.png")

# %% map 7 - time zones as a waveform, the three worst and three best
# Chosen off tz_crossings rather than by hand. The top three are clean (58, 56,
# 47). The bottom is Ottawa 20, Pittsburgh 22, and then a five-way tie at 24 -
# broken on how many flights actually move the clock, which is what the figure
# draws: Montreal 15, Florida 15, Buffalo 16, Philadelphia 17, Carolina 18.
# Montreal takes it on the shorter season of the two on 15.
ZONE = {-8: "Pacific", -7: "Mountain", -6: "Central", -5: "Eastern"}

zc = (legs[legs.tz_delta != 0].groupby("team").size().rename("zone_changing")
      .reindex(tt.team).fillna(0).astype(int))
rank = tt.set_index("team").join(zc)
worst = rank.sort_values(["tz_crossings", "zone_changing"],
                         ascending=[False, False]).index[:3].tolist()
best = rank.sort_values(["tz_crossings", "zone_changing", "total_km"],
                        ascending=[True, True, True]).index[:3].tolist()
SAW = [(t, "worst") for t in worst] + [(t, "best") for t in best]
print(f"  waveform teams - most zone-hours {worst}, fewest {best}")

fig, axes = plt.subplots(6, 1, figsize=(14, 13.6), sharex=True)
fig.subplots_adjust(top=0.905, bottom=0.048, left=0.115, right=0.978, hspace=0.42)
for axp, (team, grp) in zip(axes, SAW):
    r = rank.loc[team]
    col = COL_OIL_ORANGE if grp == "worst" else COL_BLUE_DARK
    s_ = stops[(stops.team == team) & stops.kind.eq("game")].sort_values("date")
    home_off = ven.loc[ven.home_team == team, "utc_std"].iloc[0]
    axp.axhspan(home_off - 0.42, home_off + 0.42, color=COL_GRAY, alpha=0.13,
                zorder=0)
    axp.step(s_.date, s_.utc_std, where="post", color=col, lw=1.7, zorder=3)
    away = s_[s_.utc_std != home_off]
    axp.scatter(away.date, away.utc_std, s=17, zorder=4, color=col,
                edgecolor="white", linewidth=0.5)
    axp.set_yticks(sorted(ZONE))
    axp.set_yticklabels([ZONE[z] for z in sorted(ZONE)], fontsize=11)
    axp.set_ylim(-8.7, -4.3)
    axp.tick_params(length=0)
    for side in ("top", "right", "left"):
        axp.spines[side].set_visible(False)
    axp.spines["bottom"].set_color(COL_GRAY)
    # every number in the title is read off the data, so it cannot drift
    axp.set_title(f"{TEAM_NAMES[team]}   ·   {r.tz_crossings:.0f} zone-hours"
                  f"   ·   {int(r.zone_changing)} of {int(r.n_flights)} flights "
                  f"move the clock", fontsize=13, weight="bold",
                  color=COL_BLUE_DARK, loc="left", pad=5)
# Group labels centred on their three panels, in figure coords - anchoring them
# to the first axes of each group puts them at the top of the group instead.
fig.canvas.draw()
for rows, lab, c in (((0, 1, 2), "MOST zone-hours", COL_OIL_ORANGE),
                     ((3, 4, 5), "FEWEST zone-hours", COL_BLUE_DARK)):
    tops = [axes[r].get_position() for r in rows]
    ymid = (max(b.y1 for b in tops) + min(b.y0 for b in tops)) / 2
    fig.text(0.028, ymid, lab, rotation=90, va="center", ha="center",
             fontsize=12.5, weight="bold", color=c)
axes[-1].xaxis.set_major_locator(mdates.MonthLocator())
axes[-1].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
axes[-1].tick_params(axis="x", labelsize=12)
fig.text(0.115, 0.016, "Shaded band = the team's own time zone",
         fontsize=hd.FS_NOTE, style="italic", color=COL_GRAY)
save(fig, "Jet lag, drawn as a waveform",
     "The clock at each night's venue across the season, for the three teams "
     "that cross the most time-zone hours and the three that cross the fewest.",
     FIGS / "map7_timezone_sawtooth.png")

# %% verification
print("\nverification")

# The Ottawa title asserts this is the season's worst road trip. That claim is
# a composite of seven measures, so it is checked here rather than trusted:
# distance, km/day, zone-hours, eastward hours, games per day, back-to-backs
# and rest-deficit games, each standardised across every trip of 3+ games.
_km = legs.set_index(legs.stop_index.astype(int)).km
_tz = legs.set_index(legs.stop_index.astype(int)).tz_delta
_aw = stops[stops.is_away_game].copy()
_aw["km"] = _km.reindex(_aw.index).values
_aw["tz"] = _tz.reindex(_aw.index).values
_r = tg[["game_id", "team", "rest_days"]]
_m = _r.merge(_r, on="game_id", suffixes=("", "_o"))
_oppr = _m[_m.team != _m.team_o].set_index(["team", "game_id"]).rest_days_o
_mine = tg.set_index(["team", "game_id"]).rest_days
_g = _aw.groupby(["team", "trip_id"])
T = _g.agg(start=("date", "first"), end=("date", "last"), n=("date", "size"),
           km=("km", "sum"), tz_abs=("tz", lambda v: v.abs().sum()),
           tz_east=("tz", lambda v: v.clip(lower=0).sum())).reset_index()
T["days"] = (T.end - T.start).dt.days + 1
T["kmpd"] = T.km / T.days
T["density"] = T.n / T.days
T["b2b"] = _g.date.apply(lambda v: (v.diff().dt.days == 1).sum()).values
T["rest_def"] = [int(np.nansum(_oppr.reindex(list(zip(sub.team, sub.game_id))).values
                               > _mine.reindex(list(zip(sub.team, sub.game_id))).values))
                 for _, sub in _g]
T = T[T.n >= 3]
for c in ["km", "kmpd", "tz_abs", "tz_east", "density", "b2b", "rest_def"]:
    T["z_" + c] = (T[c] - T[c].mean()) / T[c].std(ddof=0)
T["brutal"] = T[[c for c in T if c.startswith("z_")]].mean(axis=1)
top = T.nlargest(1, "brutal").iloc[0]
assert (top.team, str(top.start.date())) == ("OTT", "2026-10-27"), (
    f"the worst-trip title is stale: composite now favours {top.team} {top.start.date()}")
print(f"  worst trip: {top.team} {top.start.date()} ranks 1 of {len(T)} trips "
      f"of 3+ games on the composite (+{top.brutal:.2f})")
for team, start, *_ in TRIPS_TO_DRAW:
    out, _ = trip_legs(team, start)
    rec = trips[(trips.team == team) & (trips.start == pd.Timestamp(start))].iloc[0]
    assert abs(out.km.sum() - rec.km) < 1e-6, f"{team} arcs != trips.km"
    assert len(out) == rec.n_games
    print(f"  {team} {start}: {len(out)} arcs, {out.km.sum():,.0f} km — matches trips.parquet")
assert len(PICK) == 6 and len(set(PICK)) == 6
for t in PICK:
    n = len(legs[(legs.team == t) & (legs.km > 0)])
    assert n == int(tt.loc[tt.team == t, "n_flights"].iloc[0]) + \
        len(legs[(legs.team == t) & (legs.km > 0) & (legs.km <= 400)])
print(f"  small multiples: {PICK} — each panel's legs match legs.parquet")
for team, _ in CAL_TEAMS:
    tot = legs[legs.team == team].groupby("date").km.sum().sum()
    assert abs(tot - tt.loc[tt.team == team, "total_km"].iloc[0]) < 1e-6
    print(f"  {team} calendar sums to its season total")
assert pair.n.sum() == len(legs[legs.km > 400])
assert len(set(worst) | set(best)) == 6, "waveform picked a team twice"
assert rank.loc[worst, "tz_crossings"].min() > rank.loc[best, "tz_crossings"].max()
print(f"  waveform: worst {[f'{t} {int(rank.loc[t].tz_crossings)}' for t in worst]}"
      f"  best {[f'{t} {int(rank.loc[t].tz_crossings)}' for t in best]}")
print(f"  network: {int(pair.n.sum()):,} flights over {len(pair)} city pairs")
