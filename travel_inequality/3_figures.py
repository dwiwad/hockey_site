"""3_figures.py - the figures and the printed findings for the travel analysis.

Reads  data/team_travel.parquet, data/team_travel_with_europe.parquet,
       data/legs.parquet, data/team_weeks.parquet, data/trips.parquet
Writes figures/fig1..fig8 .png

Written for cell-by-cell execution in Spyder (Ctrl+Enter through the # %% cells).
House style comes from the vendored hd_style.py; finish() saves at dpi=300 with
transparent=True, because the site background is cream and an opaque figure
renders as a white slab on it.
"""

# %% imports and configuration
from pathlib import Path

import matplotlib.colors as mcolors
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats

try:
    HERE = Path(__file__).resolve().parent
except NameError:                       # Spyder cell execution
    HERE = Path("/Users/dwiwad/dev/hockey_site/travel_inequality")

import sys
sys.path.insert(0, str(HERE))
import hd_style as hd
from hd_style import (COL_BLUE_DARK, COL_BLUE_PALE, COL_GRAY, COL_OIL_ORANGE,
                      DIVISION, DIVISION_ORDER, DIV_COLORS, TEAM_COLORS, TEAM_NAMES,
                      finish, readable)

DATA = HERE / "data"
FIGS = HERE / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

NOTE = "Data: NHL API (club-schedule-season), 2026-27 regular season"
KM_PER_MI = 1.609344

tt = pd.read_parquet(DATA / "team_travel.parquet")
tte = pd.read_parquet(DATA / "team_travel_with_europe.parquet")
legs = pd.read_parquet(DATA / "legs.parquet")
weeks = pd.read_parquet(DATA / "team_weeks.parquet")
trips = pd.read_parquet(DATA / "trips.parquet")

tt["division"] = tt.team.map(DIVISION)
tt["color"] = tt.division.map(DIV_COLORS)
print(f"{len(tt)} teams loaded")


def gini(x):
    """Gini coefficient of a non-negative vector. 0 = perfectly even."""
    x = np.sort(np.asarray(x, dtype=float))
    n, total = len(x), x.sum()
    if total == 0:
        return 0.0
    i = np.arange(1, n + 1)
    return (2 * (i * x).sum()) / (n * total) - (n + 1) / n


def hbar(df, value, title, subtitle, path, fmt="{:,.0f}", xlabel="",
         color=None, height=11, thousands=False):
    """Ranked horizontal bar over all 32 teams, hardest at the top.

    The house finish() left-aligns the title to the axes spine, which on a
    horizontal bar chart sits to the right of the tricode labels. title_x moves
    it back out to the real left edge of the drawn content.
    """
    d = df.sort_values(value, ascending=True)
    fig, ax = plt.subplots(figsize=(12, height))
    ax.barh(d.team, d[value], color=color if color is not None else d.color,
            height=0.72)
    ax.set_xlabel(xlabel, fontsize=hd.FS_XAXIS_LABEL)
    ax.margins(x=0.14, y=0.012)
    if thousands:
        ax.xaxis.set_major_formatter(lambda v, _: f"{v/1000:,.0f}k" if v else "0")
    for y, v in zip(d.team, d[value]):
        ax.text(v + ax.get_xlim()[1] * 0.008, y, fmt.format(v),
                va="center", fontsize=11, color=COL_BLUE_DARK)
    ax.legend(handles=[Patch(facecolor=DIV_COLORS[k], label=k)
                       for k in DIVISION_ORDER],
              frameon=False, fontsize=hd.FS_LEGEND, loc="lower right")
    finish(fig, ax, title, subtitle, NOTE, path, title_x=0.045)


# %% fig 1 - the Travel Burden Index ranking
fig, ax = plt.subplots(figsize=(12, 11))
d = tt.sort_values("tbi")
ax.barh(d.team, d.tbi, color=d.color, height=0.72)
ax.axvline(0, color=COL_GRAY, lw=1)
ax.set_xlabel("Travel Burden Index  (mean of five standardised pillars)",
              fontsize=hd.FS_XAXIS_LABEL)
ax.margins(x=0.09, y=0.012)      # room for the value label on Montreal's bar
for y, v in zip(d.team, d.tbi):
    off = 0.02 if v >= 0 else -0.02
    ax.text(v + off, y, f"{v:+.2f}", va="center",
            ha="left" if v >= 0 else "right", fontsize=11, color=COL_BLUE_DARK)
ax.legend(handles=[Patch(facecolor=DIV_COLORS[k], label=k) for k in DIVISION_ORDER],
          frameon=False, fontsize=hd.FS_LEGEND, loc="lower right")
finish(fig, ax,
       "Utah, San Jose and Los Angeles draw the hardest travel in 2026-27",
       "Distance, days away, time zones, tight turnarounds and rest deficit, "
       "standardised and averaged.",
       NOTE, FIGS / "fig1_burden_ranking.png", title_x=0.045)

# %% fig 9 - what the index is actually made of
# fig1 ranks the teams on the composite, which is the right ranking but an
# unreadable unit: nobody has intuition for "+0.83". This is the same ranking
# taken apart. Because the index is the MEAN of five standardised pillars, each
# pillar contributes exactly its own z-score divided by five, and those five
# contributions sum to the team's index.
#
# One thing this chart must NOT claim is that bar length is the index. Segments
# straddle zero, so the drawn bar spans from a team's total negative pull to its
# total positive pull - Vegas runs from -0.55 to +0.79 while scoring +0.26. The
# net is the dot, and the dot has to win the visual fight.
PILLAR_LABELS_9 = {
    "p_distance": "Distance",
    "p_time_away": "Time away",
    "p_circadian": "Time zones",
    "p_density": "Tight turnarounds",
    "p_recovery": "Rest deficit",
}
# a five-step ramp across the house palette, dark blue through to oil orange
PILLAR_COLORS = ["#041E42", "#3B4B64", "#8A8578", "#D4884A", COL_OIL_ORANGE]
DIV_TICK = {**DIV_COLORS, "Central": "#6E7787"}     # the pale grey is unreadable

d = tt.sort_values("tbi")
contrib = d[list(PILLAR_LABELS_9)] / len(PILLAR_LABELS_9)
assert np.allclose(contrib.sum(axis=1), d.tbi), "contributions must sum to the index"

fig, ax = plt.subplots(figsize=(13.5, 11.5))
pos = np.zeros(len(d))
neg = np.zeros(len(d))
for (col, lab), c in zip(PILLAR_LABELS_9.items(), PILLAR_COLORS):
    v = contrib[col].values
    left = np.where(v >= 0, pos, neg + v)
    ax.barh(d.team, np.abs(v), left=left, color=c, height=0.7, label=lab,
            edgecolor="white", linewidth=0.4, zorder=3)
    pos = pos + np.where(v >= 0, v, 0)
    neg = neg + np.where(v < 0, v, 0)

ax.axvline(0, color=COL_BLUE_DARK, lw=1.1, zorder=4)
# the net score, drawn to dominate: white halo then a solid dot
ax.scatter(d.tbi, d.team, s=170, color="white", zorder=6, linewidths=0)
ax.scatter(d.tbi, d.team, s=78, color=COL_BLUE_DARK, zorder=7,
           edgecolor="white", linewidth=1.3, label="Net score (the index)")

# totals in their own column on the right, clear of the bars
xmax = pos.max() + 0.34
ax.set_xlim(neg.min() - 0.05, xmax)
for y, v in zip(d.team, d.tbi):
    ax.text(xmax - 0.02, y, f"{v:+.2f}", va="center", ha="right",
            fontsize=11, weight="bold", color=COL_BLUE_DARK)
ax.axvline(xmax - 0.30, color=COL_GRAY, lw=0.8, alpha=0.5, zorder=2)

for lbl in ax.get_yticklabels():
    lbl.set_color(DIV_TICK[DIVISION[lbl.get_text()]])
    lbl.set_fontweight("bold")
ax.set_xlabel("Each pillar's contribution to the index  (its z-score ÷ 5)",
              fontsize=hd.FS_XAXIS_LABEL)
# Reserve empty rows below the last team for the legend. Overlaying it inside
# the plot buried Montreal, Detroit and Carolina - the three teams the title is
# about - and there is no free corner on a diverging chart this dense.
ax.set_ylim(-4.6, len(d) - 0.35)
ax.legend(frameon=False, fontsize=hd.FS_LEGEND, loc="lower center", ncol=3,
          handlelength=1.6, columnspacing=2.2)
finish(fig, ax,
       "Only a fifth of the gap between the worst and best schedule is distance",
       "Segments left of zero pull a team down the ranking, right of zero push "
       "it up. The dot is the net.",
       NOTE, FIGS / "fig9_burden_composition.png", title_x=0.045)

# the claim in that title, checked rather than asserted
u = tt.loc[tt.tbi.idxmax()]
m = tt.loc[tt.tbi.idxmin()]
share = {lab: (u[c] - m[c]) / len(PILLAR_LABELS_9) / (u.tbi - m.tbi)
         for c, lab in PILLAR_LABELS_9.items()}
assert abs(sum(share.values()) - 1) < 1e-9
assert share["Distance"] < 0.25, "title says distance is a fifth of the gap"
print(f"  {u.team} vs {m.team} gap {u.tbi - m.tbi:.2f}, by pillar: "
      + ", ".join(f"{k} {v:.0%}" for k, v in share.items()))

# %% fig 2 - total distance
g_km = gini(tt.total_km)
ratio = tt.total_km.max() / tt.total_km.min()
hbar(tt, "total_km",
     f"The longest schedule flies {ratio-1:.0%} farther than the shortest",
     f"Great-circle airport-to-airport distance over 84 games. "
     f"Gini across the 32 teams = {g_km:.3f}.",
     FIGS / "fig2_total_distance_ranking.png", thousands=True,
     xlabel="Kilometres flown, 2026-27 regular season")

# %% fig 3 - Lorenz curve
x = np.sort(tt.total_km.values)
cum = np.concatenate([[0], np.cumsum(x) / x.sum()])
share = np.linspace(0, 1, len(x) + 1)

fig, ax = plt.subplots(figsize=(9, 8))
ax.plot([0, 1], [0, 1], color=COL_GRAY, lw=1.5, ls="--",
        label="Perfect equality")
ax.plot(share, cum, color=COL_OIL_ORANGE, lw=2.5, label="2026-27 schedule")
ax.fill_between(share, cum, share, color=COL_OIL_ORANGE, alpha=0.12)
ax.set_xlabel("Cumulative share of teams, least travel first",
              fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylabel("Cumulative share of league distance", fontsize=hd.FS_AXIS_LABEL)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.text(0.55, 0.30, f"Gini = {g_km:.3f}", fontsize=17, weight="bold",
        color=COL_OIL_ORANGE)
ax.text(0.55, 0.22,
        f"Lightest 16 teams fly {cum[16]:.0%} of\nthe league's total distance",
        fontsize=13, color=COL_BLUE_DARK)
hd.legend(ax, loc="upper left")
finish(fig, ax,
       "Travel is unevenly shared, but nothing like a winner-take-all split",
       "Lorenz curve of season flying distance across the 32 teams. A straight "
       "diagonal would mean every team flies exactly the same.",
       NOTE, FIGS / "fig3_lorenz_curve.png")

# %% fig 4 - the five pillars, taken apart
PILLAR_LABELS = {
    "p_distance_rank": "Distance",
    "p_time_away_rank": "Days away",
    "p_circadian_rank": "Time zones",
    "p_density_rank": "Tight games",
    "p_recovery_rank": "Rest deficit",
}
d = tt.sort_values("tbi_rank")
mat = d[list(PILLAR_LABELS)].values.astype(float)
cmap = LinearSegmentedColormap.from_list(
    "hd_rank", [COL_OIL_ORANGE, "#F0E4D8", COL_BLUE_PALE])

fig, ax = plt.subplots(figsize=(9, 12))
im = ax.imshow(mat, cmap=cmap, aspect="auto", vmin=1, vmax=32)
ax.set_xticks(range(len(PILLAR_LABELS)))
ax.set_xticklabels(PILLAR_LABELS.values(), fontsize=13)
ax.set_yticks(range(len(d)))
ax.set_yticklabels([f"{r:>2}  {t}" for r, t in zip(d.tbi_rank, d.team)],
                   fontsize=11)
ax.tick_params(length=0)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        v = int(mat[i, j])
        ax.text(j, i, v, ha="center", va="center", fontsize=10,
                color=COL_BLUE_DARK if 8 < v < 26 else "white")
cb = fig.colorbar(im, ax=ax, fraction=0.035, pad=0.03)
cb.set_label("League rank  (1 = hardest)", fontsize=12)
cb.outline.set_visible(False)
finish(fig, ax,
       "No team draws the worst of everything",
       "League rank on each of the five pillars, teams ordered by the composite "
       "index. Orange is a hard draw, blue an easy one.",
       NOTE, FIGS / "fig4_burden_components.png", title_x=0.045)

# %% fig 5 - within-team lumpiness
g_lump = tt.week_km_gini
hbar(tt, "week_km_gini",
     "The Islanders' travel arrives in the most concentrated bursts",
     "Gini of each team's own week-by-week flying distance. Higher means the "
     "miles are bunched into fewer weeks.",
     FIGS / "fig5_lumpiness_ranking.png", fmt="{:.3f}",
     xlabel="Gini of weekly distance, within team")

# %% fig 6 - cumulative travel through the season
piv = (weeks.pivot(index="week", columns="team", values="km")
       .cumsum().div(1000))
order = tt.sort_values("total_km", ascending=False).team
hi, lo = list(order[:3]), list(order[-3:])

fig, ax = plt.subplots(figsize=(12, 7.5))
for t in piv.columns:
    if t in hi or t in lo:
        continue
    ax.plot(piv.index, piv[t], color=COL_GRAY, lw=0.9, alpha=0.45)
for t in hi + lo:
    ax.plot(piv.index, piv[t],
            color=COL_OIL_ORANGE if t in hi else COL_BLUE_DARK, lw=2.4)

# End labels sit at each line's final value, which for VGK, COL and WPG is
# within a few hundred km. Push them apart just enough to stay legible.
ends = sorted(((piv[t].iloc[-1], t) for t in hi + lo), reverse=True)
min_sep = (piv.values.max() - piv.values.min()) * 0.030
placed = []
for y, t in ends:
    if placed and placed[-1][0] - y < min_sep:
        y = placed[-1][0] - min_sep
    placed.append((y, t))
for y, t in placed:
    ax.text(piv.index[-1] + 0.45, y, t,
            color=COL_OIL_ORANGE if t in hi else COL_BLUE_DARK,
            fontsize=12, va="center", weight="bold")
ax.set_xlabel("Week of the regular season", fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylabel("Cumulative distance flown (thousand km)",
              fontsize=hd.FS_AXIS_LABEL)
ax.set_xlim(0, piv.index[-1] + 2.2)
hd.legend(ax, handles=[Line2D([], [], color=COL_OIL_ORANGE, lw=2.4,
                              label="Three heaviest schedules"),
                       Line2D([], [], color=COL_BLUE_DARK, lw=2.4,
                              label="Three lightest schedules"),
                       Line2D([], [], color=COL_GRAY, lw=0.9,
                              label="Other 26 teams")], loc="upper left")
finish(fig, ax,
       "The heaviest and lightest schedules part ways inside the first month",
       "Cumulative flying distance by week. The three heaviest and three "
       "lightest separate by week three and never cross again.",
       NOTE, FIGS / "fig6_cumulative_travel.png")

# %% fig 10 - burden accumulating across the season
# fig6 accumulates kilometres. This accumulates the whole index.
#
# It works because a z-score is linear in its underlying total. If a season
# total X is a sum over weeks, X = sum_w x_w, then
#
#     z(X) = (X - mu)/sigma = sum_w [ (x_w - mu/W) / sigma ]
#
# so each week contributes an exact, additive slice of the team's final
# z-score, and the running total lands precisely on the index at season end.
# Zero on this chart is league-average pace: a line climbing above it is
# accumulating burden faster than the average team, and the final height IS
# that team's score.
#
# One measure has to be dropped. longest_trip_days is a MAXIMUM, not a sum, so
# it cannot be decomposed into weekly increments at all. The cumulative index
# therefore runs on the seven additive measures; p_time_away falls back to
# road_days alone. The correlation with the published index is reported below.
# this cell needs two tables the rest of the script does not
ven = pd.read_parquet(DATA / "venues.parquet")
tg = pd.read_parquet(DATA / "team_games.parquet")
WEEK_PILLARS = {
    "p_distance": ["w_km"],
    "p_time_away": ["w_road_days"],
    "p_circadian": ["w_tz", "w_east"],
    "p_density": ["w_b2b_travel", "w_three_in_four"],
    "p_recovery": ["w_rest_deficit"],
}
SEASON_START_10 = legs.date.min()
N_WEEKS = int((legs.date.max() - SEASON_START_10).days // 7) + 1


def wk(dates):
    return ((pd.to_datetime(pd.Series(list(dates))) - SEASON_START_10)
            .dt.days // 7).astype(int).values


teams = sorted(tt.team)
idx = pd.MultiIndex.from_product([teams, range(N_WEEKS)], names=["team", "week"])
W = pd.DataFrame(0.0, index=idx, columns=list(
    dict.fromkeys(c for v in WEEK_PILLARS.values() for c in v)))

# distance, time zones, eastward - straight off the legs
lg = legs.copy()
lg["week"] = wk(lg.date)
for src, dst, fn in (("km", "w_km", lambda v: v),
                     ("tz_delta", "w_tz", np.abs),
                     ("tz_delta", "w_east", lambda v: v.clip(lower=0))):
    agg = lg.assign(v=fn(lg[src])).groupby(["team", "week"]).v.sum()
    W[dst] = W[dst].add(agg.reindex(W.index, fill_value=0.0), fill_value=0.0)

# road days - every calendar day of every trip, bucketed by week
rd = []
for _, t in trips.iterrows():
    for d in pd.date_range(t.start, t.end, freq="D"):
        rd.append((t.team, int((d - SEASON_START_10).days // 7)))
agg = pd.Series(1.0, index=pd.MultiIndex.from_tuples(rd, names=["team", "week"]))
W["w_road_days"] = W.w_road_days.add(
    agg.groupby(level=[0, 1]).sum().reindex(W.index, fill_value=0.0), fill_value=0.0)

# travel back-to-backs and three-in-four, charged to the week of the later game
eu = set(ven.loc[ven.region.eq("Europe"), "venue"])
itin10 = tg[~tg.venue.isin(eu)].sort_values(["team", "game_date", "game_id"])
for team, g in itin10.groupby("team"):
    d_, ia = g.game_date.reset_index(drop=True), g.iata.reset_index(drop=True)
    b2b = d_.diff().dt.days.eq(1) & ia.ne(ia.shift())
    tif = (d_ - d_.shift(2)).dt.days.le(3)
    for mask, col in ((b2b, "w_b2b_travel"), (tif, "w_three_in_four")):
        for w_ in wk(d_[mask]):
            W.loc[(team, w_), col] += 1

# rest deficit - computed on the full schedule, as the index does
_r = tg[["game_id", "team", "rest_days"]]
_m = _r.merge(_r, on="game_id", suffixes=("", "_o"))
_m = _m[_m.team != _m.team_o].dropna(subset=["rest_days", "rest_days_o"])
_def = _m[_m.rest_days_o > _m.rest_days].merge(
    tg[["team", "game_id", "game_date"]], on=["team", "game_id"])
for team, g in _def.groupby("team"):
    for w_ in wk(g.game_date):
        W.loc[(team, w_), "w_rest_deficit"] += 1

# season totals must reproduce the published columns exactly
tot = W.groupby(level=0).sum()
for col, ref in (("w_km", "total_km"), ("w_road_days", "road_days"),
                 ("w_tz", "tz_crossings"), ("w_east", "eastward_hours"),
                 ("w_b2b_travel", "b2b_with_travel"),
                 ("w_three_in_four", "three_in_four"),
                 ("w_rest_deficit", "rest_deficit_games")):
    got = tot[col].reindex(teams).values
    want = tt.set_index("team")[ref].reindex(teams).values.astype(float)
    assert np.allclose(got, want), f"weekly {col} does not sum to {ref}"
print("  weekly measures reproduce every season total")

# weekly z-increments, then the running index
inc = pd.DataFrame(index=W.index)
for col in W.columns:
    mu, sd = tot[col].mean(), tot[col].std(ddof=0)
    inc[col] = (W[col] - mu / N_WEEKS) / sd
pill = pd.DataFrame({p: inc[cols].mean(axis=1) for p, cols in WEEK_PILLARS.items()})
burden = pill.mean(axis=1).unstack("team").cumsum()

final = burden.iloc[-1]
recomputed = pd.DataFrame(
    {p: pd.concat([(tot[c] - tot[c].mean()) / tot[c].std(ddof=0) for c in cols],
                  axis=1).mean(axis=1) for p, cols in WEEK_PILLARS.items()}).mean(axis=1)
assert np.allclose(final.reindex(teams), recomputed.reindex(teams)), \
    "cumulative curve must land on the index"
rho = final.reindex(teams).corr(tt.set_index("team").tbi.reindex(teams), method="spearman")
print(f"  curves land on the 7-measure index; Spearman vs the published TBI = {rho:.3f}")

# Highlight the SAME six teams as fig1 and fig9, chosen on the published index
# rather than on this variant. Dropping longest_trip_days moves Washington eight
# places, and a reader who met Carolina as 30th two figures ago should not find
# Washington in its place here.
rank_by = tt.set_index("team").tbi_rank
hi10 = rank_by.nsmallest(3).index.tolist()
lo10 = rank_by.nlargest(3).index.tolist()

# The title's claim, checked.
assert (burden["UTA"] > 0).all(), "Utah is not above average pace every week"
never = [t for t in burden.columns if (burden[t] <= 0).all()]
print(f"  above average pace every week: "
      f"{[t for t in burden.columns if (burden[t] > 0).all()]}; never above: {never}")

fig, ax = plt.subplots(figsize=(12.5, 7.8))
# A band instead of 26 more lines. These curves wander - a quiet week is BELOW
# average pace and subtracts - so twenty-six of them overlaid is unreadable
# noise that hides the six that matter.
q10 = burden.quantile(0.10, axis=1)
q90 = burden.quantile(0.90, axis=1)
q25 = burden.quantile(0.25, axis=1)
q75 = burden.quantile(0.75, axis=1)
ax.fill_between(burden.index, q10, q90, color=COL_GRAY, alpha=0.16, lw=0, zorder=1)
ax.fill_between(burden.index, q25, q75, color=COL_GRAY, alpha=0.24, lw=0, zorder=1)
ax.axhline(0, color=COL_BLUE_DARK, lw=1.1, ls=(0, (5, 4)), zorder=2)
for t in hi10 + lo10:
    ax.plot(burden.index, burden[t], color=readable(TEAM_COLORS[t]), lw=2.6,
            zorder=4, solid_capstyle="round",
            path_effects=[pe.withStroke(linewidth=4.6, foreground="white")])

ends = sorted(((burden[t].iloc[-1], t) for t in hi10 + lo10), reverse=True)
min_sep = (burden.values.max() - burden.values.min()) * 0.050
placed = []
for y, t in ends:
    if placed and placed[-1][0] - y < min_sep:
        y = placed[-1][0] - min_sep
    placed.append((y, t))
for y, t in placed:
    ax.text(burden.index[-1] + 0.4, y, t, va="center", fontsize=12.5,
            weight="bold", color=readable(TEAM_COLORS[t]))
ax.text(burden.index[-1] - 0.3, 0.045, "league-average pace", fontsize=11,
        style="italic", color=COL_BLUE_DARK, ha="right", va="bottom")
ax.set_xlabel("Week of the regular season", fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylabel("Burden accumulated, against average pace",
              fontsize=hd.FS_AXIS_LABEL)
ax.set_xlim(0, burden.index[-1] + 2.6)
# the six lines are named at their right-hand ends, so the legend only has to
# explain the bands
hd.legend(ax, handles=[
    Patch(facecolor=COL_GRAY, alpha=0.24, label="Middle half of the league"),
    Patch(facecolor=COL_GRAY, alpha=0.16, label="10th-90th percentile")],
    loc="upper left")
finish(fig, ax,
       "Utah is above league-average pace in every week of the season",
       "The three hardest schedules and the three easiest, on the seven "
       "measures that accumulate. Trip length cannot, so it is excluded.",
       NOTE, FIGS / "fig10_burden_accumulation.png")

# %% fig 7 - how much of the inequality is just geography
groups = [tt.loc[tt.division == d, "total_km"].values for d in DIVISION_ORDER]
F, p = stats.f_oneway(*groups)
grand = tt.total_km.mean()
ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
eta2 = ss_between / ((tt.total_km - grand) ** 2).sum()

fig, ax = plt.subplots(figsize=(11, 7))
bp = ax.boxplot(groups, patch_artist=True, widths=0.55,
                medianprops=dict(color=COL_BLUE_DARK, lw=2),
                whiskerprops=dict(color=COL_GRAY),
                capprops=dict(color=COL_GRAY),
                flierprops=dict(marker=""))
for patch, d in zip(bp["boxes"], DIVISION_ORDER):
    patch.set_facecolor(DIV_COLORS[d])
    patch.set_alpha(0.18)
    patch.set_edgecolor(COL_GRAY)
rng = np.random.default_rng(7)
for i, (d, g) in enumerate(zip(DIVISION_ORDER, groups), start=1):
    ax.scatter(rng.normal(i, 0.06, len(g)), g, s=52, zorder=3,
               color=DIV_COLORS[d], edgecolor="white", linewidth=0.8)
ax.set_xticklabels(DIVISION_ORDER, fontsize=hd.FS_TICK)
ax.set_ylabel("Kilometres flown, 2026-27", fontsize=hd.FS_AXIS_LABEL)
ax.yaxis.set_major_formatter(lambda v, _: f"{v/1000:,.0f}k")
ax.text(0.02, 0.96, f"$\\eta^2$ = {eta2:.2f}   F(3, 28) = {F:.1f},  p = {p:.1e}",
        transform=ax.transAxes, fontsize=14, va="top", color=COL_BLUE_DARK)
finish(fig, ax,
       f"{eta2:.0%} of the spread in travel is just which division you play in",
       "Season distance by division. Where a franchise sits on the map decides "
       "most of its travel before the schedule is written.",
       NOTE, FIGS / "fig7_division_decomposition.png")

# %% fig 8 - tight turnarounds against rest
fig, ax = plt.subplots(figsize=(11, 8))
ax.axvline(tt.b2b_with_travel.mean(), color=COL_GRAY, lw=1, ls=":")
ax.axhline(tt.rest_deficit_games.mean(), color=COL_GRAY, lw=1, ls=":")
# Both axes are small integers, so a dozen teams land on exactly the same
# point. Spread each tied cluster horizontally rather than letting the labels
# stack on top of one another.
cell = tt.groupby(["b2b_with_travel", "rest_deficit_games"])
tt["cell_pos"] = cell.cumcount()
tt["x_dodge"] = (tt.b2b_with_travel
                 + (tt.cell_pos - (cell.team.transform("size") - 1) / 2) * 0.30)
ax.scatter(tt.x_dodge, tt.rest_deficit_games, s=150, zorder=3,
           color=tt.color, edgecolor="white", linewidth=1.1)
for _, r in tt.iterrows():
    # alternate the label above and below within a tied cluster; dodging alone
    # separates the dots but not four-character tricodes
    above = r.cell_pos % 2 == 0
    ax.annotate(r.team, (r.x_dodge, r.rest_deficit_games),
                textcoords="offset points", xytext=(0, 12 if above else -22),
                ha="center", fontsize=10, color=COL_BLUE_DARK)
ax.set_xlabel("Back-to-backs that require changing city",
              fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylabel("Games facing a better-rested opponent", fontsize=hd.FS_AXIS_LABEL)
ax.margins(x=0.06, y=0.09)
ax.legend(handles=[Patch(facecolor=DIV_COLORS[k], label=k) for k in DIVISION_ORDER],
          frameon=False, fontsize=hd.FS_LEGEND, loc="lower left")
finish(fig, ax,
       "Buffalo and Pittsburgh fly the least and still get the worst of the calendar",
       "Travel back-to-backs against games started at a rest disadvantage. "
       "Dotted lines mark the league average on each.",
       NOTE, FIGS / "fig8_b2b_vs_rest.png")

# %% fig 11 and 12 - the trade-off between distance and calendar
# The two burdens the league does NOT control (geography) and the ones it does
# (when the games fall) point in opposite directions. These two figures make
# that concrete: the scatter quantifies it, the slope chart shows it team by
# team.
CAL_COLS = ["b2b_with_travel", "three_in_four", "rest_deficit_games"]
TRV_COLS = ["total_km", "tz_crossings", "road_days"]


def zc(col):
    v = tt[col].astype(float)
    return (v - v.mean()) / v.std(ddof=0)


tt["cal_z"] = pd.concat([zc(c) for c in CAL_COLS], axis=1).mean(axis=1)
tt["trav_z"] = pd.concat([zc(c) for c in TRV_COLS], axis=1).mean(axis=1)
tt["cal_rank"] = tt.cal_z.rank(ascending=False, method="min").astype(int)
tt["trav_rank"] = tt.trav_z.rank(ascending=False, method="min").astype(int)

slope, icept, rval, pval, _ = stats.linregress(tt.total_km, tt.cal_z)
print(f"  calendar vs distance r={rval:+.3f} p={pval:.3f}; "
      f"vs travel composite r={tt.cal_z.corr(tt.trav_z):+.3f}")

# ---- fig 11: the scatter ---------------------------------------------------
fig, ax = plt.subplots(figsize=(11.5, 8.4))
xs = np.linspace(tt.total_km.min() * 0.97, tt.total_km.max() * 1.03, 50)
ax.plot(xs / 1000, icept + slope * xs, color=COL_BLUE_DARK, lw=1.6,
        ls=(0, (6, 4)), zorder=2)
ax.axhline(0, color=COL_GRAY, lw=0.9, ls=":", zorder=1)
ax.axvline(tt.total_km.mean() / 1000, color=COL_GRAY, lw=0.9, ls=":", zorder=1)
ax.scatter(tt.total_km / 1000, tt.cal_z, s=150, zorder=4, color=tt.color,
           edgecolor="white", linewidth=1.1)
# nudge labels that would land on each other; UTA/DAL and EDM/VAN sit almost
# exactly on top of one another otherwise
_placed = []
for _, r in tt.sort_values("total_km").iterrows():
    px, py = r.total_km / 1000, r.cal_z
    near = sum(1 for qx, qy in _placed if abs(qx - px) < 2.2 and abs(qy - py) < 0.22)
    dy = (11, -17, 24, -30)[near % 4]
    ax.annotate(r.team, (px, py), textcoords="offset points", xytext=(0, dy),
                ha="center", va="bottom" if dy > 0 else "top",
                fontsize=9.5, color=COL_BLUE_DARK)
    _placed.append((px, py))
for team, dx, dy, txt in (
        ("PIT", 4.0, -0.30,
         "Pittsburgh: flies the fewest kilometres in the\n"
         "league, and faces a rested opponent 29 times"),
        ("VGK", -3.4, 0.42,
         "Vegas: flies the most,\nand faces one 18 times")):
    r = tt[tt.team == team].iloc[0]
    ax.annotate(txt, (r.total_km / 1000, r.cal_z),
                xytext=(r.total_km / 1000 + dx, r.cal_z + dy),
                fontsize=11.5, color=COL_BLUE_DARK,
                ha="left" if dx > 0 else "right",
                va="top" if dy < 0 else "bottom",
                arrowprops=dict(arrowstyle="-", color=COL_GRAY, lw=1.0))
ax.text(0.975, 0.955, f"r = {rval:.2f}   p = {pval:.3f}", transform=ax.transAxes,
        ha="right", va="top", fontsize=14, weight="bold", color=COL_BLUE_DARK)
ax.set_xlabel("Kilometres flown over the season (thousands)",
              fontsize=hd.FS_XAXIS_LABEL)
ax.set_ylabel("Calendar burden  (higher is harder)",
              fontsize=hd.FS_AXIS_LABEL)
ax.legend(handles=[Patch(facecolor="#6E7787" if k == "Central" else DIV_COLORS[k],
                         label=k) for k in DIVISION_ORDER],
          frameon=False, fontsize=hd.FS_LEGEND, loc="lower left")
finish(fig, ax,
       "The teams that fly the farthest get the easiest calendars",
       "Back-to-backs in two cities, three-games-in-four-nights and games "
       "against a rested opponent, against distance flown.",
       NOTE, FIGS / "fig11_distance_vs_calendar.png")

# ---- fig 12: the reversal, team by team ------------------------------------
d = tt.sort_values("trav_rank")
fig, ax = plt.subplots(figsize=(10.5, 13))
for _, r in d.iterrows():
    swing = r.cal_rank - r.trav_rank
    col = (COL_OIL_ORANGE if swing >= 8 else
           COL_BLUE_DARK if swing <= -8 else COL_GRAY)
    ax.plot([0, 1], [r.trav_rank, r.cal_rank], color=col,
            lw=2.2 if abs(swing) >= 8 else 1.0,
            alpha=0.95 if abs(swing) >= 8 else 0.45, zorder=3 if abs(swing) >= 8 else 2)
    ax.text(-0.035, r.trav_rank, f"{r.team}  {r.trav_rank}", ha="right",
            va="center", fontsize=10.5, color=COL_BLUE_DARK)
    ax.text(1.035, r.cal_rank, f"{r.cal_rank}  {r.team}", ha="left",
            va="center", fontsize=10.5, color=COL_BLUE_DARK)
ax.set_xlim(-0.30, 1.30)
ax.set_ylim(33.5, -2.6)
ax.axis("off")
for x, lab in ((0, "TRAVEL"), (1, "CALENDAR")):
    ax.text(x, -1.9, lab, ha="center", va="center", fontsize=14, weight="bold",
            color=COL_BLUE_DARK)
    ax.text(x, -1.0, "hardest at the top", ha="center", va="center",
            fontsize=11, style="italic", color=COL_GRAY)
ax.legend(handles=[
    Line2D([], [], color=COL_OIL_ORANGE, lw=2.2,
           label="Hard travel, easy calendar"),
    Line2D([], [], color=COL_BLUE_DARK, lw=2.2,
           label="Easy travel, hard calendar"),
    Line2D([], [], color=COL_GRAY, lw=1.0, label="Little change")],
    frameon=False, fontsize=hd.FS_LEGEND, loc="lower center",
    bbox_to_anchor=(0.5, -0.055), ncol=3)
finish(fig, ax,
       "Pittsburgh has the league's easiest travel and its hardest calendar",
       "Each team's rank on travel against its rank on the calendar.",
       NOTE, FIGS / "fig12_travel_calendar_reversal.png", title_x=0.045)

big = d.assign(swing=d.cal_rank - d.trav_rank)
print("  biggest reversals: " + ", ".join(
    f"{r.team} {r.trav_rank}->{r.cal_rank}"
    for _, r in big.reindex(big.swing.abs().sort_values(ascending=False).index).head(4).iterrows()))

# %% printed findings
bar = "=" * 78
print("\n" + bar)
print("NHL 2026-27 TRAVEL INEQUALITY - RANKINGS")
print(bar)

print("\nTRAVEL BURDEN INDEX  (1 = hardest schedule)\n")
print(f"{'#':>2}  {'team':<4} {'division':<13} {'TBI':>6} {'km':>9} {'flights':>8} "
      f"{'road d':>7} {'tz hrs':>7} {'b2b+trv':>8} {'3-in-4':>7} {'rest-':>6}")
for _, r in tt.sort_values("tbi_rank").iterrows():
    print(f"{r.tbi_rank:>2}  {r.team:<4} {r.division:<13} {r.tbi:>+6.2f} "
          f"{r.total_km:>9,.0f} {r.n_flights:>8.0f} {r.road_days:>7.0f} "
          f"{r.tz_crossings:>7.0f} {r.b2b_with_travel:>8.0f} "
          f"{r.three_in_four:>7.0f} {r.rest_deficit_games:>6.0f}")

print(f"\n\nHOW UNEQUAL IS IT?\n")
for col, label in [("total_km", "distance flown"),
                   ("road_days", "days on the road"),
                   ("tz_crossings", "time-zone hours crossed"),
                   ("n_flights", "flights taken")]:
    v = tt[col]
    print(f"  {label:26s} Gini {gini(v):.3f}   {v.min():>8,.0f} - {v.max():>8,.0f}"
          f"   ratio {v.max()/v.min():.2f}x")
print(f"\n  Heaviest schedule    {tt.loc[tt.km_rank.idxmin(), 'team']}  "
      f"{tt.total_km.max():,.0f} km  ({tt.total_km.max()/KM_PER_MI:,.0f} miles)")
print(f"  Lightest schedule    {tt.loc[tt.km_rank.idxmax(), 'team']}  "
      f"{tt.total_km.min():,.0f} km  ({tt.total_km.min()/KM_PER_MI:,.0f} miles)")
print(f"  Difference           {tt.total_km.max()-tt.total_km.min():,.0f} km  "
      f"({(tt.total_km.max()-tt.total_km.min())/KM_PER_MI:,.0f} miles)")
print(f"\n  Division explains eta^2 = {eta2:.3f} of the variance in distance "
      f"(F(3,28) = {F:.1f}, p = {p:.2e})")
print(f"  TBI vs raw distance, Spearman rho = "
      f"{tt.tbi.corr(tt.total_km, method='spearman'):.3f}")

print("\n\nWITHIN-TEAM LUMPINESS  (1 = most concentrated into bursts)\n")
lump = tt.sort_values("lumpiness_rank")
print(f"{'#':>2}  {'team':<4} {'wk Gini':>8} {'worst 7d':>9} {'worst 14d':>10} "
      f"{'trips':>6} {'longest':>8}")
for _, r in lump.iterrows():
    print(f"{r.lumpiness_rank:>2}  {r.team:<4} {r.week_km_gini:>8.3f} "
          f"{r.max_7day_km:>9,.0f} {r.max_14day_km:>10,.0f} {r.n_trips:>6.0f} "
          f"{r.longest_trip_days:>6.0f}d")

print("\n\nSENSITIVITY - THE FOUR TEAMS THAT PLAY IN EUROPE\n")
cmp = (tt[["team", "total_km", "km_rank", "tbi_rank"]]
       .merge(tte[["team", "total_km", "km_rank", "tbi_rank"]],
              on="team", suffixes=("", "_eu")))
cmp["delta_km"] = cmp.total_km_eu - cmp.total_km
eu = cmp[cmp.delta_km > 1].sort_values("delta_km", ascending=False)
print(f"{'team':<5} {'km excl.':>9} {'km incl.':>9} {'added':>8} "
      f"{'km rank':>9} {'-> incl.':>9} {'TBI rank':>9} {'-> incl.':>9}")
for _, r in eu.iterrows():
    print(f"{r.team:<5} {r.total_km:>9,.0f} {r.total_km_eu:>9,.0f} "
          f"{r.delta_km:>8,.0f} {r.km_rank:>9.0f} {r.km_rank_eu:>9.0f} "
          f"{r.tbi_rank:>9.0f} {r.tbi_rank_eu:>9.0f}")
print(f"\n  League distance Gini  {gini(tt.total_km):.3f} excluding Europe, "
      f"{gini(tte.total_km):.3f} including it")
print(f"\n  figures written to {FIGS}")
