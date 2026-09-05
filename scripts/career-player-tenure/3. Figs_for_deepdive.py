"""
3. Figs_for_deepdive.py - the career-tenure figures.

Reads the derived tables from S3 and writes PNGs into
static/images/deep-dives/career-tenure/ for the post to reference.

Figures 1-5:  league experience mix, experience by position, career length by
              cohort, survival curves, career length by position.
"""

# %% imports and configuration
import sys
from pathlib import Path

import numpy as np
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import s3fs
from matplotlib.ticker import FuncFormatter
from statsmodels.duration.survfunc import SurvfuncRight
from statsmodels.nonparametric.smoothers_lowess import lowess

try:
    HERE = Path(__file__).resolve().parent
except NameError:                       # Spyder cell execution
    HERE = Path("/Users/dwiwad/dev/hockey_site/scripts/career-player-tenure")
REPO = HERE.parents[1]

for p in (str(REPO), str(HERE)):        # REPO for app.*, HERE for hd_style
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from app.core.config import S3_BUCKET
except (ImportError, KeyError):
    S3_BUCKET = "hockey-decoded"

from hd_style import (COL_BLUE_DARK as BLUE_DARK, COL_BLUE_PALE as BLUE_PALE,
                      COL_OIL_ORANGE as ORANGE, COL_GRAY as GRAY,
                      FS_AXIS_LABEL, FS_XAXIS_LABEL, FS_TICK,
                      finish as _finish, legend as hd_legend)

SLUG = "career-tenure"
PREFIX = f"static-ds-analyses/{SLUG}"
FIG_DIR = REPO / "static" / "images" / "deep-dives" / SLUG
SO = {"anon": False}

POS_COLORS = {"Forward": BLUE_DARK, "Defense": BLUE_PALE, "Goalie": ORANGE}
POSMAP = {"C": "Forward", "L": "Forward", "R": "Forward",
          "D": "Defense", "G": "Goalie"}
# Era boundaries as used in posts/nhl-player-demographics.md
ERAS = [(1942, "1942 Original Six"), (1967, "1967 expansion"),
        (1991, "1991"), (2017, "2017")]


def read(name):
    return pd.read_parquet(f"s3://{S3_BUCKET}/{PREFIX}/{name}.parquet",
                           storage_options=SO)


def finish(fig, ax, title, subtitle, note, fname, **kw):
    _finish(fig, ax, title, subtitle, note, str(FIG_DIR / fname), **kw)


# %% load
car = read("player_careers")
coh = read("cohort_summary")
ps = read("player_seasons")

ps["year"] = ps.season // 10000
ps["pos_group"] = ps.position.str[0].map(POSMAP)
season_order = {y: i for i, y in enumerate(np.sort(ps.year.unique()))}
ps["sidx"] = ps.year.map(season_order)

# per player-season experience, for figs 1 and 2
ps2 = ps.merge(car[["playerId", "first_idx"]], on="playerId")
ps2["exp"] = ps2.sidx - ps2.first_idx
print(f"{len(car):,} careers, {len(ps2):,} player-seasons")


# %% FIG 1 - league experience mix by season
ps2["bucket"] = pd.cut(ps2.exp, [-1, 0, 3, 9, 99],
                       labels=["Rookie", "1-3 seasons", "4-9 seasons", "10+ seasons"])
mix = (ps2.groupby(["year", "bucket"], observed=True).playerId.nunique()
          .unstack(fill_value=0))
mix = mix.div(mix.sum(axis=1), axis=0)

fig, ax = plt.subplots(figsize=(12, 7))
ax.stackplot(mix.index, [mix[c] for c in mix.columns], labels=list(mix.columns),
             colors=[ORANGE, "#F0A07C", BLUE_PALE, BLUE_DARK], alpha=.95)
ax.set_xlim(mix.index.min(), mix.index.max())
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y*100)}%"))
ax.set_ylabel("Share of players in the league", fontsize=FS_AXIS_LABEL)
for yr, lbl in ERAS:
    ax.axvline(yr, color="white", lw=1.1, ls=":", alpha=.75)
    ax.text(yr + 0.8, .035, lbl, fontsize=9.5, color="white", rotation=90)
h, l = ax.get_legend_handles_labels()
hd_legend(ax, h[::-1], l[::-1], loc="upper left", bbox_to_anchor=(1.01, 1))
finish(fig, ax, "The rookie share of NHL rosters has declined since the 1940s",
       "Rookies made up 23% of the league across the 1940s and 1950s, and 13% across the 2020s. Dotted lines mark league eras.",
       "Data: NHL Stats API, regular season, 1918-19 to 2025-26",
       "fig1_experience_mix.png")


# %% FIG 2 - mean experience by season and position
fig, ax = plt.subplots(figsize=(12, 7))
for g in ["Forward", "Defense", "Goalie"]:
    d = ps2[ps2.pos_group == g].groupby("year").exp.mean()
    ax.scatter(d.index, d.values, color=POS_COLORS[g], alpha=.18, s=22)
    sm = lowess(d.values, d.index, frac=.18, return_sorted=True)
    ax.plot(sm[:, 0], sm[:, 1], color=POS_COLORS[g], lw=3.2, label=g)
ax.set_ylabel("Avg. seasons of NHL experience", fontsize=FS_AXIS_LABEL)
for yr, _ in ERAS:
    ax.axvline(yr, color=GRAY, lw=1, ls=":", alpha=.7)
hd_legend(ax, title="Position")
finish(fig, ax, "Average NHL experience fluctuates with the eras of the league",
       "Mean seasons of experience among players active in each season, by position. Dotted lines mark league eras.",
       "Data: NHL Stats API, regular season, 1918-19 to 2025-26",
       "fig2_experience_by_position.png")


# %% FIG 3 - KM median career length by debut cohort
fig, ax = plt.subplots(figsize=(12, 7))
ax.fill_between(coh.year, coh.lo, coh.hi, color=BLUE_PALE, alpha=.22, lw=0)
ax.plot(coh.year, coh.km_median, color=BLUE_DARK, lw=3,
        label="Kaplan-Meier median (censoring-aware)")
ax.plot(coh.year, coh.naive_completed, color=ORANGE, lw=2, ls="--",
        label="Naive mean of completed careers only")
ax.set_ylabel("Career length (seasons)", fontsize=FS_AXIS_LABEL)
ax.set_xlabel("Debut season", fontsize=FS_XAXIS_LABEL)
hd_legend(ax, loc="upper right")
finish(fig, ax, "Median career length by debut season",
       "Kaplan-Meier median with a 95% band. The dashed line drops active players instead of censoring them, and falls away after 2005.",
       "Data: NHL Stats API. Debut cohorts with n>=25. Shaded band = 95% CI",
       "fig3_career_length_by_cohort.png")


# %% FIG 4 - survival curves for selected cohorts
bands = [(1950, 1959, "1950s debuts", "#7E8AA2"),
         (1980, 1989, "1980s debuts", BLUE_PALE),
         (2000, 2009, "2000s debuts", BLUE_DARK),
         (2015, 2019, "2015-19 debuts", ORANGE)]

fig, ax = plt.subplots(figsize=(12, 7))
for lo_y, hi_y, lbl, c in bands:
    grp = car[(car.first_year >= lo_y) & (car.first_year <= hi_y)]
    sf = SurvfuncRight(grp.span.values, (~grp.censored).astype(int).values)
    # surv_times starts at the first event time, by which point the first drop
    # is already applied. Anchor at (0, 100%) so that step is visible.
    t = np.concatenate([[0], sf.surv_times])
    s = np.concatenate([[1.0], sf.surv_prob])
    ax.step(t, s, where="post", color=c, lw=3, label=f"{lbl}  (n={len(grp):,})")
ax.set_xlim(0, 22)
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y*100)}%"))
ax.set_xlabel("Seasons since debut", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Share still in the NHL", fontsize=FS_AXIS_LABEL)
hd_legend(ax)
finish(fig, ax, "Recent debut cohorts survive their first seasons at higher rates",
       "Share of each debut cohort still in the NHL. After one season, 71% of 1950s debutants remain, against 86% of 2015-19 debutants.",
       "Data: NHL Stats API. Active players right-censored",
       "fig4_survival_curves.png")


# %% FIG 5 - KM median by debut decade and position
# Only ~8 goalies debut per year, so single-year cohorts are far too thin to
# estimate a median from. Pool into decades.
rows = []
with np.errstate(divide="ignore", invalid="ignore"):
    for (dec, g), grp in car.groupby(["decade", "pos_group"]):
        if len(grp) < 30 or dec < 1920 or dec >= 2020:
            continue
        sf = SurvfuncRight(grp.span.values, (~grp.censored).astype(int).values)
        try:
            rows.append(dict(decade=dec, pos=g, med=sf.quantile(.5), n=len(grp)))
        except Exception:
            pass
pos_dec = pd.DataFrame(rows).dropna()

fig, ax = plt.subplots(figsize=(12, 7))
decs = sorted(pos_dec.decade.unique())
w = .26
for i, g in enumerate(["Forward", "Defense", "Goalie"]):
    d = pos_dec[pos_dec.pos == g].set_index("decade").reindex(decs)
    ax.bar([x + (i - 1) * w for x in range(len(decs))], d.med.values, width=w,
           color=POS_COLORS[g], label=g, edgecolor="white", lw=.8)
ax.set_xticks(range(len(decs)))
ax.set_xticklabels([f"{d}s" for d in decs], fontsize=13)
ax.set_ylabel("Median career length (seasons)", fontsize=FS_AXIS_LABEL)
ax.set_xlabel("Debut decade", fontsize=FS_XAXIS_LABEL)
hd_legend(ax, title="Position")
finish(fig, ax, "Median career length by debut decade and position",
       "Kaplan-Meier medians. Goalies are pooled by decade because roughly eight debut in a typical season.",
       "Data: NHL Stats API. Decade-position cells with n>=30",
       "fig5_career_length_by_position.png")

print(f"\nfigures written to {FIG_DIR}")

# %% load for figs 6-10
star = read("star_index")
star["hof"] = star.hof.astype(bool)

TIERS = ["Regular", "Solid", "Star", "Generational"]
TCOL = {"Regular": "#C3C9D2", "Solid": GRAY, "Star": BLUE_PALE, "Generational": ORANGE}


def km(g):
    return SurvfuncRight(g.span.values, (~g.censored).astype(int).values)


def step_xy(sf):
    """KM curve anchored at (0, 100%) so the first drop is visible."""
    return (np.concatenate([[0], sf.surv_times]),
            np.concatenate([[1.0], sf.surv_prob]))


print(f"{len(star):,} skaters with 60+ GP in their first three seasons")
print(star.tier.value_counts().reindex(TIERS).to_string())


# %% FIG 6 - survival by star tier
fig, ax = plt.subplots(figsize=(12, 7))
for t in TIERS:
    g = star[star.tier == t]
    x, y = step_xy(km(g))
    ax.step(x, y, where="post", color=TCOL[t], lw=3, label=f"{t}  (n={len(g):,})")
ax.set_xlim(0, 25)
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v*100)}%"))
ax.set_xlabel("Seasons since debut", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Share still in the NHL", fontsize=FS_AXIS_LABEL)
hd_legend(ax, title="First-3-season scoring tier")
finish(fig, ax, "Career length rises with early-career scoring",
       "Share still in the NHL by first-three-season scoring tier. After ten seasons, 87% of the top tier remain against 39% of the rest.",
       "Data: NHL Stats API. Skaters with 60+ games in their first three seasons",
       "fig6_survival_by_star_tier.png")

# verify the two numbers quoted in that subtitle
for lbl, g in [("Generational", star[star.tier == "Generational"]),
               ("everyone else", star[star.tier != "Generational"])]:
    sf = km(g)
    s10 = sf.surv_prob[sf.surv_times <= 10][-1]
    print(f"  10-season survival, {lbl}: {s10*100:.0f}%")


# %% FIG 7 - scoring rate against career length
# Deliberately plain: tier colours and the active/retired split are carried by
# figs 6 and 9, and stacking them here buried the one thing this chart is for -
# the spread around the trend.
fig, ax = plt.subplots(figsize=(12, 7))
rng = np.random.default_rng(7)
ax.scatter(star.rel, star.span + rng.uniform(-.28, .28, len(star)),
           s=24, color=GRAY, alpha=.35, edgecolors="none", zorder=2)

star["_b"] = pd.cut(star.rel, np.arange(0.4, 3.2, 0.2))
tr = (star.groupby("_b", observed=True)
          .agg(x=("rel", "median"), y=("span", "median")).dropna())
ax.plot(tr.x, tr.y, color=BLUE_DARK, lw=3, zorder=4)
ax.annotate("Median career length", (tr.x.iloc[-1], tr.y.iloc[-1]),
            (tr.x.iloc[-1] - .78, tr.y.iloc[-1] + 6.0), fontsize=13,
            color=BLUE_DARK, ha="left",
            arrowprops=dict(arrowstyle="-", lw=1, color=BLUE_DARK))

ax.axvline(1.0, color=GRAY, ls=":", lw=1.2, zorder=1)
ax.text(1.03, 27.4, "league average", fontsize=11, color=GRAY, style="italic")
ax.set_xlabel("Points in first three seasons, relative to a league-average player at the same position",
              fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Career length (seasons)", fontsize=FS_AXIS_LABEL)
ax.set_xlim(0.3, 3.2)
ax.set_ylim(0, 29)
finish(fig, ax, "Career length by early-career scoring rate",
       f"Each point is one of {len(star):,} skaters. Median career length rises from {tr.y.iloc[0]:.0f} to {tr.y.iloc[-1]:.0f} seasons across the range, with wide spread throughout.",
       "Data: NHL Stats API. Vertical jitter added. Active careers are included at their current length",
       "fig7_star_index_vs_career.png")
star = star.drop(columns=["_b"])


# %% FIG 8 - Hall of Fame, an entirely independent definition
fig, ax = plt.subplots(figsize=(12, 7))
for lbl, g, c in [("Hall of Fame", star[star.hof], ORANGE),
                  ("Everyone else", star[~star.hof], BLUE_PALE)]:
    x, y = step_xy(km(g))
    ax.step(x, y, where="post", color=c, lw=3, label=f"{lbl}  (n={len(g):,})")
ax.set_xlim(0, 25)
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v*100)}%"))
ax.set_xlabel("Seasons since debut", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Share still in the NHL", fontsize=FS_AXIS_LABEL)
hd_legend(ax)
finish(fig, ax, "Hall of Fame skaters have longer careers than their peers",
       "Median career length is 16 seasons for Hall of Famers and 9 for everyone else. Induction lags retirement, so no active player is included.",
       "Data: NHL Stats API isInHallOfFame flag. Induction lags retirement, so recent stars are absent",
       "fig8_hof_survival.png")

print(f"  HOF median span {star[star.hof].span.median():.0f}, "
      f"others {star[~star.hof].span.median():.0f}")


# %% FIGS 9 & 10 - the 28 highest-scoring debuts
# Split across two charts so fig 9 stays a tenure chart and fig 10 carries the
# scoring rate; overlaying them made neither readable.
top = star.nlargest(28, "rel").sort_values("rel")     # ascending: highest at top
labels = [f"{r['name']}  ({r.first_yr}, {r.pos})" for _, r in top.iterrows()]
y = np.arange(len(top))

# --- fig 9: career length
fig, ax = plt.subplots(figsize=(12, 10))
cols = [ORANGE if c else BLUE_DARK for c in top.censored]
ax.hlines(y, 0, top.span, color=cols, lw=2.4, alpha=.55)
ax.scatter(top.span, y, s=95, color=cols, zorder=3)
for yi, (_, r) in zip(y, top.iterrows()):
    ax.text(r.span + .45, yi, f"{r.span:.0f}" + ("+" if r.censored else ""),
            va="center", fontsize=12, color=cols[yi])
ax.set_yticks(y)
ax.set_yticklabels(labels)
ax.set_xlabel("Career length (seasons)", fontsize=FS_XAXIS_LABEL)
ax.set_xlim(0, 29)
ax.scatter([], [], s=95, color=BLUE_DARK, label="Finished")
ax.scatter([], [], s=95, color=ORANGE, label="Active (+)")
hd_legend(ax, loc="upper left", bbox_to_anchor=(0.80, 0.99))
finish(fig, ax, "Career length of the 28 highest-scoring NHL debuts",
       "Players ranked by scoring across their first three seasons. A plus marks a career still in progress.",
       "Data: NHL Stats API. Skaters with 60+ games in their first three seasons",
       "fig9_career_length_top_debuts.png", title_x=0.045)

# --- fig 10: the scoring rate itself
fig, ax = plt.subplots(figsize=(12, 10))
ax.hlines(y, 1, top.rel, color=BLUE_PALE, lw=2.4, alpha=.55)
ax.scatter(top.rel, y, s=95, color=BLUE_DARK, zorder=3)
for yi, (_, r) in zip(y, top.iterrows()):
    ax.text(r.rel + .025, yi, f"{r.rel:.2f}", va="center", fontsize=12,
            color=BLUE_DARK)
ax.set_yticks(y)
ax.set_yticklabels(labels)
ax.set_xlabel("Points relative to a league-average player at the same position\n(the axis begins at league average)",
              fontsize=FS_XAXIS_LABEL)
ax.set_xlim(1, 3.25)
finish(fig, ax, "Scoring across the first three NHL seasons, relative to position",
       "A value of 2.0 means twice the points of a league-average player at the same position over the same games.",
       f"Position-relative scoring over-selects defencemen: {(top.pos == 'D').sum()} of these 28 are D, against {(star.pos == 'D').mean()*100:.0f}% of all skaters",
       "fig10_star_index_top_debuts.png", title_x=0.045)

# %% load for figs 11-14
pairs = read("matched_pairs").sort_values("star_rel").reset_index(drop=True)
TOP_N = len(pairs)
SPAN_MAX = 29        # same x-limit as fig 9, so the charts compare directly
REL_MAX = 3.45       # highest star index is ~3.01; the rest is label room
y = np.arange(TOP_N)

# Symmetric frames so the two sides of each butterfly plot the same way.
LEFT = pd.DataFrame({"name": pairs.star, "year": pairs.star_year, "pos": pairs.pos,
                     "rel": pairs.star_rel, "span": pairs.star_span,
                     "active": pairs.star_active})
RIGHT = pd.DataFrame({"name": pairs.match, "year": pairs.match_year, "pos": pairs.pos,
                      "rel": pairs.match_rel, "span": pairs.match_span,
                      "active": pairs.match_active})


def label(r):
    return f"{r['name']}  ({int(r.year)}, {r.pos})"


# Both members of a pair debuted in the same season, so they have had the same
# number of seasons in which to build a career - censoring is held constant by
# construction rather than modelled away. That also means pairs where both are
# still active are capped at the same length and tell us nothing, so the
# headline claim is restricted to pairs where both careers are finished.
both_done = (~LEFT.active.values) & (~RIGHT.active.values)
star_wins = (LEFT.span.values[both_done] > RIGHT.span.values[both_done]).sum()
print(f"{both_done.sum()} pairs with both careers finished; star longer in {star_wins}")
print(f"median career  stars {LEFT.span.median():.1f}  matched {RIGHT.span.median():.1f}")


# %% FIG 11 - career length of the matched below-average debuts (mirrors fig 9)
fig, ax = plt.subplots(figsize=(12, 10))
cols = [ORANGE if a else BLUE_DARK for a in RIGHT.active]
ax.hlines(y, 0, RIGHT.span, color=cols, lw=2.4, alpha=.55)
ax.scatter(RIGHT.span, y, s=95, color=cols, zorder=3)
for yi, (_, r) in zip(y, RIGHT.iterrows()):
    ax.text(r.span + .45, yi, f"{r.span:.0f}" + ("+" if r.active else ""),
            va="center", fontsize=12, color=cols[yi])
ax.set_yticks(y)
ax.set_yticklabels([label(r) for _, r in RIGHT.iterrows()])
ax.set_xlabel("Career length (seasons)", fontsize=FS_XAXIS_LABEL)
ax.set_xlim(0, SPAN_MAX)
ax.scatter([], [], s=95, color=BLUE_DARK, label="Finished")
ax.scatter([], [], s=95, color=ORANGE, label="Active (+)")
hd_legend(ax, loc="upper left", bbox_to_anchor=(0.80, 0.99))
finish(fig, ax, "Career length of 28 matched below-average debuts",
       f"Each is the below-average scorer closest to one of the 28 highest-scoring debuts on position, debut year and games played. Median career: {RIGHT.span.median():.0f} seasons against {LEFT.span.median():.1f}.",
       "Data: NHL Stats API. Same x-axis and row order as the top-debut chart: each row is that star's matched partner",
       "fig11_career_length_matched_low_debuts.png", title_x=0.045)


# %% FIG 12 - the matched sample's scoring (mirrors fig 10)
fig, ax = plt.subplots(figsize=(12, 10))
ax.hlines(y, RIGHT.rel, 1, color=BLUE_PALE, lw=2.4, alpha=.55)
ax.scatter(RIGHT.rel, y, s=95, color=BLUE_DARK, zorder=3)
for yi, (_, r) in zip(y, RIGHT.iterrows()):
    ax.text(r.rel - .022, yi, f"{r.rel:.2f}", va="center", ha="right",
            fontsize=12, color=BLUE_DARK)
ax.axvline(1.0, color=GRAY, ls=":", lw=1.2, zorder=1)
ax.set_ylim(-1.0, TOP_N + 0.6)          # headroom so the rule's label clears row 1
ax.text(0.985, TOP_N - 0.05, "league average", fontsize=11, color=GRAY,
        style="italic", ha="right", va="center")
ax.set_yticks(y)
ax.set_yticklabels([label(r) for _, r in RIGHT.iterrows()])
ax.set_xlabel("Points relative to a league-average player at the same position\n(the axis ends at league average)",
              fontsize=FS_XAXIS_LABEL)
ax.set_xlim(0, 1.04)
finish(fig, ax, "Scoring across the first three NHL seasons, the matched sample",
       f"The bar is the shortfall from league average. These 28 averaged {RIGHT.rel.mean():.2f} times a league-average player at the same position; their star partners, {LEFT.rel.mean():.2f}.",
       "Data: NHL Stats API. Skaters with 60+ games in their first three seasons",
       "fig12_star_index_matched_low_debuts.png", title_x=0.045)


# %% helpers for the butterfly pairs
def pair_axes(figsize=(15, 11)):
    """Two panels growing outward from a shared centre line."""
    fig, (axL, axR) = plt.subplots(1, 2, figsize=figsize,
                                   gridspec_kw={"wspace": 0.035})
    for ax in (axL, axR):
        sns.despine(ax=ax, left=True, right=True, top=True)
        ax.tick_params(axis="both", labelsize=FS_TICK)
        ax.tick_params(axis="y", length=0)
        ax.set_yticks(y)
        ax.set_ylim(-0.8, TOP_N + 1.2)      # blank top row for the panel labels
    axR.yaxis.tick_right()
    return fig, axL, axR


def panel_label(ax, text):
    ax.text(np.mean(ax.get_xlim()), TOP_N + 0.4, text, ha="center", va="center",
            fontsize=15, weight="bold", color=BLUE_DARK)


def shared_xlabel(axL, text):
    """One x-label centred on the gutter instead of one per panel.

    Both panels carry the same units, so two labels is one too many - and at
    this width they collide. Axes-fraction x=1.02 is just past the left panel's
    right edge, i.e. the middle of the pair.
    """
    axL.set_xlabel(text, fontsize=FS_XAXIS_LABEL)
    axL.xaxis.set_label_coords(1.02, -0.055)


# %% FIG 13 - career length, star against matched partner
fig, axL, axR = pair_axes()
for ax, side, flip in ((axL, LEFT, True), (axR, RIGHT, False)):
    cols = [ORANGE if a else BLUE_DARK for a in side.active]
    ax.hlines(y, 0, side.span, color=cols, lw=2.4, alpha=.55)
    ax.scatter(side.span, y, s=95, color=cols, zorder=3)
    for yi, (_, r) in zip(y, side.iterrows()):
        ax.text(r.span + .5, yi, f"{r.span:.0f}" + ("+" if r.active else ""),
                va="center", ha="right" if flip else "left",
                fontsize=12, color=cols[yi])
    ax.set_yticklabels([label(r) for _, r in side.iterrows()])
    ax.set_xlim(SPAN_MAX, 0) if flip else ax.set_xlim(0, SPAN_MAX)
    # only the left panel keeps its 0, otherwise the two meet as "0 0"
    ax.set_xticks(np.arange(0, SPAN_MAX, 5) if flip else np.arange(5, SPAN_MAX, 5))

shared_xlabel(axL, "Career length (seasons)")
panel_label(axL, "Highest-scoring debuts")
panel_label(axR, "Matched below-average debuts")
axL.scatter([], [], s=95, color=BLUE_DARK, label="Finished")
axL.scatter([], [], s=95, color=ORANGE, label="Active (+)")
hd_legend(axL, loc="upper left", bbox_to_anchor=(0.01, 0.99))
_finish(fig, axL, "The highest-scoring debuts against their matched partners",
        f"Career length, same scale on both sides. Of the {both_done.sum()} pairs in which both careers are finished, the star lasted longer in {star_wins}.",
        "Data: NHL Stats API. Each row is one matched pair: same position, same debut year, similar games played",
        str(FIG_DIR / "fig13_career_length_top_vs_matched.png"), title_x=0.045)


# %% FIG 14 - early-career scoring, star against matched partner
fig, axL, axR = pair_axes()
for ax, side, hi, flip in ((axL, LEFT, REL_MAX, True), (axR, RIGHT, 0.0, False)):
    ax.hlines(y, 1.0, side.rel, color=BLUE_PALE, lw=2.4, alpha=.55)
    ax.scatter(side.rel, y, s=95, color=BLUE_DARK, zorder=3)
    off = .03 if flip else -.03
    for yi, (_, r) in zip(y, side.iterrows()):
        ax.text(r.rel + off, yi, f"{r.rel:.2f}", va="center",
                ha="right" if flip else "left", fontsize=12, color=BLUE_DARK)
    ax.set_yticklabels([label(r) for _, r in side.iterrows()])
    ax.set_xlim(hi, 1.0) if flip else ax.set_xlim(1.0, hi)
    # the left panel owns the shared 1.0 at the gutter
    ax.set_xticks(np.arange(1.0, 3.01, 0.5) if flip else np.arange(0, 0.76, 0.25))

shared_xlabel(axL, "Points in the first three seasons, relative to a league-average player at the same position")
panel_label(axL, "Highest-scoring debuts")
panel_label(axR, "Matched below-average debuts")
_finish(fig, axL, "Early-career scoring, star against matched partner",
        f"Each row is one matched pair, running outward from league average at the centre. The stars averaged {LEFT.rel.mean():.2f} times an average player at their position; their partners, {RIGHT.rel.mean():.2f}.",
        "Data: NHL Stats API. The panels are on different scales: scoring above average is unbounded, below average is floored at zero",
        str(FIG_DIR / "fig14_star_index_top_vs_matched.png"), title_x=0.045)

import statsmodels.api as sm

# %% load and fit for figs 15-18
d = read("team_season_experience")

ERAS = [(1917, 1941, "1917-1941"), (1942, 1966, "Original Six"),
        (1967, 1978, "1967-1978"), (1979, 2004, "1979-2004"),
        (2005, 2026, "Salary cap")]


def fit(y, X, groups):
    """Clustered by season: teams within a season are not independent - one
    team's points come out of another's."""
    return sm.OLS(y, sm.add_constant(X)).fit(cov_type="cluster",
                                             cov_kwds={"groups": groups})


# Dummies rather than demeaning: with an unbalanced panel, demeaning by season
# and then adding franchise dummies is only approximately two-way fixed
# effects. n is small enough that the dummies can just go in.
seas_d = pd.get_dummies(d.season, prefix="s", drop_first=True).astype(float)
fran_d = pd.get_dummies(d.teamId, prefix="t", drop_first=True).astype(float)

specs = {}
specs["Raw"] = fit(d.point_pct, d[["exp"]], d.season)
specs["+ season"] = fit(d.point_pct, pd.concat([d[["exp"]], seas_d], axis=1), d.season)
specs["+ franchise"] = fit(d.point_pct,
                           pd.concat([d[["exp"]], seas_d, fran_d], axis=1), d.season)

# First differences within a franchise: when a team got older than it was last
# year, did it get better? The strictest of the four.
d = d.sort_values(["teamId", "yr"])
lag = d.groupby("teamId")[["yr", "exp", "point_pct"]].shift(1)
fd = (d.assign(d_exp=d.exp - lag.exp, d_pp=d.point_pct - lag.point_pct,
               gap_yr=d.yr - lag.yr)
       .query("gap_yr == 1").dropna(subset=["d_exp", "d_pp"]))
specs["Year on year"] = fit(fd.d_pp, fd[["d_exp"]], fd.season)

rows = []
for name, m in specs.items():
    k = "d_exp" if "d_exp" in m.params.index else "exp"
    rows.append({"spec": name, "coef": m.params[k], "se": m.bse[k], "n": int(m.nobs)})
    print(f"  {name:<14} {m.params[k]*100:+6.2f} pp  (SE {m.bse[k]*100:.2f})  n={int(m.nobs):,}")
spec = pd.DataFrame(rows)


def binned(df, x, ycol, q=10):
    b = pd.qcut(df[x], q, duplicates="drop")
    o = df.groupby(b, observed=True).agg(x=(x, "mean"), y=(ycol, "mean"),
                                         n=(ycol, "size"), sd=(ycol, "std"))
    o["se"] = o.sd / np.sqrt(o.n)
    return o.reset_index(drop=True)


# %% FIG 15 - the league's experience over time
by_season = d.groupby("yr").apply(
    lambda g: np.average(g.exp, weights=g.player_games), include_groups=False)
post = by_season.loc[by_season.idxmax():]
trough_yr, trough = post.idxmin(), post.min()

fig, ax = plt.subplots(figsize=(12, 7))
# The league's own first decade is mechanical: in 1917-18 every player is a
# rookie because the NHL is, and the series can only climb until the first long
# careers exist. Drawn, but greyed and labelled.
FILL = 1927
ax.plot(by_season.loc[:FILL].index, by_season.loc[:FILL].values,
        color=GRAY, lw=2.6, zorder=2)
ax.plot(by_season.loc[FILL:].index, by_season.loc[FILL:].values,
        color=BLUE_DARK, lw=2.6, zorder=3)
ax.annotate("the league itself is new:\neveryone starts a rookie",
            (1920, by_season.loc[1920]), (1929, 1.3), fontsize=11, color=GRAY,
            ha="left", va="center",
            arrowprops=dict(arrowstyle="-", lw=1, color=GRAY))

# The war years are a spike, not a dip: enlistment took the young men and the
# clubs filled the gaps with old ones. 1945 is the decade's high point.
for x, lbl, dy in [(1945, "1945: wartime rosters\nlean on veterans", 1.0),
                   (1967, "Expansion\ndoubles the league", 1.0),
                   (1979, "WHA merger", -1.3), (2000, "Expansion to 30", -1.3)]:
    if x not in by_season.index:
        continue
    ax.axvline(x, color=GRAY, ls=":", lw=1.1, zorder=1)
    ax.annotate(lbl, (x, by_season.loc[x] + dy), fontsize=11, color=GRAY,
                ha="center", va="bottom" if dy > 0 else "top")
ax.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Mean prior NHL seasons", fontsize=FS_AXIS_LABEL)
ax.set_xlim(1917, 2026)
finish(fig, ax, "The NHL is as experienced now as at any time since the Original Six",
       f"Games-weighted mean prior NHL seasons of the players who dressed. Expansion resets it: the {by_season.idxmax()} peak of {by_season.max():.1f} fell to {trough:.1f} by {trough_yr}, and has taken since to recover.",
       "Data: NHL Stats API. Rookies count as zero. Weighted by games played for the team",
       "fig15_league_experience_by_season.png")


# %% FIG 16 - is the relationship there in every decade?
# An expansion team is young and bad at the same time, for reasons that have
# nothing to do with experience helping - hence the second series.
d["decade"] = (d.yr // 10) * 10
dec = []
for dc, g in d.groupby("decade"):
    if len(g) < 20:
        continue
    m = sm.OLS(g.point_pct_dev, sm.add_constant(g[["exp_dev"]])).fit()
    x = g[g.franchise_age >= 3]
    mx = sm.OLS(x.point_pct_dev, sm.add_constant(x[["exp_dev"]])).fit()
    dec.append({"decade": dc, "b": m.params.exp_dev, "se": m.bse.exp_dev,
                "b_est": mx.params.exp_dev, "n": len(g)})
dec = pd.DataFrame(dec)
pooled = specs["+ season"].params["exp"]

fig, ax = plt.subplots(figsize=(12, 7))
ax.axhline(0, color=GRAY, ls="-", lw=1.2, zorder=1)
ax.axhline(pooled, color=GRAY, ls=":", lw=1.4, zorder=1)
ax.text(2029, pooled, f"all seasons\n{pooled*100:+.1f}", fontsize=11,
        color=GRAY, va="center", ha="left", style="italic")
ax.errorbar(dec.decade + 5, dec.b, yerr=1.96 * dec.se, fmt="o", ms=11, lw=0,
            elinewidth=2.0, color=BLUE_DARK, zorder=3, label="All teams")
ax.scatter(dec.decade + 5, dec.b_est, s=52, marker="D", color=ORANGE, zorder=4,
           label="Excluding franchises in their first three seasons")
ax.set_xlabel("Decade", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Points % per extra season\nof team experience", fontsize=FS_AXIS_LABEL)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v*100:+.0f}"))
ax.set_xlim(1915, 2045)
ax.set_xticks(dec.decade + 5)
ax.set_xticklabels([f"{x}s" for x in dec.decade])
hd_legend(ax, loc="upper left")
finish(fig, ax, "The experience advantage is only consistent after the 1950s",
       "Slope of points percentage on team experience, decade by decade, both against the league average s it runs the other way.",
       "Data: NHL Stats API. Bars are 95% confidence intervals. New franchises are young and bad at once, hence the second series",
       "fig16_experience_by_decade.png")


# %% FIG 17 - the same coefficient under four specifications
fig, ax = plt.subplots(figsize=(12, 7))
yy = np.arange(len(spec))[::-1]
cols = [BLUE_DARK, BLUE_DARK, ORANGE, ORANGE]
ax.axvline(0, color=GRAY, ls=":", lw=1.2, zorder=1)
for yi, r, col in zip(yy, spec.itertuples(), cols):
    ax.errorbar(r.coef, yi, xerr=1.96 * r.se, fmt="o", ms=12, lw=0,
                elinewidth=2.2, color=col, zorder=3)
    ax.text(r.coef, yi + 0.22, f"{r.coef*100:+.2f}", ha="center", va="bottom",
            fontsize=13, color=col)
ax.set_yticks(yy)
ax.set_yticklabels(["Raw, all team-seasons", "Compared within the season",
                    "and within the franchise", "Year-on-year change, same team"])
ax.set_ylim(-0.7, len(spec) - 0.3)
ax.set_xlabel("Change in points percentage per extra season of team experience",
              fontsize=FS_XAXIS_LABEL)
# explicit whole-point ticks: the auto locator lands on 0.005-wide steps, which
# the percentage-point formatter then rounds into a run of repeated labels
hi = np.ceil((spec.coef + 1.96 * spec.se).max() * 100)
ax.set_xticks(np.arange(0, (hi + 1) / 100, 0.01))
ax.set_xlim(-0.004, (hi + 0.4) / 100)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v*100:+.0f}"))
finish(fig, ax, "How much of the experience advantage survives a control",
       f"The same coefficient under four specifications. Comparing a franchise to itself a year later leaves {spec.coef.iloc[3]*100:+.2f} points of the {spec.coef.iloc[1]*100:+.2f} found across teams.",
       "Data: NHL Stats API, 1917-2026. The raw estimate is the low one because league experience rose over time while points percentage could not",
       "fig17_experience_specifications.png", title_x=0.045)


# %% FIG 18 - rookies and veterans, the composition the mean hides
fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 7), sharey=True, sharex=True,
                               gridspec_kw={"wspace": 0.06})
for ax, col, colour, lab in (
        (axL, "rookie_share", ORANGE, "Rookie share of team games"),
        (axR, "vet_share", BLUE_DARK, "Ten-year-veteran share of team games")):
    b = binned(d, col + "_dev", "point_pct_dev", q=10)
    m = fit(d.point_pct_dev, d[[col + "_dev"]], d.season)
# %% FIG 18 - rookies and veterans, the composition the mean hides
fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 7), sharey=True, sharex=True,
                               gridspec_kw={"wspace": 0.06})
for ax, col, colour, lab in (
        (axL, "rookie_share", ORANGE, "Rookie share of team games"),
        (axR, "vet_share", BLUE_DARK, "Ten-year-veteran share of team games")):
    b = binned(d, col + "_dev", "point_pct_dev", q=10)
    m = fit(d.point_pct_dev, d[[col + "_dev"]], d.season)
    ax.axhline(0, color=GRAY, ls=":", lw=1.2, zorder=1)
    ax.axvline(0, color=GRAY, ls=":", lw=1.2, zorder=1)
    ax.errorbar(b.x, b.y, yerr=1.96 * b.se, fmt="o", ms=9, lw=0,
                elinewidth=1.6, color=colour, zorder=3)
    xs = np.linspace(b.x.min(), b.x.max(), 50)
    ax.plot(xs, m.params[col + "_dev"] * xs, color=colour, lw=2.5, alpha=.45, zorder=2)
    ax.text(0.5, 0.98, f"{m.params[col + '_dev']*10:+.1f} points per 10-point share",
            transform=ax.transAxes, ha="center", va="top", fontsize=15,
            weight="bold", color=colour)
    ax.set_xlabel(lab + ", vs the league average", fontsize=FS_XAXIS_LABEL)
    ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v*100:+.0f}%"))
    ax.tick_params(axis="both", labelsize=FS_TICK)
    sns.despine(ax=ax)
    ax.grid(False)
axL.set_ylabel("Points % minus the league average", fontsize=FS_AXIS_LABEL)
axL.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v*100:+.0f}"))
_finish(fig, axL, "Rookie vigour does not show up in the standings",
        "Deciles of each share, 1917-2026. Teams that lean on rookies lose and teams that lean on veterans win, but not symmetrically: point for point the rookie penalty is the larger.",
        "Data: NHL Stats API. Shares are of games played, not of roster spots. Bars are 95% confidence intervals",
        str(FIG_DIR / "fig18_rookies_and_veterans.png"), title_x=0.045)

# %% load and fit for figs 19-20
L = read("team_games")
ts_id = L.teamId.astype(str) + "_" + L.season.astype(str)


def cluster(y, X, groups):
    return sm.OLS(y, sm.add_constant(X)).fit(cov_type="cluster",
                                             cov_kwds={"groups": groups})


def pct(v, _=None):
    return f"{v*100:.0f}%"


def signed(pp):
    """Points of win probability, without rendering a null result as '-0.0'."""
    return "0.0" if abs(pp) < 0.05 else f"{pp:+.1f}"


# Both headline numbers come from the same one-variable form, so the slope
# drawn on each panel of fig 20 is the slope quoted above it. `within` is
# already demeaned within team-season, so by Frisch-Waugh this IS the
# team-season fixed-effects estimator - asserted below.
B, Bse = (lambda m: (m.params["between"], m.bse["between"]))(
    cluster(L.won, L[["between"]], ts_id))
W, Wse = (lambda m: (m.params["within"], m.bse["within"]))(
    cluster(L.won, L[["within"]], ts_id))

dm = L[["won", "exp", "opp_exp", "home"]].sub(
    L.groupby(["teamId", "season"])[["won", "exp", "opp_exp", "home"]].transform("mean"))
assert abs(cluster(dm.won, dm[["exp"]], ts_id).params["exp"] - W) < 1e-6
fe_fit = cluster(dm.won, dm[["exp", "opp_exp", "home"]], ts_id)
ols_fit = cluster(L.won, L[["exp", "opp_exp", "home"]], ts_id)
Bc, Wc = ols_fit.params["exp"], fe_fit.params["exp"]

# Clustered on the game: every game is in here twice, once from each side, so
# the naive standard error would be about a factor of root-2 too small.
gap_fit = sm.Logit(L.won, sm.add_constant(L[["gap"]])).fit(
    disp=0, cov_type="cluster", cov_kwds={"groups": L.game_id})

print(f"between teams {B*100:+.2f} pp (SE {Bse*100:.2f})")
print(f"within a team {W*100:+.2f} pp (SE {Wse*100:.2f}), "
      f"95% CI [{(W-1.96*Wse)*100:+.2f}, {(W+1.96*Wse)*100:+.2f}]")


def gbin(df, col, edges=None, q=None):
    b = pd.qcut(df[col], q) if q else pd.cut(df[col], edges)
    o = df.groupby(b, observed=True).agg(x=(col, "mean"), p=("won", "mean"),
                                         n=("won", "size"))
    o["se"] = np.sqrt(o.p * (1 - o.p) / o.n)
    return o.reset_index(drop=True)


# %% FIG 19 - win rate against the experience gap in the game
bins = gbin(L, "gap", edges=np.arange(-3.5, 3.51, 0.5))
BREAK = 0.5

fig, ax = plt.subplots(figsize=(12, 7))
ax.axhline(BREAK, color=GRAY, ls=":", lw=1.2, zorder=1)
grid = np.linspace(-3.5, 3.5, 200)
ax.plot(grid, gap_fit.predict(sm.add_constant(pd.DataFrame({"gap": grid}))),
        color=BLUE_PALE, lw=2.5, zorder=2, label="Logistic fit")
ax.errorbar(bins.x, bins.p, yerr=1.96 * bins.se, fmt="o", ms=9, lw=0,
            elinewidth=1.6, color=BLUE_DARK, zorder=3,
            label="Half-season bins (95% CI)")
ax.set_xlabel("Experience advantage over the opponent that night (seasons)",
              fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Win rate", fontsize=FS_AXIS_LABEL)
ax.set_xlim(-3.8, 3.8)
ax.set_ylim(0.35, 0.65)
ax.yaxis.set_major_formatter(plt.FuncFormatter(pct))
hd_legend(ax, loc="upper left")
finish(fig, ax, "The more experienced lineup wins more often",
       f"Every regular-season game, 2010-11 to 2024-25. Each additional season of average experience over the opponent is worth about {gap_fit.params['gap']/4*100:.1f} points of win probability.",
       "Data: NHL Stats API and game rosters. Each game appears twice, once from each side, so home advantage cancels",
       "fig19_win_rate_by_experience_gap.png")


# %% FIG 20 - the same effect, split between teams and within one team
bw, wi = gbin(L, "between", q=10), gbin(L, "within", q=10)

fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 7), sharey=True,
                               gridspec_kw={"wspace": 0.06})
panels = ((axL, bw, BLUE_DARK, B, "Between teams",
           "Team's experience minus the league average (seasons)"),
          (axR, wi, ORANGE, W, "Within one team",
           "Lineup minus the team's own season average (seasons)"))
for ax, b, col, coef, head, xlab in panels:
    ax.axhline(0.5, color=GRAY, ls=":", lw=1.2, zorder=1)
    ax.axvline(0, color=GRAY, ls=":", lw=1.2, zorder=1)
    xs = np.linspace(b.x.min(), b.x.max(), 50)
    ax.plot(xs, 0.5 + coef * xs, color=col, lw=2.5, alpha=.45, zorder=2)
    ax.errorbar(b.x, b.p, yerr=1.96 * b.se, fmt="o", ms=9, lw=0,
                elinewidth=1.6, color=col, zorder=3)
    ax.text(0.5, 0.98, f"{head}:  {signed(coef*100)} points per season",
            transform=ax.transAxes, ha="center", va="top", fontsize=15,
            weight="bold", color=col)
    ax.set_xlim(-2.1, 2.1)
    ax.set_xlabel(xlab, fontsize=FS_XAXIS_LABEL)
    ax.tick_params(axis="both", labelsize=FS_TICK)
    sns.despine(ax=ax)
    ax.grid(False)
axL.set_ylim(0.40, 0.60)
axL.set_yticks(np.arange(0.40, 0.601, 0.04))
axL.yaxis.set_major_formatter(plt.FuncFormatter(pct))
axL.set_ylabel("Win rate", fontsize=FS_AXIS_LABEL)
_finish(fig, axL, "Experience marks a good roster, but does not seem to act on the game",
        f"Deciles of each measure, same axes. The within-team estimate rules out anything larger than {abs(W-1.96*Wse)*100:.1f} points of win probability per season of experience.",
        f"Holding the opponent's experience and home ice constant the slopes become {signed(Bc*100)} and {signed(Wc*100)} points. Bars are 95% confidence intervals",
        str(FIG_DIR / "fig20_between_vs_within_team.png"), title_x=0.045)

print(f"\nall figures written to {FIG_DIR}")