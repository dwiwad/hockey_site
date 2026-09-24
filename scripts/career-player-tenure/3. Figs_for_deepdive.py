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
# Descriptive versions, for figures that label the era lines in place rather
# than explaining them in the subtitle.
ERA_MARKS = [(1942, "Original Six begins"), (1967, "Expansion doubles the league"),
             (1991, "Expansion wave to 30 teams"), (2017, "Vegas joins")]


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
# ps2.exp is PRIOR seasons (a rookie is 0), so cut on inclusive tenure instead -
# binning exp directly put every band one season off, and made the top band
# "11th season or later" while the legend claimed "10+".
ps2["ten"] = ps2.exp + 1
ps2["bucket"] = pd.cut(ps2.ten, [0, 1, 4, 9, 99],
                       labels=["Rookie", "2nd-4th season", "5th-9th season",
                               "10th season or later"])
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
for yr, lbl in ERA_MARKS:
    ax.axvline(yr, color="white", lw=1.1, ls=":", alpha=.75)
    ax.text(yr + 0.9, .035, lbl, fontsize=9.5, color="white", rotation=90)
h, l = ax.get_legend_handles_labels()
hd_legend(ax, h[::-1], l[::-1], loc="upper left", bbox_to_anchor=(1.01, 1))
finish(fig, ax, "The NHL has never leaned less on rookies, or more on veterans",
       f"Rookies were 23% of the league across the 1940s and 1950s and {mix.loc[2025, 'Rookie']*100:.0f}% in 2025-26, while the share in a tenth season or later reached an all-time high of {mix.loc[2025, '10th season or later']*100:.0f}%.",
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
ax.set_ylim(0, ax.get_ylim()[1])
for yr, lbl in ERA_MARKS:
    ax.axvline(yr, color=GRAY, lw=1, ls=":", alpha=.7)
    ax.text(yr + 0.9, 0.15, lbl, fontsize=9.5, color=GRAY, rotation=90,
            va="bottom")
hd_legend(ax, title="Position")
finish(fig, ax, "Average NHL experience fluctuates with the eras of the league",
       "Mean seasons of experience among players active in each season, by position.",
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

#ERAS = [(1917, 1941, "1917-1941"), (1942, 1966, "Original Six"),
#        (1967, 1978, "1967-1978"), (1979, 2004, "1979-2004"),
#        (2005, 2026, "Salary cap")]


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

# %% FIG 21 - the senior share of the league, over time
# Fig 1 stacks four experience bands; this pulls out the two ends and puts them
# on a readable scale. Tenure is counted inclusively here - a rookie is in his
# 1st season - so it is ps2.exp (prior seasons) + 1.
ps2["ten"] = ps2.exp + 1
mixyr = ps2.groupby("year").apply(
    lambda g: pd.Series({"vet10": g.ten.ge(10).mean(),
                         "rookie": g.ten.eq(1).mean()}),
    include_groups=False)

# Before this the league itself is new - it had existed under a decade, so a
# high rookie share is mechanical rather than a fact about roster building.
FILL = 1927

fig, ax = plt.subplots(figsize=(12, 7))

for col, colour, lbl in [("vet10", BLUE_DARK, "In their 10th season or later"),
                         ("rookie", ORANGE, "Rookies")]:
    # faint annual values behind a LOWESS smooth, the same idiom as fig 2
    ax.plot(mixyr.index, mixyr[col], color=colour, lw=1, alpha=.25, zorder=2)
    sm = lowess(mixyr[col].values, mixyr.index.values, frac=.18,
                return_sorted=True)
    ax.plot(sm[:, 0], sm[:, 1], color=colour, lw=3.2, label=lbl, zorder=3)

for yr, lbl in ERAS:
    ax.axvline(yr, color=GRAY, lw=1, ls=":", alpha=.7, zorder=1)

peak_yr = mixyr.vet10.idxmax()
ax.annotate(f"{peak_yr}-{str(peak_yr + 1)[-2:]}:  {mixyr.vet10.max()*100:.0f}%",
            (peak_yr, mixyr.vet10.max()),
            (peak_yr - 21, mixyr.vet10.max() + .045), fontsize=12,
            color=BLUE_DARK, ha="left",
            arrowprops=dict(arrowstyle="-", lw=1, color=BLUE_DARK))

ax.set_xlim(mixyr.index.min(), mixyr.index.max())
ax.set_ylim(0, .5)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v*100)}%"))
ax.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Share of players in the league", fontsize=FS_AXIS_LABEL)
hd_legend(ax, loc="upper right", bbox_to_anchor=(0.99, 0.99))
finish(fig, ax, "The NHL has never been as senior as it is now",
       f"Share of players in their 10th season or later, against the rookie share. Veterans are at an all-time high of {mixyr.vet10.max()*100:.0f}% and rookies near an all-time low.",
       "Data: NHL Stats API. Faint lines are annual values, bold lines LOWESS smooths. Dotted lines mark league eras",
       "fig21_senior_share_by_season.png")

for lo, hi, lab in [(1930, 1939, "1930s"), (1950, 1959, "1950s"),
                    (1970, 1979, "1970s"), (2020, 2025, "2020s")]:
    w = mixyr.loc[lo:hi]
    print(f"  {lab}  10+ {w.vet10.mean()*100:4.1f}%   rookie {w.rookie.mean()*100:4.1f}%")
    
# %% load and prepare for figs 22-25
sk = read("skater_seasons")
bio = read("skater_bios")

ag = sk.merge(bio[["playerId", "birth_date"]], on="playerId")
ag["yr"] = ag.season // 10000
ag["birth"] = pd.to_datetime(ag.birth_date, errors="coerce")
ag["byr"] = ag.birth.dt.year
# Age as of 1 October of the season year - the same nominal-season-start
# convention codebook.py uses for debut_age.
ag["age"] = ((pd.to_datetime(ag.yr.astype(str) + "-10-01") - ag.birth)
             .dt.days / 365.25).round().astype("Int64")

# 20-game floor: points-per-game on a five-game call-up is noise, and those
# seasons would otherwise dominate the tails of every tier.
ag = ag[ag.age.between(18, 42) & ag.games_played.ge(20)].copy()
ag["ppg"] = ag.points / ag.games_played
ag = (ag.merge(star[["playerId", "tier"]], on="playerId")
        .sort_values(["playerId", "yr"]))

# delta pairs: same player, consecutive seasons only
_g = ag.groupby("playerId")
ag["d_ppg"] = ag.ppg - _g.ppg.shift(1)
ag["d_age"] = ag.age - _g.age.shift(1)
delta = ag[ag.d_age.eq(1)].copy()

# each tier's own reference level, so tiers with very different scoring rates
# are comparable on PROPORTIONAL decline
base = ag[ag.age.between(24, 26)].groupby("tier", observed=True).ppg.mean()

AGE_BANDS = [21, 24, 27, 30, 33, 42]
BAND_LBL = ["21-24", "24-27", "27-30", "30-33", "33+"]
print(f"{len(ag):,} tiered skater-seasons, {ag.playerId.nunique():,} players, "
      f"age non-null {ag.age.notna().mean()*100:.0f}%")


# %% FIG 22 - scoring rate by age and tier
curve = ag.groupby(["age", "tier"], observed=True).agg(
    ppg=("ppg", "mean"), n=("ppg", "size")).reset_index()

fig, ax = plt.subplots(figsize=(12, 7))
for t in TIERS:
    c = curve[curve.tier == t].sort_values("age")
    thin = c[c.n < 100]          # past here the line is a handful of survivors
    thick = c[c.n >= 100]
    ax.plot(c.age, c.ppg, color=TCOL[t], lw=1.2, alpha=.35, zorder=2)
    ax.plot(thick.age, thick.ppg, color=TCOL[t], lw=3.2, zorder=3,
            label=f"{t}  (n={c.n.sum():,})")
ax.set_xlabel("Age at the start of the season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Points per game", fontsize=FS_AXIS_LABEL)
ax.set_xlim(18, 41)
ax.set_ylim(0, 1.35)
hd_legend(ax, title="First-3-season scoring tier", loc="upper right")
finish(fig, ax, "Generational scorers peak about three times higher",
       f"Mean points per game by age. Lines thin where fewer than 100 player-seasons remain - past roughly 33 these are survivors, not a fair sample.",
       "Data: NHL Stats API. Skater-seasons of 20+ games. Ages 18-23 overlap the window the tiers are defined on",
       "fig22_scoring_by_age_and_tier.png")


# %% FIG 23 - the delta method: proportional decline by age
band = pd.cut(delta.age, AGE_BANDS, labels=BAND_LBL)
dl = (delta.groupby([band, "tier"], observed=True).d_ppg.mean().unstack())
dl_pct = (dl / base) * 100
dn = delta.groupby([band, "tier"], observed=True).size().unstack()

fig, ax = plt.subplots(figsize=(12, 7))
ax.axhline(0, color=GRAY, lw=1.2, zorder=1)
x = np.arange(len(BAND_LBL))
for t in TIERS:
    ax.plot(x, dl_pct[t].values, color=TCOL[t], lw=3.2, marker="o", ms=9,
            zorder=3, label=t)
# The 21-24 band sits inside the window the tiers are defined on, so its values
# are regression to the mean rather than an aging result.
ax.set_xticks(x)
hd_legend(ax, title="First-3-season scoring tier", loc="upper right")
ax.set_xticklabels(BAND_LBL)
ax.set_xlim(-0.4, len(BAND_LBL) - 0.6)
ax.set_xlabel("Age", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Yearly change in points per game,\nas % of that tier's own peak",
              fontsize=FS_AXIS_LABEL)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
finish(fig, ax, "The best players lose their scoring far more slowly",
       f"Year-over-year change for the same player in consecutive seasons, as a share of his tier's own age 24-26 level. After 33, the top tier loses {abs(dl_pct.loc['33+','Generational']):.0f}% a year against {abs(dl_pct.loc['33+','Regular']):.0f}% for the rest.",
       "Data: NHL Stats API. Paired seasons only, so the sample composition is held fixed",
       "fig23_decline_rate_by_tier.png")

print("\nyearly change as % of own peak:")
print(dl_pct.round(1).to_string())
print("\nn pairs:")
print(dn.to_string())
for lab, sub in [("modern 2005+", delta[delta.yr >= 2005]),
                 ("pre-2005", delta[delta.yr < 2005])]:
    b2 = pd.cut(sub.age, AGE_BANDS, labels=BAND_LBL)
    r = (sub.groupby([b2, "tier"], observed=True).d_ppg.mean().unstack() / base * 100)
    print(f"  {lab}, 33+:  " + "  ".join(f"{t} {r.loc['33+', t]:+.1f}%" for t in TIERS))


# %% FIG 24 - how long each tier stays employable
# A player born in 2003 cannot be observed at 38, so the denominator must be
# restricted to players who had the chance to reach that age inside the window.
# At 35 this excludes 847 of 4,238 players and lifts every tier by about a quarter.
byr = ag.groupby("playerId").byr.first()
tier_of = ag.groupby("playerId").tier.first()
LAST_YEAR = ag.yr.max()

rows = []
for a in range(20, 41):
    eligible = byr[(LAST_YEAR - byr) >= a].index
    den = tier_of[tier_of.index.isin(eligible)].value_counts()
    num = ag[ag.age == a].groupby("tier", observed=True).playerId.nunique()
    rows.append((num / den).rename(a))
surv = pd.DataFrame(rows).sort_index()

fig, ax = plt.subplots(figsize=(12, 7))
for t in TIERS:
    ax.plot(surv.index, surv[t], color=TCOL[t], lw=3.2, zorder=3, label=t)
ax.set_xlabel("Age", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Share of the tier still playing\n20+ games at that age",
              fontsize=FS_AXIS_LABEL)
ax.set_xlim(20, 40)
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v*100)}%"))
for a in (35,):
    ax.axvline(a, color=GRAY, ls=":", lw=1.2, zorder=1)
    ax.annotate(f"at {a}:  {surv.loc[a, 'Generational']*100:.0f}% vs {surv.loc[a, 'Regular']*100:.0f}%",
                (a, surv.loc[a, "Generational"]), (a - 9, surv.loc[a, "Generational"] + .10),
                fontsize=12, color=ORANGE, ha="left",
                arrowprops=dict(arrowstyle="-", lw=1, color=ORANGE))
hd_legend(ax, title="First-3-season scoring tier", loc="upper right")
finish(fig, ax, "Starting higher and falling slower compounds into a decade of extra career",
       f"Share of each tier still dressing for 20+ games. At 38, {surv.loc[38,'Generational']*100:.0f}% of the top tier are still playing against {surv.loc[38,'Regular']*100:.0f}% of the rest.",
       "Data: NHL Stats API. Denominator restricted to players old enough to have reached that age by the final season",
       "fig24_survival_by_age_and_tier.png")

print("\nshare still playing:")
print((surv.loc[[30, 32, 35, 38]] * 100).round(1).to_string())


# %% FIG 25 - why the naive aging curve lies
# Same players, same seasons, two estimators. The peak-indexed curve says
# ordinary players age best; the delta curve says they age worst. The first is
# survivor bias: only the Regulars who improved are still there to be measured.
pk = ag[ag.age.between(22, 25)].groupby("playerId").ppg.mean().rename("pk")
ix = ag.join(pk, on="playerId").dropna(subset=["pk"])
ix = ix[ix.pk > 0].copy()
ix["idx"] = ix.ppg / ix.pk
iband = pd.cut(ix.age, [25, 28, 31, 34, 42], labels=["25-28", "28-31", "31-34", "34+"])
naive = ix.groupby([iband, "tier"], observed=True).idx.mean().unstack()
naive_n = ix.groupby([iband, "tier"], observed=True).size().unstack()

fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 7), gridspec_kw={"wspace": 0.22})

xn = np.arange(len(naive.index))
for t in TIERS:
    axL.plot(xn, naive[t].values, color=TCOL[t], lw=3.2, marker="o", ms=9, label=t)
axL.axhline(1.0, color=GRAY, ls=":", lw=1.2)
axL.set_xticks(xn)
axL.set_xticklabels(list(naive.index))
axL.set_ylabel("Points per game as a share\nof the player's own age 22-25 level",
               fontsize=FS_AXIS_LABEL)
axL.set_xlabel("Age", fontsize=FS_XAXIS_LABEL)
axL.text(0.5, 0.98, "Peak-indexed:  Regulars appear to age best",
         transform=axL.transAxes, ha="center", va="top", fontsize=15,
         weight="bold", color=BLUE_DARK)
hd_legend(axL, loc="lower left", fontsize=12)

for t in TIERS:
    axR.plot(x, dl_pct[t].values, color=TCOL[t], lw=3.2, marker="o", ms=9, label=t)
axR.axhline(0, color=GRAY, lw=1.2)
axR.set_xticks(x)
axR.set_xticklabels(BAND_LBL)
axR.set_ylabel("Yearly change, as % of\nthat tier's own peak", fontsize=FS_AXIS_LABEL)
axR.set_xlabel("Age", fontsize=FS_XAXIS_LABEL)
axR.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
axR.text(0.5, 0.98, "Paired seasons:  Regulars age worst",
         transform=axR.transAxes, ha="center", va="top", fontsize=15,
         weight="bold", color=ORANGE)

for a in (axL, axR):
    sns.despine(ax=a)
    a.grid(False)
    a.tick_params(axis="both", labelsize=FS_TICK)

_finish(fig, axL, "The same data, two estimators, opposite conclusions",
        f"Only {naive_n.loc['34+','Regular']:,.0f} of {naive_n.loc['25-28','Regular']:,.0f} Regulars are still observed past 34, and they are the ones who improved. Pairing consecutive seasons holds the sample fixed and reverses the ranking.",
        "Data: NHL Stats API. Left panel is the standard aging curve; right panel is the delta method",
        str(FIG_DIR / "fig25_aging_curve_estimators.png"), title_x=0.045)

# %% prep for figs 26-27  (yearly cadence, season 4+)
ag_y = read("skater_seasons").merge(
    read("skater_bios")[["playerId", "birth_date"]], on="playerId")
ag_y["yr"] = ag_y.season // 10000
ag_y["birth"] = pd.to_datetime(ag_y.birth_date, errors="coerce")
ag_y["age"] = ((pd.to_datetime(ag_y.yr.astype(str) + "-10-01") - ag_y.birth)
               .dt.days / 365.25).round()
ag_y = ag_y[ag_y.age.between(18, 40) & ag_y.games_played.ge(20)].copy()
ag_y["age"] = ag_y.age.astype(int)
ag_y["ppg"] = ag_y.points / ag_y.games_played
ag_y = (ag_y.merge(star[["playerId", "tier"]], on="playerId")
            .sort_values(["playerId", "yr"]))
ag_y["career_season"] = ag_y.groupby("playerId").cumcount() + 1

# Tiers are assigned on seasons 1-3, so measuring aging inside that window is
# circular. Figs 26-27 start at season 4; figs 22-25 above do not, which is why
# they disagree about the early twenties.
ag_y = ag_y[ag_y.career_season >= 4].copy()
_gy = ag_y.groupby("playerId")
ag_y["d_ppg"] = ag_y.ppg - _gy.ppg.shift(1)
ag_y["d_age"] = ag_y.age - _gy.age.shift(1)

AGE_MIN, AGE_MAX, MIN_N = 23, 38, 25
AGES = range(AGE_MIN, AGE_MAX + 1)
base_y = ag_y[ag_y.age.between(24, 26)].groupby("tier", observed=True).ppg.mean()
print(f"{len(ag_y):,} season-4+ seasons\n{base_y.round(3).to_string()}")


# %% helper - pooled mean and CI by age, for figs 26-27
def age_band(df, col, ages, window=1, min_n=20):
    """Mean of `col` by age and tier, pooling a +/-1 year window.

    Pooling is what lets the top tier reach 38: Generational has only ~20
    players at any single age past 34, but ~55 across a three-year window.
    The CI is computed on the pooled sample, so it widens honestly where the
    tier thins rather than the line simply stopping.
    """
    rows = []
    for a in ages:
        w = df[df.age.between(a - window, a + window)]
        for t in TIERS:
            v = w.loc[w.tier == t, col].dropna()
            if len(v) < min_n:
                continue
            m, se = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
            rows.append({"age": a, "tier": t, "m": m,
                         "lo": m - 1.96 * se, "hi": m + 1.96 * se, "n": len(v)})
    return pd.DataFrame(rows)


# Start at 24: reaching a fourth season younger than that takes an unusually
# early debut, so the left edge would be a selected sample, not a cohort.
AGE_MIN, AGE_MAX = 24, 38
AGES = range(AGE_MIN, AGE_MAX + 1)


# %% FIG 26 - scoring rate by age, with confidence bands
lv = age_band(ag_y, "ppg", AGES)

fig, ax = plt.subplots(figsize=(12, 7))
for t in TIERS:
    s = lv[lv.tier == t].sort_values("age")
    ax.fill_between(s.age, s.lo, s.hi, color=TCOL[t], alpha=.20, lw=0, zorder=2)
    ax.plot(s.age, s.m, color=TCOL[t], lw=3.2, zorder=3,
            label=f"{t}  (n={int(ag_y[ag_y.tier == t].shape[0]):,})")
ax.set_xlabel("Age at the start of the season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Points per game", fontsize=FS_AXIS_LABEL)
ax.set_xlim(AGE_MIN, AGE_MAX)
ax.set_ylim(0, 1.35)
hd_legend(ax, title="First-3-season scoring tier", loc="upper right")

r26 = lv[(lv.age == 26)].set_index("tier").m
r35 = lv[(lv.age == 35)].set_index("tier").m
finish(fig, ax, "The gap the great ones arrive with never closes",
       f"Points per game by age, fourth NHL season onward. The top tier outscores the rest by {r26['Generational']/r26['Regular']:.1f}x at 26 and still {r35['Generational']/r35['Regular']:.1f}x at 35.",
       "Data: NHL Stats API. Shaded bands are 95% intervals on a three-year pooled mean; they widen where a tier thins out",
       "fig26_scoring_by_age_yearly.png")


# %% FIG 27 - yearly change as a share of each tier's own peak, with bands
dly = ag_y[ag_y.d_age.eq(1)]
dc = age_band(dly, "d_ppg", AGES)
# dividing by a per-tier constant scales the interval with the estimate
for c in ("m", "lo", "hi"):
    dc[c] = dc[c] / dc.tier.map(base_y) * 100

fig, ax = plt.subplots(figsize=(12, 7))
ax.axhline(0, color=GRAY, lw=1.4, zorder=1)
for t in TIERS:
    s = dc[dc.tier == t].sort_values("age")
    ax.fill_between(s.age, s.lo, s.hi, color=TCOL[t], alpha=.20, lw=0, zorder=2)
    ax.plot(s.age, s.m, color=TCOL[t], lw=3.2, zorder=3, label=t)
ax.set_xlabel("Age at the start of the season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Change in points per game since last season,\n"
              "as % of that tier's own peak level", fontsize=FS_AXIS_LABEL)
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:+.0f}%"))
ax.set_xlim(AGE_MIN, AGE_MAX)
hd_legend(ax, title="First-3-season scoring tier", loc="lower left")
finish(fig, ax, "The same season of decline costs an ordinary player far more",
       "Each point compares a player to himself a year earlier, so the line is not distorted by who happened to survive. Zero means no change from last season.",
       "Data: NHL Stats API. Shaded bands are 95% intervals on a three-year pooled mean. Fourth NHL season onward",
       "fig27_decline_rate_yearly.png")

print("\nmean yearly change, ages 33+:")
print(dc[dc.age >= 33].groupby("tier", observed=True).m.mean().round(1).to_string())
print("\npooled n at 36 / 38:")
print(dc[dc.age.isin([36, 38])].pivot(index="age", columns="tier", values="n").to_string())

# %% prep for figs 28-30 - the flow accounting
flow_ps = read("player_seasons").merge(
    read("player_careers")[["playerId", "first_year", "last_year", "first_idx"]],
    on="playerId")
flow_ts = read("team_seasons")
flow_ps["yr"] = flow_ps.season // 10000
flow_ts["yr"] = flow_ts.season // 10000
_ord = {y: i for i, y in enumerate(np.sort(flow_ps.yr.unique()))}
flow_ps["sidx"] = flow_ps.yr.map(_ord)
flow_ps["ten"] = flow_ps.sidx - flow_ps.first_idx + 1
flow_ps["deb"] = flow_ps.yr == flow_ps.first_year
flow_ps["ext"] = flow_ps.yr == flow_ps.last_year

FL = flow_ps.groupby("yr").agg(players=("playerId", "nunique"),
                               debuts=("deb", "sum"), exits=("ext", "sum"))
FL["teams"] = flow_ts.groupby("yr").teamId.nunique()
FL = FL.dropna()
FL["deb_pt"] = FL.debuts / FL.teams
FL["exit_pt"] = FL.exits / FL.teams
LASTY = int(flow_ps.yr.max())

# Year-over-year retention. The successor season is looked up in the data, not
# computed as yr+1 - 2004-05 was cancelled, and treating it as a missing season
# scores every 2003-04 player as having left the league.
_act = {y: set(g.playerId) for y, g in flow_ps.groupby("yr")}
_years = sorted(_act)
_nxt = {y: _years[i + 1] for i, y in enumerate(_years[:-1])}
ret = flow_ps[flow_ps.yr.isin(_nxt)].copy()
ret["ret"] = [pid in _act[_nxt[y]] for pid, y in zip(ret.playerId, ret.yr)]
ret["grp"] = pd.cut(ret.ten, [0, 1, 4, 9, 99],
                    labels=["Rookie", "2nd-4th season", "5th-9th season",
                            "10th season or later"])
RET = ret.groupby(["yr", "grp"], observed=True).ret.mean().unstack()
GCOL = {"Rookie": ORANGE, "2nd-4th season": "#F0A07C",
        "5th-9th season": BLUE_PALE, "10th season or later": BLUE_DARK}
print(f"debuts/team 1970s {FL.loc[1970:1979,'deb_pt'].mean():.2f} -> "
      f"2020s {FL.loc[2020:2025,'deb_pt'].mean():.2f}")


# %% FIG 28 - inflow: how many new players get in
fig, ax = plt.subplots(figsize=(12, 7))
ax.plot(FL.index, FL.deb_pt, color=BLUE_DARK, lw=1.1, alpha=.30, zorder=2)
sm_ = lowess(FL.deb_pt.values, FL.index.values, frac=.20, return_sorted=True)
ax.plot(sm_[:, 0], sm_[:, 1], color=BLUE_DARK, lw=3.2, zorder=3)
for yr, lbl in ERA_MARKS:
    ax.axvline(yr, color=GRAY, lw=1, ls=":", alpha=.7, zorder=1)
    ax.text(yr + 0.9, 0.25, lbl, fontsize=9.5, color=GRAY, rotation=90, va="bottom")
ax.annotate(f"{FL.loc[LASTY, 'deb_pt']:.1f}",
            (LASTY, FL.loc[LASTY, "deb_pt"]), (LASTY - 13, 2.2),
            fontsize=12, color=BLUE_DARK, ha="left",
            arrowprops=dict(arrowstyle="-", lw=1, color=BLUE_DARK))
ax.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("New NHL debuts per team", fontsize=FS_AXIS_LABEL)
ax.set_xlim(1918, LASTY)
ax.set_ylim(0, 9)
finish(fig, ax, "Teams hand out a third fewer NHL debuts than they used to",
       f"New players entering the league, per team, per season. Down from {FL.loc[1970:1979,'deb_pt'].mean():.1f} across the 1970s to {FL.loc[2020:2025,'deb_pt'].mean():.1f} in the 2020s.",
       "Data: NHL Stats API. Faint line is single seasons, bold a LOWESS smooth",
       "fig28_debuts_per_team.png")


# %% FIG 29 - inflow against outflow
# Exits cannot be counted in the final season: everyone still active has their
# last observed season there, so it would read as a mass retirement.
F = FL.loc[:LASTY - 1]
fig, ax = plt.subplots(figsize=(12, 7))
for col, colour, lbl in [("deb_pt", BLUE_DARK, "In: players making their NHL debut"),
                         ("exit_pt", ORANGE, "Out: players in their final season")]:
    ax.plot(F.index, F[col], color=colour, lw=1.1, alpha=.28, zorder=2)
    s_ = lowess(F[col].values, F.index.values, frac=.20, return_sorted=True)
    ax.plot(s_[:, 0], s_[:, 1], color=colour, lw=3.2, zorder=3, label=lbl)
ax.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Players per team", fontsize=FS_AXIS_LABEL)
ax.set_xlim(1918, LASTY - 1)
ax.set_ylim(0, 9)
hd_legend(ax, loc="upper left")
finish(fig, ax, "The door in has narrowed. The door out has not",
       f"Arrivals and departures per team. Debuts fall steadily after the 1970s while exits hold roughly flat, and the gap is where the veteran share comes from.",
       "Data: NHL Stats API. The final season is omitted: active players cannot yet be counted as having left",
       "fig29_inflow_vs_outflow.png")


# %% FIG 30 - who stopped leaving
fig, ax = plt.subplots(figsize=(12, 7))
for g in ["Rookie", "2nd-4th season", "5th-9th season", "10th season or later"]:
    ax.plot(RET.index, RET[g], color=GCOL[g], lw=1.0, alpha=.22, zorder=2)
    s_ = lowess(RET[g].dropna().values, RET[g].dropna().index.values,
                frac=.25, return_sorted=True)
    ax.plot(s_[:, 0], s_[:, 1], color=GCOL[g], lw=3.2, zorder=3, label=g)
ax.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Share returning the following season", fontsize=FS_AXIS_LABEL)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v*100)}%"))
ax.set_xlim(1930, LASTY - 1)
ax.set_ylim(0.4, 1.0)
hd_legend(ax, title="Tenure at the time", loc="lower right")
v70 = RET.loc[1970:1979, "10th season or later"].mean()
v20 = RET.loc[2020:LASTY - 1, "10th season or later"].mean()
finish(fig, ax, "It is the veterans who stopped leaving, not the rookies who started staying",
       f"Share of players who appear again the next season. Ten-year veterans returned {v70*100:.0f}% of the time in the 1970s and {v20*100:.0f}% in the 2020s, while rookie retention barely moved.",
       "Data: NHL Stats API. The 2004-05 lockout is bridged rather than counted as a season away",
       "fig30_retention_by_tenure.png")

# %% FIG 31 - entry and exit as a share of the league
# Share of players, not per team: roster-size rules changed over the century,
# so a per-team count partly measures the rulebook. This doesn't.
FS = FL.copy()
FS["in_pct"] = FS.debuts / FS.players
FS["out_pct"] = FS.exits / FS.players
FS = FS.loc[:LASTY - 1]        # exits are uncountable in the boundary season

fig, ax = plt.subplots(figsize=(12, 7))
ax.fill_between(FS.index, FS.in_pct, FS.out_pct, where=FS.in_pct >= FS.out_pct,
                color=BLUE_PALE, alpha=.12, lw=0, zorder=1)
for col, colour, lbl in [("in_pct", ORANGE, "In their first NHL season"),
                         ("out_pct", BLUE_DARK, "In their last NHL season")]:
    ax.plot(FS.index, FS[col], color=colour, lw=1.0, alpha=.25, zorder=2)
    s_ = lowess(FS[col].values, FS.index.values, frac=.20, return_sorted=True)
    ax.plot(s_[:, 0], s_[:, 1], color=colour, lw=3.2, zorder=3, label=lbl)

for yr, lbl in ERA_MARKS:
    ax.axvline(yr, color=GRAY, lw=1, ls=":", alpha=.7, zorder=1)
    ax.text(yr + 0.9, 0.012, lbl, fontsize=9.5, color=GRAY, rotation=90, va="bottom")

ax.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Share of all players in the league", fontsize=FS_AXIS_LABEL)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v*100)}%"))
ax.set_xlim(1930, LASTY - 1)
ax.set_ylim(0, 0.35)
hd_legend(ax, loc="upper right")

i70, i20 = FS.loc[1970:1979, "in_pct"].mean(), FS.loc[2020:, "in_pct"].mean()
o70, o20 = FS.loc[1970:1979, "out_pct"].mean(), FS.loc[2020:, "out_pct"].mean()
finish(fig, ax, "The way into the NHL narrowed. The way out barely moved",
       f"First-season players fell from {i70*100:.0f}% of the league in the 1970s to {i20*100:.0f}% in the 2020s, while last-season players went only {o70*100:.0f}% to {o20*100:.0f}%.",
       "Data: NHL Stats API. The final season is omitted: players still active cannot yet be counted as leaving",
       "fig31_entry_exit_share.png")

print(f"\nfirst-season share, 5 lowest since 1930:")
print((FL.loc[1930:, "debuts"] / FL.loc[1930:, "players"]).nsmallest(5).mul(100).round(1).to_string())

# %% FIG 32 - flows in and out, against the size of the league
# Arrivals are drawn as a band inside the total; departures as a line over it.
# They cannot both be bands - a one-season career is an arrival and a departure
# in the same year, so the two categories overlap and would double-count.
FC = FL.copy()
FC["in_pct"] = FC.debuts / FC.players
FC["out_pct"] = FC.exits / FC.players
FX = FC.loc[:LASTY - 1]          # exits are uncountable in the boundary season

fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 7),
                               gridspec_kw={"wspace": 0.22, "width_ratios": [1.25, 1]})

# --- left: headcount, flows against the whole
axL.fill_between(FC.index, 0, FC.debuts, color=ORANGE, alpha=.95, lw=0,
                 label="Arriving: first NHL season")
axL.fill_between(FC.index, FC.debuts, FC.players, color=BLUE_PALE, alpha=.95,
                 lw=0, label="Everyone else")
axL.plot(FX.index, FX.exits, color=BLUE_DARK, lw=2.4, zorder=4,
         label="Departing: last NHL season")
for yr, lbl in ERA_MARKS:
    axL.axvline(yr, color="white", lw=1.1, ls=":", alpha=.55, zorder=3)
    axL.text(yr + 9, 40, lbl, fontsize=9.5, color="white", rotation=90, va="bottom")
axL.set_xlim(1930, LASTY)
axL.set_ylim(0, FC.players.max() * 1.06)
axL.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
axL.set_ylabel("Players in the league", fontsize=FS_AXIS_LABEL)
hd_legend(axL, loc="upper left", fontsize=12)

# --- right: the same flows as shares
for col, colour, lbl in [("in_pct", ORANGE, "Arriving"),
                         ("out_pct", BLUE_DARK, "Departing")]:
    axR.plot(FX.index, FX[col], color=colour, lw=1.0, alpha=.22, zorder=2)
    s_ = lowess(FX[col].values, FX.index.values, frac=.20, return_sorted=True)
    axR.plot(s_[:, 0], s_[:, 1], color=colour, lw=3.2, zorder=3, label=lbl)
for yr, lbl in ERA_MARKS:
    axR.axvline(yr, color=GRAY, lw=1, ls=":", alpha=.7, zorder=1)
    axR.text(yr + 1.2, 0.012, lbl, fontsize=9, color=GRAY, rotation=90, va="bottom")
axR.set_xlim(1930, LASTY - 1)
axR.set_ylim(0, 0.35)
axR.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{int(v*100)}%"))
axR.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
axR.set_ylabel("Share of the league", fontsize=FS_AXIS_LABEL)
hd_legend(axR, loc="upper right", fontsize=12)

for a in (axL, axR):
    sns.despine(ax=a)
    a.grid(False)
    a.tick_params(axis="both", labelsize=FS_TICK)

p70, p20 = FC.loc[1970:1979, "players"].mean(), FC.loc[2020:, "players"].mean()
d70, d20 = FX.loc[1970:1979, "debuts"].mean(), FX.loc[2020:, "debuts"].mean()
i70, i20 = FX.loc[1970:1979, "in_pct"].mean(), FX.loc[2020:, "in_pct"].mean()
o70, o20 = FX.loc[1970:1979, "out_pct"].mean(), FX.loc[2020:, "out_pct"].mean()

_finish(fig, axL, "The league doubled. The traffic through it did not",
        f"The NHL has grown {p20/p70:.1f}x since the 1970s while annual debuts rose only {d20/d70:.2f}x. Arrivals fell from {i70*100:.0f}% of the league to {i20*100:.0f}%, departures from {o70*100:.0f}% to {o20*100:.0f}%.",
        "Data: NHL Stats API. The final season is omitted from the departure series: active players cannot yet be counted as leaving",
        str(FIG_DIR / "fig32_debuts_vs_league_size.png"), title_x=0.045)

print(f"league  {p70:>6.0f} -> {p20:>6.0f}  ({p20/p70:.2f}x)")
print(f"debuts  {d70:>6.0f} -> {d20:>6.0f}  ({d20/d70:.2f}x)")
print(f"exits   {FX.loc[1970:1979,'exits'].mean():>6.0f} -> {FX.loc[2020:,'exits'].mean():>6.0f}")

# %% FIG 33 - flows in and out, against the size of the league (single panel)
# Arrivals are drawn as a band inside the total; departures as a line over it.
# They cannot both be bands - a one-season career is an arrival and a departure
# in the same year, so the two categories overlap and would double-count.
FC = FL.copy()
FX = FC.loc[:LASTY - 1]          # exits are uncountable in the boundary season

fig, ax = plt.subplots(figsize=(12, 7))
ax.fill_between(FC.index, 0, FC.debuts, color=ORANGE, alpha=.95, lw=0,
                label="Arriving: first NHL season")
ax.fill_between(FC.index, FC.debuts, FC.players, color=BLUE_PALE, alpha=.95,
                lw=0, label="Everyone else")
ax.plot(FX.index, FX.exits, color=BLUE_DARK, lw=2.4, zorder=4,
        label="Departing: last NHL season")

for yr, lbl in ERA_MARKS:
    ax.axvline(yr, color="white", lw=1.1, ls=":", alpha=.55, zorder=3)
    ax.text(yr + 0.9, 40, lbl, fontsize=9.5, color="white", rotation=90, va="bottom")

ax.set_xlim(1930, LASTY)
ax.set_ylim(0, FC.players.max() * 1.06)
ax.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Players in the league", fontsize=FS_AXIS_LABEL)
hd_legend(ax, loc="upper left")

p70, p20 = FC.loc[1970:1979, "players"].mean(), FC.loc[2020:, "players"].mean()
d70, d20 = FX.loc[1970:1979, "debuts"].mean(), FX.loc[2020:, "debuts"].mean()
w70, w20 = p70 / d70, p20 / d20

finish(fig, ax, "The league doubled. The traffic through it did not",
       f"The NHL has grown {p20/p70:.1f}x since the 1970s while annual debuts rose only {d20/d70:.2f}x. With a bigger league fed by a similar intake, the average player now lasts {w20:.1f} seasons against {w70:.1f}.",
       "Data: NHL Stats API. The final season is omitted from the departure line: active players cannot yet be counted as leaving",
       "fig33_flows_vs_league_size.png")

print(f"league {p70:.0f} -> {p20:.0f} ({p20/p70:.2f}x)   debuts {d70:.0f} -> {d20:.0f} ({d20/d70:.2f}x)")
print(f"implied mean career (players/debuts): {w70:.2f} -> {w20:.2f} seasons")

# %% FIG 34 - what happened to the distribution of career length
# All three quantiles, by debut decade. Cohorts after the 2000s are dropped:
# with a third still active, the upper quantiles are not yet estimable.
QC = []
with np.errstate(divide="ignore", invalid="ignore"):
    for dec, g in car.groupby(car.first_year // 10 * 10):
        if len(g) < 80 or dec < 1930 or dec > 2000:
            continue
        sf = SurvfuncRight(g.span.values, (~g.censored).astype(int).values)
        row = {"decade": int(dec), "n": len(g)}
        for p, lab in [(.25, "p25"), (.5, "p50"), (.75, "p75")]:
            try:
                row[lab] = sf.quantile(p)
            except Exception:
                row[lab] = np.nan
        QC.append(row)
QC = pd.DataFrame(QC).set_index("decade")

fig, ax = plt.subplots(figsize=(12, 7))
ax.fill_between(QC.index, QC.p25, QC.p75, color=BLUE_PALE, alpha=.18, lw=0, zorder=1)
for col, colour, lbl, lw in [("p75", BLUE_PALE, "75th percentile", 2.4),
                             ("p50", BLUE_DARK, "Median", 3.4),
                             ("p25", GRAY, "25th percentile", 2.4)]:
    ax.plot(QC.index, QC[col], color=colour, lw=lw, marker="o", ms=8,
            zorder=3, label=lbl)
ax.axvspan(1965, 1975, color=ORANGE, alpha=.10, lw=0, zorder=0)
ax.text(1970, 15.3, "expansion floods the\nleague with short careers",
        fontsize=10.5, color=ORANGE, ha="center", va="top", style="italic")
ax.set_xlabel("Debut decade", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Career length (seasons)", fontsize=FS_AXIS_LABEL)
ax.set_xticks(QC.index)
ax.set_xticklabels([f"{d}s" for d in QC.index])
ax.set_ylim(0, 16)
hd_legend(ax, loc="upper left")
finish(fig, ax, "Career length has no trend - it has an expansion cycle",
       f"Kaplan-Meier quantiles by debut cohort. The 1960s produced longer careers than any decade since, and the 1970s the shortest, because expansion filled new rosters with players who did not last.",
       "Data: NHL Stats API. Cohorts after 2000 are omitted: too many careers are still running to estimate the upper quantiles",
       "fig34_career_length_quantiles.png")
print(QC.round(1).to_string())


# %% FIG 34 - career length by cohort, full percentile fan
QC = []
with np.errstate(divide="ignore", invalid="ignore"):
    for dec, g in car.groupby(car.first_year // 10 * 10):
        if len(g) < 150 or dec < 1930 or dec > 2000:
            continue
        sf = SurvfuncRight(g.span.values, (~g.censored).astype(int).values)
        row = {"decade": int(dec)}
        for p in [.10, .25, .50, .75, .90]:
            try:
                row[f"p{int(p*100)}"] = sf.quantile(p)
            except Exception:
                row[f"p{int(p*100)}"] = np.nan
        # mean career = area under the survival curve
        row["mean"] = np.sum([sf.surv_prob[sf.surv_times <= t][-1]
                              if (sf.surv_times <= t).any() else 1.0
                              for t in range(26)])
        QC.append(row)
QC = pd.DataFrame(QC).set_index("decade")

fig, ax = plt.subplots(figsize=(12, 7))
ax.fill_between(QC.index, QC.p10, QC.p90, color=BLUE_PALE, alpha=.10, lw=0, zorder=1)
ax.fill_between(QC.index, QC.p25, QC.p75, color=BLUE_PALE, alpha=.20, lw=0, zorder=1)
for col, colour, lbl, lw, ls in [
        ("p90", BLUE_PALE, "90th percentile", 2.0, "-"),
        ("p75", BLUE_PALE, "75th", 2.0, "-"),
        ("mean", ORANGE, "Mean", 3.0, "--"),
        ("p50", BLUE_DARK, "Median", 3.4, "-"),
        ("p25", GRAY, "25th", 2.0, "-"),
        ("p10", GRAY, "10th percentile", 2.0, "-")]:
    ax.plot(QC.index, QC[col], color=colour, lw=lw, ls=ls, marker="o", ms=6,
            zorder=3, label=lbl)
ax.axvspan(1965, 1975, color=ORANGE, alpha=.08, lw=0, zorder=0)
ax.text(1970, 17.4, "expansion", fontsize=10.5, color=ORANGE, ha="center",
        va="top", style="italic")
ax.set_xlabel("Debut decade", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Career length (seasons)", fontsize=FS_AXIS_LABEL)
ax.set_xticks(QC.index)
ax.set_xticklabels([f"{d}s" for d in QC.index])
ax.set_ylim(0, 18)
hd_legend(ax, loc="upper left", ncol=2, fontsize=12)
finish(fig, ax, "Career length goes in cycles, not in a direction",
       f"Kaplan-Meier percentiles by debut cohort. The mean sits at {QC['mean'].loc[2000]:.1f} seasons for 2000s debutants against {QC['mean'].loc[1960]:.1f} for the 1960s - no trend, just expansion cycles.",
       "Data: NHL Stats API. Cohorts after 2000 omitted: too many careers still running to estimate the upper percentiles",
       "fig35_career_length_percentiles.png")
print(QC.round(2).to_string())

# %% FIG 35 - what the distribution of career length actually looks like
# Active players are excluded: their careers aren't over, so counting them
# would pile unfinished careers into the short bins. The right panel goes
# further and takes a cohort window where every career has ended, so the
# comparison isn't contaminated by who happened to debut recently.
done = car[~car.censored].copy()
cohort = done[done.first_year.between(1980, 1999)]

fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 7), sharey=True,
                               gridspec_kw={"wspace": 0.08})
BINS = np.arange(0.5, 26.5, 1)

for ax, d, lbl in ((axL, done, "All completed careers, 1918-2025"),
                   (axR, cohort, "Debut cohorts 1980-1999")):
    ax.hist(d.span, bins=BINS, color=BLUE_PALE, alpha=.9, edgecolor="white", lw=.6)
    mn, md = d.span.mean(), d.span.median()
    ax.axvline(md, color=BLUE_DARK, lw=2.6, zorder=4)
    ax.axvline(mn, color=ORANGE, lw=2.6, ls="--", zorder=4)
    top = ax.get_ylim()[1]
    ax.text(md - 0.4, top * .92, f"median {md:.0f}", color=BLUE_DARK,
            fontsize=12, ha="right", va="top")
    ax.text(mn + 0.4, top * .82, f"mean {mn:.1f}", color=ORANGE,
            fontsize=12, ha="left", va="top")
    one = (d.span == 1).mean()
    ax.annotate(f"{one*100:.0f}% last\na single season", (1, np.histogram(d.span, BINS)[0][0]),
                (4.2, top * .70), fontsize=11, color=GRAY, ha="left",
                arrowprops=dict(arrowstyle="->", lw=1, color=GRAY))
    ax.text(0.5, 0.99, lbl, transform=ax.transAxes, ha="center", va="top",
            fontsize=14, weight="bold", color=BLUE_DARK)
    ax.set_xlabel("Career length (seasons)", fontsize=FS_XAXIS_LABEL)
    ax.set_xlim(0, 26)
    sns.despine(ax=ax)
    ax.grid(False)
    ax.tick_params(axis="both", labelsize=FS_TICK)
axL.set_ylabel("Players", fontsize=FS_AXIS_LABEL)

_finish(fig, axL, "Most NHL careers are very short, and a few are very long",
        f"Career length is heavily right-skewed, so the mean sits well above the median. Of {len(done):,} completed careers, {(done.span==1).mean()*100:.0f}% lasted one season and {(done.span>=15).mean()*100:.0f}% reached fifteen.",
        "Data: NHL Stats API. Active players excluded - their careers are unfinished, not short",
        str(FIG_DIR / "fig35_career_length_distribution.png"), title_x=0.045)

for lbl, d in [("all completed", done), ("1980-99 cohort", cohort)]:
    print(f"\n{lbl}  n={len(d):,}")
    print(f"  mean {d.span.mean():.2f}  median {d.span.median():.0f}  "
          f"skew {d.span.skew():.2f}")
    print("  percentiles: " + "  ".join(
        f"p{int(p*100)} {d.span.quantile(p):.0f}" for p in [.1,.25,.5,.75,.9,.95]))
    print(f"  1 season {(d.span==1).mean()*100:.0f}%   10+ {(d.span>=10).mean()*100:.0f}%   "
          f"15+ {(d.span>=15).mean()*100:.0f}%")

# span counts elapsed seasons; n_seasons counts seasons actually played.
# They diverge for players with a gap year - worth knowing which you're quoting.
gap = (done.span - done.n_seasons)
print(f"\nspan vs seasons played: differ for {(gap>0).mean()*100:.0f}% of players, "
      f"mean gap {gap.mean():.2f} seasons")

# %% prep for figs 36-37 - postseason outcomes
# Cup winner identified as the team with the most playoff wins that season; the
# runner-up as second-most. Verified against known winners (2023-24 Florida,
# 2022-23 Vegas, 1967-68 Montreal). Four early seasons tie at the top and are
# dropped by the drop_duplicates below: 1917, 1922, 1927, 1936.
PL = read("playoff_team_seasons")
tr_p = read("team_rosters"); ts_p = read("team_seasons")
tr_p["yr"] = tr_p.season // 10000; ts_p["yr"] = ts_p.season // 10000
tr_p["exp"] = tr_p.yr - tr_p.groupby("playerId").yr.transform("min")
tr_p = tr_p[tr_p.gp > 0]
tm_p = (tr_p.groupby(["season", "teamId"])
        .apply(lambda g: pd.Series({"exp": np.average(g.exp, weights=g.gp)}),
               include_groups=False).reset_index())
D = ts_p.merge(tm_p, on=["season", "teamId"]).query("gp >= 20").copy()

PL["rk"] = PL.groupby("yr").w.rank(ascending=False, method="min")
_w = PL[PL.rk == 1].drop_duplicates("yr")[["yr", "teamId"]].assign(result="Won the Cup")
_l = PL[PL.rk == 2].drop_duplicates("yr")[["yr", "teamId"]].assign(result="Lost the final")
D = D.merge(PL[["yr", "teamId"]].assign(playoff=1), on=["yr", "teamId"], how="left")
D["playoff"] = D.playoff.fillna(0).astype(int)
D = D.merge(pd.concat([_w, _l]), on=["yr", "teamId"], how="left")
D["result"] = D.result.where(D.result.notna(), pd.Series(
    np.where(D.playoff == 1, "Made playoffs", "Missed playoffs"), index=D.index))
# every comparison within season: league size and scoring era both move
for c in ["exp", "point_pct"]:
    D[c + "_d"] = D[c] - D.groupby("season")[c].transform("mean")
D = D[D.yr <= 2024]
ORDER = ["Won the Cup", "Lost the final", "Made playoffs", "Missed playoffs"]
RCOL = {"Won the Cup": ORANGE, "Lost the final": BLUE_PALE,
        "Made playoffs": GRAY, "Missed playoffs": "#C3C9D2"}


# %% FIG 36 - experience by postseason outcome
st = D.groupby("result").exp_d.agg(["mean", "sem", "size"]).reindex(ORDER)

fig, ax = plt.subplots(figsize=(12, 7))
y = np.arange(len(ORDER))[::-1]
ax.axvline(0, color=GRAY, lw=1.4, zorder=1)
for yi, r in zip(y, ORDER):
    m, se = st.loc[r, "mean"], st.loc[r, "sem"]
    ax.errorbar(m, yi, xerr=1.96 * se, fmt="o", ms=13, lw=0, elinewidth=2.4,
                color=RCOL[r], zorder=3)
    ax.text(m, yi + 0.20, f"{m:+.2f}", ha="center", va="bottom", fontsize=13,
            color=RCOL[r])
ax.set_yticks(y)
ax.set_yticklabels([f"{r}  (n={int(st.loc[r,'size']):,})" for r in ORDER])
ax.set_ylim(-0.6, len(ORDER) - 0.4)
ax.set_xlabel("Team experience, relative to the league that season (seasons)",
              fontsize=FS_XAXIS_LABEL)
finish(fig, ax, "Experience gets teams into the playoffs, then stops mattering",
       f"Games-weighted mean experience against the league average. The gap between playoff and non-playoff teams is {st.loc['Made playoffs','mean']-st.loc['Missed playoffs','mean']:+.2f} seasons; between Cup winners and the teams they beat, {st.loc['Won the Cup','mean']-st.loc['Lost the final','mean']:+.2f}.",
       "Data: NHL Stats API, 1917-2025. Bars are 95% confidence intervals",
       "fig36_experience_by_postseason_outcome.png", title_x=0.045)


# %% FIG 37 - the finals, winner against loser
fin = (D[D.result == "Won the Cup"].set_index("yr").exp_d.rename("win")
       .to_frame().join(D[D.result == "Lost the final"].set_index("yr").exp_d.rename("lose"),
                        how="inner"))
lim = (min(fin.min()) - 0.3, max(fin.max()) + 0.3)

fig, ax = plt.subplots(figsize=(12, 7))
ax.plot(lim, lim, color=GRAY, ls="--", lw=1.4, zorder=1)
ax.axhline(0, color=GRAY, lw=.8, alpha=.5, zorder=1)
ax.axvline(0, color=GRAY, lw=.8, alpha=.5, zorder=1)
ax.scatter(fin.lose, fin.win, s=52, color=BLUE_DARK, alpha=.6,
           edgecolors="white", lw=.6, zorder=3)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("Experience of the team that lost the final", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Experience of the\nteam that won", fontsize=FS_AXIS_LABEL)
ax.text(lim[0] + .15, lim[1] - .15, "winner more experienced", fontsize=11,
        color=GRAY, style="italic", va="top")
ax.text(lim[1] - .15, lim[0] + .15, "loser more experienced", fontsize=11,
        color=GRAY, style="italic", ha="right")
share = (fin.win > fin.lose).mean()
finish(fig, ax, "The more experienced team does not win the Stanley Cup",
       f"Each point is one final, {int(fin.index.min())} to {int(fin.index.max())}, both measured against their own season's league average. The winner is the more experienced side {share*100:.0f}% of the time - a coin flip.",
       "Data: NHL Stats API. Dashed line is equal experience. Cup winner identified as the team with the most playoff wins",
       "fig37_finals_winner_vs_loser.png")
print(f"finals n={len(fin)}  winner {fin.win.mean():+.2f}  loser {fin.lose.mean():+.2f}  "
      f"winner-more-experienced {share*100:.0f}%")

# %% FIG 38 - raw tenure by postseason outcome, modern era
# Restricted to 1991+ on purpose. There is one Cup winner per season whatever
# the league size, so finalists spread evenly across the century while playoff
# and non-playoff teams concentrate in the 32-team era. Pooled over all years
# that era mix puts "made playoffs" ABOVE "won the Cup", which is an artifact.
M = D[D.yr >= 1991]
box = [M.loc[M.result == r, "exp"].values for r in ORDER]

fig, ax = plt.subplots(figsize=(12, 7))
bp = ax.boxplot(box, vert=False, widths=.62, patch_artist=True, showfliers=False,
                medianprops=dict(color="white", lw=2.4),
                whiskerprops=dict(color=GRAY, lw=1.4),
                capprops=dict(color=GRAY, lw=1.4))
for patch, r in zip(bp["boxes"], ORDER):
    patch.set(facecolor=RCOL[r], alpha=.92, edgecolor="white", lw=1.2)

for i, r in enumerate(ORDER, start=1):
    v = M.loc[M.result == r, "exp"]
    ax.scatter(v.mean(), i, marker="D", s=70, color=BLUE_DARK, zorder=5)
    ax.text(v.max() + .15, i, f"mean {v.mean():.2f}   median {v.median():.2f}",
            va="center", fontsize=11, color=GRAY)

ax.scatter([], [], marker="D", s=70, color=BLUE_DARK, label="Mean")
ax.plot([], [], color=GRAY, lw=2.4, label="Median (white line)")
ax.set_yticks(range(1, len(ORDER) + 1))
ax.set_yticklabels([f"{r}\n(n={int((M.result == r).sum()):,})" for r in ORDER])
ax.set_xlabel("Team experience (games-weighted prior NHL seasons)",
              fontsize=FS_XAXIS_LABEL)
ax.set_xlim(3, 11)
hd_legend(ax, loc="lower right")

g_pl = M[M.result == "Made playoffs"].exp.mean() - M[M.result == "Missed playoffs"].exp.mean()
g_cup = M[M.result == "Won the Cup"].exp.mean() - M[M.result == "Lost the final"].exp.mean()
finish(fig, ax, "The experience gap is at the playoff line, not the Cup",
       f"Teams that qualified averaged {g_pl:+.2f} seasons more experience than teams that missed. Between the two teams that reached the final, the gap is {g_cup:+.2f}.",
       "Data: NHL Stats API, 1991-2025. Earlier seasons excluded: one Cup winner per season regardless of league size makes a pooled comparison an era artifact",
       "fig38_raw_tenure_by_outcome.png", title_x=0.045)

for r in ORDER:
    v = M.loc[M.result == r, "exp"]
    print(f"  {r:>18} n={len(v):>4}  mean {v.mean():.2f}  median {v.median():.2f}  "
          f"IQR {v.quantile(.25):.2f}-{v.quantile(.75):.2f}")
    
# %% FIG 39 - who is leaving: exit rate by tenure, with bands
# Complements fig 30. "Leaving" here is a player's last observed season
# (flow_ps.ext), not a missed next season, so a player who sits out a year and
# comes back is not counted as gone. That makes the latest seasons read slightly
# HIGH - their comebacks haven't happened yet - so the recent fall in veteran
# exits is, if anything, understated.
# Each point pools exits / player-seasons over a centred 5-season window, with a
# Wilson 95% band on the pooled counts. Starts at 1967: six-team rosters are too
# small for a readable rate.
EX_WIN, EX_START = 5, 1967
EX_GROUPS = [("Rookie", flow_ps.ten == 1, GRAY),
             ("4th-9th season", flow_ps.ten.between(4, 9), BLUE_PALE),
             ("10th season or later", flow_ps.ten >= 10, ORANGE)]


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / d
    return c - h, c + h


fig, ax = plt.subplots(figsize=(12, 7))
EXR = {}
for lbl, mask, colour in EX_GROUPS:
    g = (flow_ps[mask & (flow_ps.yr < LASTY)]
         .drop_duplicates(["playerId", "yr"])
         .groupby("yr").ext.agg(["sum", "size"]))
    r = g.rolling(EX_WIN, center=True, min_periods=EX_WIN).sum().dropna()
    r = r[r.index >= EX_START]
    EXR[lbl] = r["sum"] / r["size"]
    lo, hi = wilson(r["sum"], r["size"])
    ax.fill_between(r.index, lo, hi, color=colour, alpha=.15, lw=0)
    ax.plot(r.index, EXR[lbl], color=colour, lw=3, label=lbl)

vet = EXR["10th season or later"]
peak = vet.loc[1990:].idxmax()
ax.annotate(f"{vet[peak]:.0%}", (peak, vet[peak]), xytext=(0, 38),
            textcoords="offset points", ha="center", fontsize=13, color=ORANGE,
            arrowprops=dict(arrowstyle="-", color=ORANGE, lw=1))
ax.annotate(f"{vet.iloc[-1]:.0%}", (vet.index[-1], vet.iloc[-1]), xytext=(8, 0),
            textcoords="offset points", va="center", fontsize=13, color=ORANGE)
ax.set_ylim(0, None)
ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.0%}"))
ax.set_xlabel("Season", fontsize=FS_XAXIS_LABEL)
ax.set_ylabel("Share who never play another NHL season", fontsize=FS_AXIS_LABEL)
hd_legend(ax, loc="upper right")
finish(fig, ax, "Veterans are staying longer. Rookies aren't",
       f"Players in their 10th season or later left at {vet[peak]:.0%} a year around {peak}; now it is {vet.iloc[-1]:.0%}. Rookies still wash out at about {EXR['Rookie'].iloc[-1]:.0%}.",
       f"Data: NHL Stats API. {EX_WIN}-season centred rolling rate; shaded band = 95% CI. Seasons since {EX_START}",
       "fig39_exit_rate_by_tenure.png")
