"""
2. Wrangle_Data.py - build every derived table for the career-tenure post.

Reads the five raw tables written by "1. Get_Data.py" and writes back to the
same prefix:

  player_careers.parquet          one row per player - the analysis spine
  star_index.parquet              skaters with 60+ GP in their first 3 seasons
  cohort_summary.parquet          Kaplan-Meier median tenure by debut year
  matched_pairs.parquet           28 star / below-average matched pairs
  team_season_experience.parquet  one row per team-season, 1917-2026
  team_games.parquet              one row per team-game, 2010-2025

Written for cell-by-cell execution in Spyder.
"""

# % imports and configuration
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import s3fs
from statsmodels.duration.survfunc import SurvfuncRight

try:
    REPO = Path(__file__).resolve().parents[2]
except NameError:
    REPO = Path("/Users/dwiwad/dev/hockey_site")
sys.path.insert(0, str(REPO))

try:
    from app.core.config import S3_BUCKET
except (ImportError, KeyError):
    S3_BUCKET = "hockey-decoded"

SLUG = "career-tenure"
PREFIX = f"static-ds-analyses/{SLUG}"

# The game-level files live under the total-depth-index prefix. Read them where
# they are - copying 116 MB into our prefix would create two paths that drift.
TDI = f"s3://{S3_BUCKET}/static-ds-analyses/total-depth-index/all-seasons"

FS = s3fs.S3FileSystem(anon=False)
SO = {"anon": False}


def read(name):
    return pd.read_parquet(f"s3://{S3_BUCKET}/{PREFIX}/{name}.parquet",
                           storage_options=SO)


def write(df, name):
    if df.empty:
        raise ValueError(f"refusing to write an empty table: {name}")
    df.to_parquet(f"s3://{S3_BUCKET}/{PREFIX}/{name}.parquet",
                  storage_options=SO, index=False)
    print(f"  wrote {name}  ({len(df):,} rows)")


# %% load the raw tables
player_seasons = read("player_seasons")
skater_seasons = read("skater_seasons")
skater_bios = read("skater_bios")
team_seasons = read("team_seasons")
team_rosters = read("team_rosters")
print(f"loaded {len(player_seasons):,} player-seasons, {len(team_rosters):,} team-rosters")

# %% player_careers - the analysis spine
POS_GROUP = {"C": "Forward", "L": "Forward", "R": "Forward",
             "D": "Defense", "G": "Goalie"}

ps = player_seasons.copy()
ps["yr"] = ps.season // 10000

# sidx: ordinal position among the seasons that were ACTUALLY PLAYED. 2004-05
# was cancelled, so no player has a row in it and it consumes no index. This is
# what makes span lockout-safe: a career spanning 2003-04 to 2005-06 is 2
# seasons, not 3. Using calendar years here would silently credit everyone
# active in that era with a phantom season.
season_order = {s: i for i, s in enumerate(sorted(ps.season.unique()))}
ps["sidx"] = ps.season.map(season_order)
print(f"{len(season_order)} seasons played "
      f"({'20042005 absent' if 20042005 not in season_order else 'LOCKOUT PRESENT - check'})")

g = ps.groupby("playerId")
car = pd.DataFrame({
    "first_year": g.yr.min(), "last_year": g.yr.max(),
    "first_idx": g.sidx.min(), "last_idx": g.sidx.max(),
    "n_seasons": g.season.nunique(), "total_gp": g.games_played.sum(),
    "name": g.name.last(),
}).reset_index()

car["span"] = car.last_idx - car.first_idx + 1        # PRIMARY TENURE MEASURE
car["censored"] = car.last_year == ps.yr.max()        # still active -> lower bound
car["decade"] = (car.first_year // 10) * 10

# modal position, ties broken arbitrarily
cnt = ps.groupby(["playerId", "position"]).size().rename("n").reset_index()
modal = cnt.sort_values("n").drop_duplicates("playerId", keep="last")
car = car.merge(modal[["playerId", "position"]], on="playerId")
car["pos_group"] = car.position.map(POS_GROUP)

assert (car.span >= car.n_seasons).all(), "span must be >= seasons actually played"
write(car, "player_careers")

# %% star_index - early-career scoring, normalised by era and position
sk = skater_seasons.copy()
sk["yr"] = sk.season // 10000

# League points-per-game for each position in each season. Normalising per
# season removes scoring inflation; per position stops defencemen being buried
# (unadjusted Bobby Orr ranks 262nd, adjusted 7th).
lg = (sk.groupby(["season", "position"])
        .apply(lambda x: x.points.sum() / x.games_played.sum(), include_groups=False)
        .rename("ppg").reset_index())

# First three seasons only. Career totals are mechanically correlated with
# career length, so ranking on them and then "discovering" that stars last
# longer would be circular.
sk = sk.sort_values(["playerId", "season"])
sk["ord"] = sk.groupby("playerId").cumcount()
f3 = sk[sk.ord < 3].merge(lg, on=["season", "position"])
f3["exp_pts"] = f3.ppg * f3.games_played

star = (f3.groupby("playerId")
          .agg(gp=("games_played", "sum"), pts=("points", "sum"),
               exp=("exp_pts", "sum"), first_yr=("yr", "min"),
               pos=("position", "first"), name=("name", "last"))
          .reset_index())

star = star[star.gp >= 60].copy()          # the sample definition
star["rel"] = star.pts / star.exp          # STAR INDEX: 1.0 = league average
star["tier"] = pd.cut(star.rel, [-1, 1.2, 1.5, 2.0, 99],
                      labels=["Regular", "Solid", "Star", "Generational"])

star = (star.merge(skater_bios[["playerId", "hof"]], on="playerId", how="left")
             .merge(car[["playerId", "span", "censored", "first_year"]], on="playerId"))
star["hof"] = star.hof.fillna(False)

write(star, "star_index")
print(star.nlargest(8, "rel")[["name", "first_yr", "pos", "rel", "span"]]
          .to_string(index=False, float_format=lambda x: f"{x:.2f}"))

# %% cohort_summary - Kaplan-Meier median tenure by debut year
rows = []
for yr, grp in car.groupby("first_year"):
    if len(grp) < 25:                        # too few to estimate a median
        continue
    sf = SurvfuncRight(grp.span.values, (~grp.censored).astype(int).values)
    try:
        med = sf.quantile(.5)
        lo, hi = sf.quantile_ci(.5)
    except Exception:                        # curve never reaches 50%
        med, lo, hi = np.nan, np.nan, np.nan
    rows.append(dict(year=yr, km_median=med, lo=lo, hi=hi, n=len(grp),
                     naive_completed=grp.loc[~grp.censored, "span"].mean(),
                     pct_censored=grp.censored.mean()))
coh = pd.DataFrame(rows).dropna(subset=["km_median"])
write(coh, "cohort_summary")


# %% matched_pairs - 28 stars vs comparable below-average scorers
def match_below_average(d, n=28, cutoff=1.0):
    """Pair each top-n scorer with a below-average player: exact position,
    nearest debut year, nearest first-three-season games as a tie-break.
    Greedy, without replacement, best star picking first - deterministic.

    Matching on debut year is what makes the tenure comparison honest: both
    members of a pair have had the same number of seasons in which to build a
    career, so censoring is held constant rather than modelled away.
    """
    stars = d.nlargest(n, "rel").sort_values("rel", ascending=False)
    pool = d[d.rel < cutoff]
    used, picked = set(), []
    for _, s in stars.iterrows():
        c = pool[(pool.pos == s.pos) & (~pool.playerId.isin(used))].copy()
        if c.empty:
            raise ValueError(f"no below-average {s.pos} left for {s['name']}")
        c["_dy"] = (c.first_yr - s.first_yr).abs()
        c["_dg"] = (c.gp - s.gp).abs()
        pick = c.sort_values(["_dy", "_dg"]).iloc[0]
        used.add(pick.playerId)
        picked.append(pick)
    return stars.reset_index(drop=True), pd.DataFrame(picked).reset_index(drop=True)


top, low = match_below_average(star)
pairs = pd.DataFrame({
    "star": top.name, "star_year": top.first_yr, "pos": top.pos,
    "star_rel": top.rel, "star_span": top.span, "star_active": top.censored,
    "star_gp": top.gp,
    "match": low.name, "match_year": low.first_yr, "match_rel": low.rel,
    "match_span": low.span, "match_active": low.censored, "match_gp": low.gp,
})
write(pairs, "matched_pairs")
print(f"  exact debut-year matches: {(pairs.star_year == pairs.match_year).sum()}/28")
print(f"  median career  stars {pairs.star_span.median():.1f}  "
      f"matched {pairs.match_span.median():.1f}")

# %% team_season_experience - one row per team-season, 1917-2026
tr = team_rosters.copy()
tr["yr"] = tr.season // 10000
ts = team_seasons.copy()
ts["yr"] = ts.season // 10000

# Experience is PRIOR SEASONS, not career length: career span isn't knowable at
# the time and is mechanically correlated with being good, which is the very
# confound this analysis exists to separate out.
tr["exp"] = tr.yr - tr.groupby("playerId").yr.transform("min")
assert tr.exp.min() >= 0
tr = tr[tr.gp > 0]


def team_metrics(grp):
    """Games-weighted, because a team is the men who dressed - not the mean of
    the forty who passed through it. Unweighted means are badly distorted in
    the small-roster eras."""
    w, e = grp.gp.to_numpy(float), grp.exp.to_numpy(float)
    mu = np.average(e, weights=w)
    return pd.Series({
        "exp": mu,
        "exp_sd": np.sqrt(np.average((e - mu) ** 2, weights=w)),
        "rookie_share": w[e == 0].sum() / w.sum(),
        "vet_share": w[e >= 10].sum() / w.sum(),
        "n_players": len(grp), "player_games": w.sum()})


tm = (tr.groupby(["season", "teamId"])
        .apply(team_metrics, include_groups=False).reset_index())

d = ts.merge(tm, on=["season", "teamId"], how="inner")
d = d[d.gp >= 20]              # drops the 6-game 1917-18 Wanderers and similar

# Every comparison is within a season: a six-team league and a thirty-two-team
# league produce completely different spreads of both experience and points.
for c in ["exp", "point_pct", "rookie_share", "vet_share", "exp_sd"]:
    d[c + "_dev"] = d[c] - d.groupby("season")[c].transform("mean")

# New franchises are young and bad at once, for reasons unrelated to experience
d["franchise_age"] = d.yr - d.groupby("teamId").yr.transform("min")

write(d, "team_season_experience")
print(f"  r(experience, points%) within season = "
      f"{d.exp_dev.corr(d.point_pct_dev):+.3f}")

# %% team_games - one row per team-game, 2010-2025   (~2 min, 116 MB of CSV)
ros = pd.read_csv(f"{TDI}/all_rosters_20102025.csv", storage_options=SO,
                  usecols=["teamId", "playerId", "positionCode", "game_id"])
meta = pd.read_csv(f"{TDI}/all_games_meta_20102025.csv", storage_options=SO,
                   low_memory=False,
                   usecols=["id", "season", "gameType", "awayTeam.id", "homeTeam.id",
                            "awayTeam.score", "homeTeam.score"])

games = meta[meta.gameType == 2].copy()          # regular season only
games["yr"] = games.season.astype(str).str[:4].astype(int)
ros = ros.merge(games[["id", "yr", "season"]], left_on="game_id", right_on="id")

# Debut = the FIRST of either source. A player can dress without taking a shift
# (a backup goalie), which leaves him out of the season summary entirely. Using
# the summary alone gave 1,540 missing debuts and 259 negative-experience rows.
debut = pd.concat([ps.groupby("playerId").yr.min(),
                   ros.groupby("playerId").yr.min()], axis=1).min(axis=1).rename("debut")
ros = ros.merge(debut, left_on="playerId", right_index=True)
ros["exp"] = ros.yr - ros.debut
assert ros.exp.min() >= 0 and ros.exp.notna().all()

tg = (ros.groupby(["game_id", "teamId", "season"])
        .agg(exp=("exp", "mean"), rookies=("exp", lambda s: (s == 0).sum()),
             dressed=("exp", "size")).reset_index())

gm = games.rename(columns={"id": "game_id", "homeTeam.id": "home",
                           "awayTeam.id": "away", "homeTeam.score": "hs",
                           "awayTeam.score": "as_"})
gm = gm[["game_id", "home", "away", "hs", "as_"]].dropna(subset=["hs", "as_"])

# Long form: each game contributes two rows, one per team
long = []
for side, opp, is_home in (("home", "away", 1), ("away", "home", 0)):
    t = gm.rename(columns={side: "teamId", opp: "oppId"})[
        ["game_id", "teamId", "oppId", "hs", "as_"]].copy()
    t["won"] = (t.hs > t.as_).astype(int) if is_home else (t.as_ > t.hs).astype(int)
    t["home"] = is_home
    long.append(t)

L = (pd.concat(long)
     .merge(tg, on=["game_id", "teamId"])
     .merge(tg[["game_id", "teamId", "exp"]]
            .rename(columns={"teamId": "oppId", "exp": "opp_exp"}),
            on=["game_id", "oppId"]))

L["gap"] = L.exp - L.opp_exp                                   # vs opponent tonight
L["ts_mean"] = L.groupby(["teamId", "season"]).exp.transform("mean")
L["within"] = L.exp - L.ts_mean                                # vs own season norm
L["between"] = L.ts_mean - L.groupby("season").exp.transform("mean")

write(L, "team_games")


# %% verify
for name, n in [("player_careers", 8731), ("star_index", 4229),
                ("matched_pairs", 28), ("team_season_experience", 1755),
                ("team_games", 35680)]:
    got = len(read(name))
    print(f"{name:26} {got:>7,}  {'ok' if got == n else f'EXPECTED {n:,}'}")