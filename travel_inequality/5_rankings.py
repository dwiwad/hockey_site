"""5_rankings.py - one ranked bar chart per travel metric.

Reads  data/team_travel.parquet
Writes figures/rankings/rank_NN_<metric>.png  (20 figures)

fig2 in 3_figures.py ranks the 32 teams on total distance. This does the same
for every other measure in the analysis, so each element of the Travel Burden
Index - and the extras that feed it - can be looked at on its own.

Written for cell-by-cell execution in Spyder (# %% markers), like the other
stages.

Titles are generated from the data rather than written by hand. A hand-written
headline goes stale the moment a number moves, and with twenty figures that is
a question of when, not if. Ties are handled explicitly: where several teams
share the extreme the title says so instead of silently naming the first.
"""

# %% imports and configuration
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

try:
    HERE = Path(__file__).resolve().parent
except NameError:                       # Spyder cell execution
    HERE = Path("/Users/dwiwad/dev/hockey_site/travel_inequality")
sys.path.insert(0, str(HERE))

import hd_style as hd
from hd_style import (COL_BLUE_DARK, DIVISION, DIVISION_ORDER, DIV_COLORS,
                      TEAM_NAMES, finish)

DATA = HERE / "data"
FIGS = HERE / "figures" / "rankings"
FIGS.mkdir(parents=True, exist_ok=True)
NOTE = "Data: NHL API (club-schedule-season), 2026-27 regular season"

tt = pd.read_parquet(DATA / "team_travel.parquet")
tt["division"] = tt.team.map(DIVISION)
# Central is the pale house grey and disappears against cream at bar size
tt["color"] = tt.division.map({**DIV_COLORS, "Central": "#6E7787"})
print(f"{len(tt)} teams")


def gini(x):
    """Gini coefficient of a non-negative vector. 0 = perfectly even."""
    x = np.sort(np.asarray(x, dtype=float))
    n, total = len(x), x.sum()
    if total == 0:
        return 0.0
    i = np.arange(1, n + 1)
    return (2 * (i * x).sum()) / (n * total) - (n + 1) / n


# %% the metrics
# col, slug, x-axis label, value format, title verb phrase, higher_is_worse
METRICS = [
    # -- distance
    ("total_km", "distance_flown", "Kilometres flown over the season",
     "{:,.0f}", "fly the farthest", "{:,.0f} km", True),
    ("n_flights", "flights_taken", "Flights over 400 km",
     "{:,.0f}", "take the most flights", "{:.0f}", True),
    ("mean_flight_km", "mean_flight_length", "Mean length of a flight (km)",
     "{:,.0f}", "have the longest average flight", "{:,.0f} km", True),
    ("max_leg_km", "longest_single_flight", "Longest single flight (km)",
     "{:,.0f}", "take the longest single flight", "{:,.0f} km", True),
    # -- time away
    ("road_days", "days_on_the_road", "Days living out of a hotel",
     "{:,.0f}", "spend the most days on the road", "{:.0f}", True),
    ("n_trips", "road_trips", "Separate road trips",
     "{:,.0f}", "make the most separate road trips", "{:.0f}", True),
    ("longest_trip_days", "longest_trip_days", "Longest road trip (days)",
     "{:,.0f}", "have the longest road trip", "{:.0f} days", True),
    ("longest_trip_games", "longest_trip_games", "Longest road trip (games)",
     "{:,.0f}", "play the most games in one road trip", "{:.0f}", True),
    ("longest_trip_km", "longest_trip_km", "Longest road trip (km flown)",
     "{:,.0f}", "fly the farthest on a single road trip", "{:,.0f} km", True),
    # -- circadian
    ("tz_crossings", "time_zone_hours", "Time-zone hours crossed",
     "{:,.0f}", "cross the most time-zone hours", "{:.0f}", True),
    ("eastward_hours", "eastward_hours", "Eastward time-zone hours",
     "{:,.0f}", "cross the most hours eastward", "{:.0f}", True),
    # -- density
    ("b2b", "back_to_backs", "Games on consecutive nights",
     "{:,.0f}", "play the most back-to-backs", "{:.0f}", True),
    ("b2b_with_travel", "back_to_backs_with_travel",
     "Back-to-backs requiring a new city",
     "{:,.0f}", "play the most back-to-backs in two cities", "{:.0f}", True),
    ("b2b_travel_km", "back_to_back_km", "Kilometres flown between back-to-backs",
     "{:,.0f}", "fly the farthest between back-to-backs", "{:,.0f} km", True),
    ("three_in_four", "three_games_in_four_nights", "Three games in four nights",
     "{:,.0f}", "face the most three-in-four stretches", "{:.0f}", True),
    # -- recovery
    ("rest_deficit_games", "rest_deficit_games",
     "Games started against a better-rested opponent",
     "{:,.0f}", "most often face a better-rested opponent", "{:.0f} games", True),
    ("mean_rest_days", "mean_rest_days", "Mean days of rest between games",
     "{:.2f}", "get the least rest between games", "{:.2f} days", False),
    # -- lumpiness
    ("week_km_gini", "lumpiness", "Gini of weekly distance, within team",
     "{:.3f}", "have the most concentrated travel", "{:.3f}", True),
    ("max_7day_km", "worst_7_day_stretch", "Heaviest seven days of travel (km)",
     "{:,.0f}", "have the heaviest single week", "{:,.0f} km", True),
    ("max_14day_km", "worst_14_day_stretch", "Heaviest fortnight of travel (km)",
     "{:,.0f}", "have the heaviest fortnight", "{:,.0f} km", True),
]


def leaders(col, higher_is_worse):
    """Team(s) at the hard end of a metric, and the value. Ties included."""
    v = tt[col].astype(float)
    extreme = v.max() if higher_is_worse else v.min()
    who = tt.loc[v == extreme, "team"].tolist()
    return who, extreme


def phrase(who):
    """A subject that reads correctly whether one team leads or several tie.

    NHL club names are plural nouns - "the Golden Knights fly", "the Jets fly" -
    so the verb agrees either way and no singular/plural branch is needed.
    """
    if len(who) == 1:
        return TEAM_NAMES[who[0]]
    if len(who) == 2:
        return f"{TEAM_NAMES[who[0]]} and {TEAM_NAMES[who[1]]}"
    return f"{len(who)} teams"


# %% draw
rows = []
for i, (col, slug, xlabel, fmt, verb, vfmt, worse_high) in enumerate(METRICS, 1):
    v = tt[col].astype(float)
    who, val = leaders(col, worse_high)
    g, lo, hi = gini(v), v.min(), v.max()

    d = tt.sort_values(col, ascending=worse_high)
    fig, ax = plt.subplots(figsize=(12, 11))
    ax.barh(d.team, d[col], color=d.color, height=0.72)
    ax.set_xlabel(xlabel, fontsize=hd.FS_XAXIS_LABEL)
    ax.margins(x=0.15, y=0.012)
    if hi >= 10_000:
        ax.xaxis.set_major_formatter(lambda x, _: f"{x/1000:,.0f}k" if x else "0")
    for y, val_ in zip(d.team, d[col]):
        ax.text(val_ + ax.get_xlim()[1] * 0.008, y, fmt.format(val_),
                va="center", fontsize=11, color=COL_BLUE_DARK)
    ax.legend(handles=[Patch(facecolor="#6E7787" if k == "Central" else DIV_COLORS[k],
                             label=k) for k in DIVISION_ORDER],
              frameon=False, fontsize=hd.FS_LEGEND, loc="lower right")
    finish(fig, ax,
           f"{phrase(who)} {verb}: {vfmt.format(val)}",
           f"Gini across the 32 teams = {g:.3f}. Spread {fmt.format(lo)} to "
           f"{fmt.format(hi)}, a {hi/lo:.2f}× range.",
           NOTE, FIGS / f"rank_{i:02d}_{slug}.png", title_x=0.045)
    rows.append(dict(metric=col, gini=g, cv=v.std(ddof=0) / v.mean(),
                     ratio=hi / lo, low=lo, high=hi,
                     hardest=",".join(who)))

# %% verification and the summary the whole family exists to support
summary = pd.DataFrame(rows).sort_values("gini", ascending=False)
assert len(summary) == len(METRICS)
assert len(list(FIGS.glob("rank_*.png"))) == len(METRICS)

print(f"\n{len(METRICS)} rankings written to {FIGS}\n")
print(f"{'metric':28s} {'gini':>6} {'CV':>6} {'ratio':>7}  hardest")
for _, r in summary.iterrows():
    print(f"{r.metric:28s} {r.gini:>6.3f} {r.cv:>6.3f} {r.ratio:>6.2f}x  {r.hardest}")

d_rank = int((summary.metric == "total_km").argmax()) + 1
print(f"\nDistance ranks {d_rank} of {len(summary)} on Gini - the metric everyone "
      f"measures is\namong the MOST equally shared things about an NHL schedule.")
summary.to_csv(DATA / "metric_inequality.csv", index=False)
print(f"summary written to {DATA / 'metric_inequality.csv'}")
