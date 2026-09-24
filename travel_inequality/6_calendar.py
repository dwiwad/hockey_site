"""6_calendar.py - Part 2: calendar burden, and the trade-off against travel.

Reads  data/team_travel.parquet, data/team_games.parquet, data/legs.parquet,
       data/venues.parquet
Writes figures/part2/p2_01 .. p2_10 .png

Part 1 measures what geography imposes on a team: distance, time zones, nights
away. This measures what the schedule chooses - when the games fall, and who
the team meets - and then asks whether the two are related.

They are, strongly and negatively. What the analysis does NOT support is the
obvious reading of that. Tested before any of this was drawn:

  travel vs calendar          r = -0.587, permutation p = 0.0003   strong
  variance cancelled by it    var(sum) 0.410 vs 0.988 independent  58%
  "the East has it worse"     t = 1.70, p = 0.098                  n.s.
  calendar as division effect eta2 = 0.137, F = 1.5, p = 0.24      n.s.
  compensation is complete    combined still West-tilted p = 0.006 no

So this is a TEAM-level trade-off that does not map onto the conference map and
only partly undoes the geography. Every title here is written to respect that,
and the division figure states its own non-significance on its face.

Written for cell-by-cell execution in Spyder (# %% markers).
"""

# %% imports and configuration
import sys
from pathlib import Path

import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats

try:
    HERE = Path(__file__).resolve().parent
except NameError:                       # Spyder cell execution
    HERE = Path("/Users/dwiwad/dev/hockey_site/travel_inequality")
sys.path.insert(0, str(HERE))

import hd_style as hd
from hd_style import (COL_BLUE_DARK, COL_BLUE_PALE, COL_GRAY, COL_OIL_ORANGE,
                      DIVISION, DIVISION_ORDER, DIV_COLORS, TEAM_COLORS, TEAM_NAMES,
                      finish, readable, distinct_colors)

DATA = HERE / "data"
FIGS = HERE / "figures" / "part2"
FIGS.mkdir(parents=True, exist_ok=True)
NOTE = "Data: NHL API (club-schedule-season), 2026-27 regular season"
SEED = 20262027

TRAVEL_COLS = ["total_km", "tz_crossings", "road_days"]
CALENDAR_COLS = ["b2b_with_travel", "three_in_four", "rest_deficit_games"]
CAL_LABELS = {"b2b_with_travel": "Back-to-backs in two cities",
              "three_in_four": "Three games in four nights",
              "rest_deficit_games": "Facing a rested opponent"}
# Central's house grey vanishes on cream at bar size
DIV_C = {**DIV_COLORS, "Central": "#6E7787"}

tt = pd.read_parquet(DATA / "team_travel.parquet")
tt["division"] = tt.team.map(DIVISION)
tt["conf"] = np.where(tt.division.isin(["Atlantic", "Metropolitan"]), "East", "West")
tt["color"] = tt.division.map(DIV_C)


def z(s):
    s = s.astype(float)
    return (s - s.mean()) / s.std(ddof=0)


# the persisted composites must be reproducible from the raw columns
assert np.allclose(pd.concat([z(tt[c]) for c in TRAVEL_COLS], axis=1).mean(axis=1), tt.trav_z)
assert np.allclose(pd.concat([z(tt[c]) for c in CALENDAR_COLS], axis=1).mean(axis=1), tt.cal_z)
assert np.allclose((tt.trav_z + tt.cal_z) / 2, tt.comb)
print(f"{len(tt)} teams; composites verified against the raw columns")

STATS = {}      # every number quoted in a title or annotation lands here


def gini(x):
    x = np.sort(np.asarray(x, dtype=float))
    n, total = len(x), x.sum()
    if total == 0:
        return 0.0
    i = np.arange(1, n + 1)
    return (2 * (i * x).sum()) / (n * total) - (n + 1) / n


def leaders(col, high_is_worse=True):
    """Team(s) at the hard end, and the value. Ties named rather than hidden."""
    v = tt[col].astype(float)
    val = v.max() if high_is_worse else v.min()
    return tt.loc[v == val, "team"].tolist(), val


def phrase(who):
    if len(who) == 1:
        return TEAM_NAMES[who[0]]
    if len(who) == 2:
        return f"{TEAM_NAMES[who[0]]} and {TEAM_NAMES[who[1]]}"
    return f"{len(who)} teams"


def div_legend(ax, **kw):
    kw.setdefault("loc", "lower right")
    return ax.legend(handles=[Patch(facecolor=DIV_C[k], label=k)
                              for k in DIVISION_ORDER],
                     frameon=False, fontsize=hd.FS_LEGEND, **kw)


def eta2(col, by="division"):
    grp = [tt.loc[tt[by] == g, col].values for g in sorted(tt[by].unique())]
    F, p = stats.f_oneway(*grp)
    grand = tt[col].mean()
    ssb = sum(len(x) * (x.mean() - grand) ** 2 for x in grp)
    return ssb / ((tt[col] - grand) ** 2).sum(), F, p


# %% p2_01 - the calendar burden ranking
who, val = leaders("cal_z")
g_cal = gini(tt.b2b_with_travel + tt.three_in_four + tt.rest_deficit_games)
STATS["calendar leader"] = f"{who} {val:+.2f}"

d = tt.sort_values("cal_z")
fig, ax = plt.subplots(figsize=(12, 11))
ax.barh(d.team, d.cal_z, color=d.color, height=0.72)
ax.axvline(0, color=COL_GRAY, lw=1)
ax.set_xlabel("Calendar burden  (higher is harder)", fontsize=hd.FS_XAXIS_LABEL)
ax.margins(x=0.10, y=0.012)
for y, v in zip(d.team, d.cal_z):
    ax.text(v + (0.03 if v >= 0 else -0.03), y, f"{v:+.2f}", va="center",
            ha="left" if v >= 0 else "right", fontsize=11, color=COL_BLUE_DARK)
div_legend(ax)
finish(fig, ax,
       f"{phrase(who)} draw the league's hardest calendar",
       "Back-to-backs that change city, three-games-in-four-nights, and games "
       "started against a better-rested opponent.",
       NOTE, FIGS / "p2_01_calendar_ranking.png", title_x=0.045)

# %% p2_02 - what the calendar burden is made of
# Same construction as fig9: the composite is a MEAN of three z-scores, so each
# contributes exactly its own z divided by three, and the three sum to the bar.
# Same trap too - segments straddle zero, so the drawn bar is wider than the
# score. The net dot has to win the visual fight.
COMP_COLORS = [COL_BLUE_DARK, "#8A8578", COL_OIL_ORANGE]
d = tt.sort_values("cal_z")
contrib = pd.concat([z(d[c]) for c in CALENDAR_COLS], axis=1) / len(CALENDAR_COLS)
contrib.columns = CALENDAR_COLS
assert np.allclose(contrib.sum(axis=1), d.cal_z), "segments must sum to the score"

fig, ax = plt.subplots(figsize=(13.5, 11.5))
pos = np.zeros(len(d)); neg = np.zeros(len(d))
for col, c in zip(CALENDAR_COLS, COMP_COLORS):
    v = contrib[col].values
    left = np.where(v >= 0, pos, neg + v)
    ax.barh(d.team, np.abs(v), left=left, color=c, height=0.7,
            label=CAL_LABELS[col], edgecolor="white", linewidth=0.4, zorder=3)
    pos = pos + np.where(v >= 0, v, 0)
    neg = neg + np.where(v < 0, v, 0)
ax.axvline(0, color=COL_BLUE_DARK, lw=1.1, zorder=4)
ax.scatter(d.cal_z, d.team, s=170, color="white", zorder=6, linewidths=0)
ax.scatter(d.cal_z, d.team, s=78, color=COL_BLUE_DARK, zorder=7,
           edgecolor="white", linewidth=1.3, label="Net score")
xmax = pos.max() + 0.40
ax.set_xlim(neg.min() - 0.05, xmax)
for y, v in zip(d.team, d.cal_z):
    ax.text(xmax - 0.02, y, f"{v:+.2f}", va="center", ha="right", fontsize=11,
            weight="bold", color=COL_BLUE_DARK)
ax.axvline(xmax - 0.34, color=COL_GRAY, lw=0.8, alpha=0.5, zorder=2)
for lbl in ax.get_yticklabels():
    lbl.set_color(DIV_C[DIVISION[lbl.get_text()]])
    lbl.set_fontweight("bold")
ax.set_xlabel("Each component's contribution  (its z-score ÷ 3)",
              fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylim(-3.4, len(d) - 0.35)
ax.legend(frameon=False, fontsize=hd.FS_LEGEND, loc="lower center", ncol=2,
          handlelength=1.6, columnspacing=2.0)
finish(fig, ax,
       "Pittsburgh's calendar is hard in all three ways at once",
       "Segments left of zero make a schedule easier, right of zero harder. "
       "The dot is the net.",
       NOTE, FIGS / "p2_02_calendar_composition.png", title_x=0.045)
assert (tt.loc[tt.team == "PIT", CALENDAR_COLS].apply(
    lambda r: all(z(tt[c]).loc[r.name] > 0 for c in CALENDAR_COLS), axis=1)).all(), \
    "the title claims Pittsburgh is above average on all three"

# %% p2_03 - the three components as ranks
d = tt.sort_values("cal_rank")
mat = np.column_stack([tt.set_index("team").loc[d.team, c]
                       .rank(ascending=False, method="min").values
                       for c in CALENDAR_COLS])
from matplotlib.colors import LinearSegmentedColormap
cmap = LinearSegmentedColormap.from_list("hd_rank", [COL_OIL_ORANGE, "#F0E4D8", COL_BLUE_PALE])
fig, ax = plt.subplots(figsize=(8.5, 12))
im = ax.imshow(mat, cmap=cmap, aspect="auto", vmin=1, vmax=32)
ax.set_xticks(range(3))
ax.set_xticklabels(["Back-to-backs\nin two cities", "Three games\nin four nights",
                    "Facing a rested\nopponent"], fontsize=12)
ax.set_yticks(range(len(d)))
ax.set_yticklabels([f"{r:>2}  {t}" for r, t in zip(d.cal_rank, d.team)], fontsize=11)
ax.tick_params(length=0)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        v = int(mat[i, j])
        ax.text(j, i, v, ha="center", va="center", fontsize=10,
                color=COL_BLUE_DARK if 8 < v < 26 else "white")
cb = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
cb.set_label("League rank  (1 = hardest)", fontsize=12)
cb.outline.set_visible(False)
finish(fig, ax,
       "The three calendar burdens do not travel together",
       "Rank on each component, teams ordered by the composite. Orange is a "
       "hard draw, blue an easy one.",
       NOTE, FIGS / "p2_03_component_ranks.png", title_x=0.045)

# %% p2_04 - calendar burden accumulating across the season
# Same construction as fig10, and cleaner here: all three components are counts
# assigned to a specific game, so unlike trip length they decompose into weekly
# increments exactly. z(X) = sum_w [(x_w - mu/W)/sigma], so the running total
# lands precisely on the season score. Zero is league-average pace.
legs = pd.read_parquet(DATA / "legs.parquet")
tg = pd.read_parquet(DATA / "team_games.parquet")
ven = pd.read_parquet(DATA / "venues.parquet")
START = legs.date.min()
NW = int((legs.date.max() - START).days // 7) + 1
teams = sorted(tt.team)


def wk(dates):
    return ((pd.to_datetime(pd.Series(list(dates))) - START).dt.days // 7).astype(int).values


idx = pd.MultiIndex.from_product([teams, range(NW)], names=["team", "week"])
W = pd.DataFrame(0.0, index=idx, columns=CALENDAR_COLS)

eu = set(ven.loc[ven.region.eq("Europe"), "venue"])
itin = tg[~tg.venue.isin(eu)].sort_values(["team", "game_date", "game_id"])
for team, g in itin.groupby("team"):
    d_, ia = g.game_date.reset_index(drop=True), g.iata.reset_index(drop=True)
    for mask, col in ((d_.diff().dt.days.eq(1) & ia.ne(ia.shift()), "b2b_with_travel"),
                      ((d_ - d_.shift(2)).dt.days.le(3), "three_in_four")):
        for w_ in wk(d_[mask]):
            W.loc[(team, w_), col] += 1
_r = tg[["game_id", "team", "rest_days"]]
_m = _r.merge(_r, on="game_id", suffixes=("", "_o"))
_m = _m[_m.team != _m.team_o].dropna(subset=["rest_days", "rest_days_o"])
_d = _m[_m.rest_days_o > _m.rest_days].merge(tg[["team", "game_id", "game_date"]],
                                             on=["team", "game_id"])
for team, g in _d.groupby("team"):
    for w_ in wk(g.game_date):
        W.loc[(team, w_), "rest_deficit_games"] += 1

tot = W.groupby(level=0).sum()
for col in CALENDAR_COLS:
    assert np.allclose(tot[col].reindex(teams).values,
                       tt.set_index("team")[col].reindex(teams).values.astype(float)), \
        f"weekly {col} does not sum to the season total"
inc = pd.DataFrame({c: (W[c] - tot[c].mean() / NW) / tot[c].std(ddof=0)
                    for c in CALENDAR_COLS})
cal_cum = inc.mean(axis=1).unstack("team").cumsum()
assert np.allclose(cal_cum.iloc[-1].reindex(teams),
                   tt.set_index("team").cal_z.reindex(teams)), \
    "the curves must land on the calendar score"
print("  calendar accumulation verified: weekly sums and season endpoints")

# the title's claim, checked rather than trusted
_pit = cal_cum["PIT"]
assert (_pit.iloc[1:] > 0).all() and int((_pit > 0).sum()) >= 27, \
    "Pittsburgh is not above average pace almost from the first week"
print(f"  PIT above average pace in {int((_pit > 0).sum())} of {len(_pit)} weeks, "
      f"permanently from week 1")

hi = tt.nlargest(3, "cal_z").team.tolist()
lo = tt.nsmallest(3, "cal_z").team.tolist()
fig, ax = plt.subplots(figsize=(12.5, 7.8))
ax.fill_between(cal_cum.index, cal_cum.quantile(0.10, axis=1),
                cal_cum.quantile(0.90, axis=1), color=COL_GRAY, alpha=0.16, lw=0)
ax.fill_between(cal_cum.index, cal_cum.quantile(0.25, axis=1),
                cal_cum.quantile(0.75, axis=1), color=COL_GRAY, alpha=0.24, lw=0)
ax.axhline(0, color=COL_BLUE_DARK, lw=1.1, ls=(0, (5, 4)))
# Pittsburgh and Boston share a gold, Montreal and Calgary a red, Buffalo and
# Toronto a navy - pull the second of each pair darker so crossings are readable
CAL_C = distinct_colors(hi + lo)
for t in hi + lo:
    ax.plot(cal_cum.index, cal_cum[t], color=CAL_C[t], lw=2.6,
            zorder=4, solid_capstyle="round",
            path_effects=[pe.withStroke(linewidth=4.6, foreground="white")])
ends = sorted(((cal_cum[t].iloc[-1], t) for t in hi + lo), reverse=True)
sep = (cal_cum.values.max() - cal_cum.values.min()) * 0.05
placed = []
for y, t in ends:
    if placed and placed[-1][0] - y < sep:
        y = placed[-1][0] - sep
    placed.append((y, t))
for y, t in placed:
    ax.text(cal_cum.index[-1] + 0.4, y, t, va="center", fontsize=12.5,
            weight="bold", color=CAL_C[t])
ax.text(cal_cum.index[-1] - 0.3, 0.05, "league-average pace", fontsize=11,
        style="italic", color=COL_BLUE_DARK, ha="right", va="bottom")
ax.set_xlabel("Week of the regular season", fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylabel("Calendar burden accumulated", fontsize=hd.FS_AXIS_LABEL)
ax.set_xlim(0, cal_cum.index[-1] + 2.6)
hd.legend(ax, handles=[Patch(facecolor=COL_GRAY, alpha=0.24, label="Middle half"),
                       Patch(facecolor=COL_GRAY, alpha=0.16, label="10th-90th pct")],
          loc="upper left")
finish(fig, ax,
       "Pittsburgh's calendar is above average pace almost from the first week",
       "The three hardest calendars and the three easiest, accumulating week "
       "by week. Each line ends at that team's season score.",
       NOTE, FIGS / "p2_04_calendar_accumulation.png")

# %% p2_05 - the trade-off itself
sl, ic, r_c, p_c, _ = stats.linregress(tt.trav_z, tt.cal_z)
STATS["trade-off r (composites)"] = f"{r_c:+.3f} p={p_c:.5f}"
fig, ax = plt.subplots(figsize=(11.5, 8.4))
xs = np.linspace(tt.trav_z.min() - 0.15, tt.trav_z.max() + 0.15, 50)
ax.plot(xs, ic + sl * xs, color=COL_BLUE_DARK, lw=1.6, ls=(0, (6, 4)), zorder=2)
ax.axhline(0, color=COL_GRAY, lw=0.9, ls=":", zorder=1)
ax.axvline(0, color=COL_GRAY, lw=0.9, ls=":", zorder=1)
ax.scatter(tt.trav_z, tt.cal_z, s=150, color=tt.color, edgecolor="white",
           linewidth=1.1, zorder=4)
_pl = []
for _, rr in tt.sort_values("trav_z").iterrows():
    near = sum(1 for qx, qy in _pl if abs(qx - rr.trav_z) < 0.16 and abs(qy - rr.cal_z) < 0.22)
    ax.annotate(rr.team, (rr.trav_z, rr.cal_z), textcoords="offset points",
                xytext=(0, (11, -17, 24, -30)[near % 4]), ha="center",
                va="bottom" if near % 4 in (0, 2) else "top",
                fontsize=9.5, color=COL_BLUE_DARK)
    _pl.append((rr.trav_z, rr.cal_z))
ax.text(0.975, 0.955, f"r = {r_c:.2f}   p = {p_c:.4f}", transform=ax.transAxes,
        ha="right", va="top", fontsize=14, weight="bold", color=COL_BLUE_DARK)
ax.set_xlabel("Travel burden  (distance, time zones, nights away)",
              fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylabel("Calendar burden  (higher is harder)", fontsize=hd.FS_AXIS_LABEL)
div_legend(ax, loc="lower left")
finish(fig, ax,
       "The harder a team's travel, the easier its calendar",
       "Both composites are standardised across the 32 teams, so zero is the "
       "league average on each.",
       NOTE, FIGS / "p2_05_travel_vs_calendar.png")

# %% p2_06 - the variance cancellation, which is the real evidence
# If two burdens were handed out independently, the variance of their average
# would be the average of their variances (over four). It is not: the negative
# covariance cancels most of it.
#
# Plot the MEAN of the two, not the sum. trav_z and cal_z are each already a
# mean of z-scores, so their mean is on the same scale and the three strips are
# directly comparable - a sum is not, and drawing one makes the combined row
# look no tighter than its parts even though it is.
a, b = tt.trav_z, tt.cal_z
va, vb = a.var(ddof=0), b.var(ddof=0)
cov = np.cov(a, b, ddof=0)[0, 1]
v_obs = tt.comb.var(ddof=0)
assert abs((a + b).var(ddof=0) - (va + vb + 2 * cov)) < 1e-12, "variance identity"
assert abs(v_obs - (a + b).var(ddof=0) / 4) < 1e-12, "comb is the mean of the two"
v_ind = (va + vb) / 4                       # same scale, covariance set to zero
cancelled = 1 - v_obs / v_ind
STATS["variance cancelled"] = (f"{cancelled:.1%} (sd {np.sqrt(v_obs):.2f} observed "
                               f"vs {np.sqrt(v_ind):.2f} if independent)")

rows = [("Travel burden", a, COL_OIL_ORANGE),
        ("Calendar burden", b, COL_BLUE_PALE),
        ("Both, averaged", tt.comb, COL_BLUE_DARK)]
fig, ax = plt.subplots(figsize=(12.5, 7.4))
rng = np.random.default_rng(SEED)
for i, (lab, v, c) in enumerate(rows):
    y = len(rows) - 1 - i
    ax.hlines(y, v.min(), v.max(), color=c, lw=2.0, alpha=0.30, zorder=2)
    ax.scatter(v, y + rng.normal(0, 0.040, len(v)), s=95, color=c, alpha=0.85,
               edgecolor="white", linewidth=0.9, zorder=4)
    ax.text(-2.05, y + 0.30, lab, fontsize=14, weight="bold", color=c, ha="left")
    ax.text(-2.05, y + 0.13, f"sd {v.std(ddof=0):.2f}", fontsize=11,
            color=COL_GRAY, ha="left")

# the null, drawn where it can be compared directly against the observed row
sd_i = np.sqrt(v_ind)
ax.hlines(-0.62, -sd_i, sd_i, color=COL_GRAY, lw=7, alpha=0.55, zorder=3)
ax.hlines(-0.62, -np.sqrt(v_obs), np.sqrt(v_obs), color=COL_BLUE_DARK, lw=7,
          zorder=4)
ax.text(-2.05, -0.62, "\u00b11 sd", fontsize=12, color=COL_BLUE_DARK,
        ha="left", va="center", weight="bold")
ax.text(sd_i + 0.06, -0.62, f"if the two were unrelated: sd {sd_i:.2f}",
        fontsize=11.5, color=COL_GRAY, va="center")
ax.text(-sd_i - 0.06, -0.62, f"actual: sd {np.sqrt(v_obs):.2f}  ",
        fontsize=11.5, color=COL_BLUE_DARK, va="center", ha="right",
        weight="bold")

ax.axvline(0, color=COL_GRAY, lw=1, ls=":", zorder=1)
ax.set_yticks([])
ax.set_ylim(-1.05, len(rows) - 0.30)
ax.set_xlim(-2.10, 2.10)
ax.set_xlabel("Standardised burden  (higher is harder)", fontsize=hd.FS_XAXIS_LABEL)
for side in ("top", "right", "left"):
    ax.spines[side].set_visible(False)
finish(fig, ax,
       f"Counting both burdens makes the league {cancelled:.0%} more equal",
       "Each dot is a team. Averaging the two burdens gives a far tighter "
       "spread than either one alone.",
       NOTE, FIGS / "p2_06_variance_cancellation.png")

# %% p2_07 - is the trade-off beyond chance?
rng = np.random.default_rng(SEED)
null = np.array([np.corrcoef(a, rng.permutation(b.values))[0, 1] for _ in range(20000)])
obs = np.corrcoef(a, b)[0, 1]
p_perm = float(np.mean(np.abs(null) >= abs(obs)))
STATS["permutation p"] = f"{p_perm:.4f} on 20,000 shuffles (r={obs:+.3f})"

fig, ax = plt.subplots(figsize=(11.5, 6.8))
ax.hist(null, bins=60, color=COL_GRAY, alpha=0.55, edgecolor="white", linewidth=0.4)
ax.axvline(obs, color=COL_OIL_ORANGE, lw=2.6, zorder=5)
ax.axvline(-obs, color=COL_OIL_ORANGE, lw=1.2, ls=(0, (4, 3)), alpha=0.6, zorder=5)
ax.annotate(f"observed\nr = {obs:.2f}", (obs, ax.get_ylim()[1] * 0.72),
            xytext=(obs + 0.16, ax.get_ylim()[1] * 0.85), fontsize=13,
            weight="bold", color=COL_OIL_ORANGE,
            arrowprops=dict(arrowstyle="-", color=COL_OIL_ORANGE, lw=1.2))
ax.text(0.02, 0.95,
        f"{int(np.sum(np.abs(null) >= abs(obs)))} of 20,000 random reshuffles\n"
        f"produced a correlation this strong.\np = {p_perm:.4f}",
        transform=ax.transAxes, va="top", fontsize=12.5, color=COL_BLUE_DARK,
        linespacing=1.7)
ax.set_xlabel("Correlation between travel and calendar burden",
              fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylabel("Reshuffles", fontsize=hd.FS_AXIS_LABEL)
finish(fig, ax,
       "The trade-off is not a coincidence of a small league",
       "Calendar burdens reshuffled at random across the 32 teams, 20,000 "
       "times, against what the real schedule produced.",
       NOTE, FIGS / "p2_07_permutation_test.png")

# %% p2_08 - geography, three ways
# The figure that carries both the argument and its limits. Travel is decided by
# the map; the calendar is not decided by anything visible here; counting both
# leaves a real but much smaller geographic tilt.
panels = [("trav_z", "Travel burden"), ("cal_z", "Calendar burden"),
          ("comb", "Both combined")]
fig, axes = plt.subplots(1, 3, figsize=(15.5, 7.2), sharey=True)
fig.subplots_adjust(top=0.80, bottom=0.14, left=0.055, right=0.985, wspace=0.09)
rng = np.random.default_rng(SEED)
for axp, (col, lab) in zip(axes, panels):
    e2, F, p = eta2(col)
    STATS[f"eta2 {col}"] = f"{e2:.3f} F={F:.2f} p={p:.3f}"
    groups = [tt.loc[tt.division == dv, col].values for dv in DIVISION_ORDER]
    bp = axp.boxplot(groups, patch_artist=True, widths=0.55,
                     medianprops=dict(color=COL_BLUE_DARK, lw=2),
                     whiskerprops=dict(color=COL_GRAY),
                     capprops=dict(color=COL_GRAY), flierprops=dict(marker=""))
    for patch, dv in zip(bp["boxes"], DIVISION_ORDER):
        patch.set_facecolor(DIV_C[dv]); patch.set_alpha(0.18)
        patch.set_edgecolor(COL_GRAY)
    for i, (dv, gv) in enumerate(zip(DIVISION_ORDER, groups), start=1):
        axp.scatter(rng.normal(i, 0.06, len(gv)), gv, s=52, zorder=3,
                    color=DIV_C[dv], edgecolor="white", linewidth=0.8)
    axp.axhline(0, color=COL_GRAY, lw=0.9, ls=":", zorder=1)
    axp.set_xticks(range(1, 5))
    axp.set_xticklabels([d[:3].upper() for d in DIVISION_ORDER], fontsize=12)
    sig = "n.s." if p >= 0.05 else ("p < .001" if p < 0.001 else f"p = {p:.3f}")
    axp.set_title(f"{lab}\n$\\eta^2$ = {e2:.2f}   {sig}", fontsize=14,
                  weight="bold", color=COL_BLUE_DARK, pad=10, linespacing=1.6)
    for side in ("top", "right"):
        axp.spines[side].set_visible(False)
axes[0].set_ylabel("Standardised burden", fontsize=hd.FS_AXIS_LABEL)
fig.text(0.055, 0.045,
         "ATL Atlantic   MET Metropolitan   CEN Central   PAC Pacific",
         fontsize=hd.FS_NOTE, style="italic", color=COL_GRAY)
e2t = eta2("trav_z")[0]; e2c = eta2("cal_z")[0]; e2b = eta2("comb")[0]
fig.text(0.045, 0.965,
         "Where a team plays decides its travel, not its calendar",
         fontsize=hd.FS_TITLE, weight="bold", ha="left", va="top")
fig.text(0.045, 0.925,
         f"Division explains {e2t:.0%} of the variance in travel burden but only "
         f"{e2c:.0%} of the calendar — and that {e2c:.0%} is not statistically significant.",
         fontsize=hd.FS_SUBTITLE, ha="left", va="top")
fig.text(0.94, 0.012, NOTE, fontsize=hd.FS_NOTE, style="italic", ha="right")
fig.savefig(FIGS / "p2_08_geography_three_ways.png", dpi=300,
            bbox_inches="tight", transparent=True)
print("  saved p2_08_geography_three_ways.png")
plt.close(fig)

# %% p2_09 - who has it worst once both burdens count
# comb is NOT the Travel Burden Index from Part 1. It weights travel and
# calendar evenly; the TBI is 3:2 across its pillars and also counts trip
# length. They correlate at Spearman 0.89 and differ by a mean of 3.4 places.
rho_tbi = tt.comb.corr(tt.tbi, method="spearman")
shift = (tt.comb_rank - tt.tbi_rank).abs()
STATS["comb vs TBI"] = f"Spearman {rho_tbi:.3f}, mean shift {shift.mean():.1f} places"

d = tt.sort_values("comb")
fig, ax = plt.subplots(figsize=(13, 11.5))
pos = np.zeros(len(d)); neg = np.zeros(len(d))
for col, c, lab in ((("trav_z"), COL_OIL_ORANGE, "Travel burden"),
                    (("cal_z"), COL_BLUE_PALE, "Calendar burden")):
    v = d[col].values / 2                       # comb is the mean of the two
    left = np.where(v >= 0, pos, neg + v)
    ax.barh(d.team, np.abs(v), left=left, color=c, height=0.7, label=lab,
            edgecolor="white", linewidth=0.4, zorder=3)
    pos = pos + np.where(v >= 0, v, 0)
    neg = neg + np.where(v < 0, v, 0)
assert np.allclose(pos + neg, d.comb), "segments must sum to the combined score"
ax.axvline(0, color=COL_BLUE_DARK, lw=1.1, zorder=4)
ax.scatter(d.comb, d.team, s=170, color="white", zorder=6, linewidths=0)
ax.scatter(d.comb, d.team, s=78, color=COL_BLUE_DARK, zorder=7,
           edgecolor="white", linewidth=1.3, label="Combined score")
xmax = pos.max() + 0.36
ax.set_xlim(neg.min() - 0.05, xmax)
for y, v in zip(d.team, d.comb):
    ax.text(xmax - 0.02, y, f"{v:+.2f}", va="center", ha="right", fontsize=11,
            weight="bold", color=COL_BLUE_DARK)
ax.axvline(xmax - 0.30, color=COL_GRAY, lw=0.8, alpha=0.5, zorder=2)
for lbl in ax.get_yticklabels():
    lbl.set_color(DIV_C[DIVISION[lbl.get_text()]])
    lbl.set_fontweight("bold")
ax.set_xlabel("Contribution to the combined burden  (each z-score ÷ 2)",
              fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylim(-3.0, len(d) - 0.35)
ax.legend(frameon=False, fontsize=hd.FS_LEGEND, loc="lower center", ncol=3,
          handlelength=1.6, columnspacing=2.0)
tE = stats.ttest_ind(tt.loc[tt.conf == "East", "comb"], tt.loc[tt.conf == "West", "comb"])
STATS["combined East vs West"] = (f"East {tt[tt.conf=='East'].comb.mean():+.3f} "
                                  f"West {tt[tt.conf=='West'].comb.mean():+.3f} "
                                  f"t={tE.statistic:+.2f} p={tE.pvalue:.3f}")
finish(fig, ax,
       "Counting both burdens, the West still has it worse",
       f"The trade-off narrows the gap but does not close it: West "
       f"{tt[tt.conf=='West'].comb.mean():+.2f} against East "
       f"{tt[tt.conf=='East'].comb.mean():+.2f}, p = {tE.pvalue:.3f}.",
       NOTE, FIGS / "p2_09_combined_ranking.png", title_x=0.045)

# %% p2_10 - which parts of the calendar actually drive the trade-off
PANEL = CALENDAR_COLS + ["b2b"]
LAB4 = {**CAL_LABELS, "b2b": "All back-to-backs"}
fig, axes = plt.subplots(2, 2, figsize=(12.5, 10))
fig.subplots_adjust(top=0.815, bottom=0.065, left=0.075, right=0.98,
                    hspace=0.46, wspace=0.20)
for axp, col in zip(axes.ravel(), PANEL):
    r_, p_ = stats.pearsonr(tt.total_km, tt[col])
    STATS[f"{col} vs distance"] = f"r={r_:+.2f} p={p_:.3f}"
    sl_, ic_ = np.polyfit(tt.total_km, tt[col], 1)
    xs = np.linspace(tt.total_km.min() * 0.98, tt.total_km.max() * 1.02, 40)
    axp.plot(xs / 1000, ic_ + sl_ * xs, color=COL_BLUE_DARK, lw=1.5,
             ls=(0, (6, 4)), zorder=2)
    axp.scatter(tt.total_km / 1000, tt[col], s=78, color=tt.color, zorder=4,
                edgecolor="white", linewidth=0.9)
    sig = "n.s." if p_ >= 0.05 else ("p < .001" if p_ < 0.001 else f"p = {p_:.3f}")
    axp.set_title(f"{LAB4[col]}\nr = {r_:.2f}   {sig}", fontsize=13.5,
                  weight="bold", color=COL_BLUE_DARK, pad=8, linespacing=1.5)
    axp.set_xlabel("Kilometres flown (thousands)", fontsize=13)
    axp.set_ylabel("Games", fontsize=13)
    for side in ("top", "right"):
        axp.spines[side].set_visible(False)
# legend under the subtitle, not at the foot - the foot belongs to the source note
fig.legend(handles=[Patch(facecolor=DIV_C[k], label=k) for k in DIVISION_ORDER],
           frameon=False, fontsize=hd.FS_LEGEND, ncol=4, loc="upper center",
           bbox_to_anchor=(0.5, 0.905))
fig.text(0.045, 0.985, "Back-to-backs drive the trade-off; three-in-fours barely do",
         fontsize=hd.FS_TITLE, weight="bold", ha="left", va="top")
fig.text(0.045, 0.947,
         "Each calendar component against distance flown. Only the back-to-back "
         "measures are significant on their own.",
         fontsize=hd.FS_SUBTITLE, ha="left", va="top")
fig.text(0.94, 0.012, NOTE, fontsize=hd.FS_NOTE, style="italic", ha="right")
fig.savefig(FIGS / "p2_10_components_vs_distance.png", dpi=300,
            bbox_inches="tight", transparent=True)
print("  saved p2_10_components_vs_distance.png")
plt.close(fig)

# %% every statistic quoted in Part 2, in one verified place
print("\n" + "=" * 74)
print("PART 2 - STATISTICS QUOTED IN THE FIGURES")
print("=" * 74)
for k, v in STATS.items():
    print(f"  {k:28} {v}")
tM = stats.ttest_ind(tt.loc[tt.division == "Metropolitan", "cal_z"],
                     tt.loc[tt.division != "Metropolitan", "cal_z"])
tC = stats.ttest_ind(tt.loc[tt.conf == "East", "cal_z"], tt.loc[tt.conf == "West", "cal_z"])
print(f"  {'calendar East vs West':28} t={tC.statistic:+.2f} p={tC.pvalue:.3f}  (n.s.)")
print(f"  {'Metropolitan vs rest':28} t={tM.statistic:+.2f} p={tM.pvalue:.3f}")
print(f"\n  calendar burden by division:")
print(tt.groupby("division")[["trav_z", "cal_z", "comb"]].mean().round(2).to_string())
assert len(list(FIGS.glob("p2_*.png"))) == 10, "expected ten Part 2 figures"
print(f"\n  {len(list(FIGS.glob('p2_*.png')))} figures in {FIGS}")
