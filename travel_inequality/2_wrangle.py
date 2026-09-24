"""2_wrangle.py - turn the 2026-27 schedule into itineraries, then into metrics.

Reads  data/games.parquet, data/venues.parquet
Writes data/team_games.parquet   one row per team per game (both perspectives)
       data/stops.parquet        the itinerary: every place a team sleeps
       data/legs.parquet         one row per travel leg per team
       data/trips.parquet        one row per road trip
       data/team_weeks.parquet   team x season week, for the lumpiness measure
       data/team_travel.parquet  one row per team: every metric, every rank

Written for cell-by-cell execution in Spyder (Ctrl+Enter through the # %% cells).

The itinerary model
-------------------
A team's location sequence is [home arena] + [venue of game 1, ..., game 84].
Consecutive home games give zero-distance legs. A road trip is a maximal run of
consecutive away games, and the flight home needs no special case: the next
game's venue simply IS the home arena. Neutral sites need no special case
either, because the venue is read from the schedule rather than inferred from
the home team.

One thing DOES need a special case: long gaps. Taken literally, the sequence
above has New Jersey on a single 22-day road trip from January 28 to February
18, because their western swing and their post-All-Star-break trip are both
away games with the break sitting between them. No team lives in a hotel for
ten days. So when a team is on the road and the next game is HOME_GAP_DAYS or
more away, it is sent home in between.

The threshold is not arbitrary. Away-to-away gaps in this schedule are 1, 2, 3
or 4 days 748 times, and then the distribution falls off a cliff: the only
larger gaps are 5, 7, 9, 10 and 11 days, ten of them in total, and they are all
the Christmas break, the All-Star break and bye weeks. Five days is the gap in
the histogram, not a number picked to taste.

The gap rule alone still misses one case. Toronto play Detroit on December 22
and Montreal on December 26 - a four-day gap that reads as one 17-day road trip
straddling Christmas. Nobody spends Christmas in a Detroit hotel. So a team is
also sent home across any gap containing two or more consecutive dates on which
the WHOLE LEAGUE is dark. Those dates are read off the schedule rather than
hardcoded, and in 2026-27 the only runs that qualify are December 23-25 and
February 4-7 - the holiday break and the All-Star break. Single dark dates
(November 20, November 26) do not send anyone home.

Two other modelling choices worth knowing
-----------------------------------------
1. The four trans-Atlantic games are dropped and the surrounding legs bridged
   (EXCLUDE_EUROPE). Carolina, Seattle, Chicago and Ottawa each fly to Europe
   and back once - enough to decide the ranking on a once-a-decade scheduling
   quirk rather than on the season the other 28 teams actually play. Set
   EXCLUDE_EUROPE = False for the sensitivity run; both are printed at the end.
2. Time-zone crossings are differenced on each venue's STANDARD offset, not the
   DST-aware venueUTCOffset the API returns per game. Otherwise a team sitting
   at home through the November or March DST switch books a phantom crossing.
"""

# %% imports and configuration
import os
from pathlib import Path

import numpy as np
import pandas as pd

try:
    HERE = Path(__file__).resolve().parent
except NameError:                       # Spyder cell execution
    HERE = Path("/Users/dwiwad/dev/hockey_site/travel_inequality")

DATA = HERE / "data"

# Default True; the sensitivity run is `TI_EXCLUDE_EUROPE=0 python 2_wrangle.py`,
# which writes the same tables under a _with_europe suffix. See the docstring.
EXCLUDE_EUROPE = os.getenv("TI_EXCLUDE_EUROPE", "1") == "1"
HOME_GAP_DAYS = 5                       # days off that send a road team home
BUS_KM = 400.0                          # below this a team buses; NYR/NYI/NJD,
                                        # ANA/LAK, PHI/NYC, WSH/PHI all qualify
R_EARTH = 6371.0088                     # km, IUGG mean radius
KM_PER_MI = 1.609344

WRITE_S3 = False
S3_PREFIX = "static-ds-analyses/travel-inequality"

games = pd.read_parquet(DATA / "games.parquet")
venues = pd.read_parquet(DATA / "venues.parquet")
games["game_date"] = pd.to_datetime(games["game_date"])
print(f"{len(games):,} games, {len(venues)} venues")

# Dates inside the season on which no game is played anywhere, and the subset
# of those that sit in a run of MIN_DARK_RUN or more - the league's mandated
# breaks, which send every road team home.
MIN_DARK_RUN = 2
_all_days = pd.date_range(games.game_date.min(), games.game_date.max(), freq="D")
_dark = _all_days.difference(pd.DatetimeIndex(games.game_date.unique()))
_run = (~pd.Series(_dark).diff().eq(pd.Timedelta(days=1))).cumsum()
_sizes = _run.map(_run.value_counts())
LEAGUE_BREAK_DATES = set(pd.Series(_dark)[_sizes >= MIN_DARK_RUN])
print(f"  {len(_dark)} league-wide dark dates; "
      f"{len(LEAGUE_BREAK_DATES)} of them in a run of {MIN_DARK_RUN}+: "
      f"{sorted(d.date() for d in LEAGUE_BREAK_DATES)}")

# %% helpers


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km between arrays of decimal degrees."""
    p1, p2 = np.radians(np.asarray(lat1, float)), np.radians(np.asarray(lat2, float))
    dp = p2 - p1
    dl = np.radians(np.asarray(lon2, float) - np.asarray(lon1, float))
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * R_EARTH * np.arcsin(np.sqrt(a))


def gini(x):
    """Gini coefficient of a non-negative vector. 0 = perfectly even.

    Same estimator the site uses for its depth metrics: sort ascending, then
    (2*sum(i*x_i)/(n*sum(x))) - (n+1)/n with i one-indexed.
    """
    x = np.sort(np.asarray(x, dtype=float))
    if x.min() < 0:
        raise ValueError("Gini is undefined for negative values")
    n = len(x)
    total = x.sum()
    if total == 0:
        return 0.0
    i = np.arange(1, n + 1)
    return (2 * (i * x).sum()) / (n * total) - (n + 1) / n


def z(s):
    """Z-score a Series across the 32 teams. Population sd, so it is exact."""
    return (s - s.mean()) / s.std(ddof=0)


SUFFIX = "" if EXCLUDE_EUROPE else "_with_europe"


def write(df, name):
    if df.empty:
        raise ValueError(f"refusing to write an empty table: {name}")
    name += SUFFIX
    path = DATA / f"{name}.parquet"
    df.to_parquet(path, index=False)
    print(f"  wrote {path}  ({len(df):,} rows)")
    if WRITE_S3:
        from app.core.config import S3_BUCKET
        uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/{name}.parquet"
        df.to_parquet(uri, storage_options={"anon": False}, index=False)
        print(f"  mirrored {uri}")


# %% one row per team per game
# Each game contributes two rows, one per participant, so an itinerary is just
# a filter and a sort.
vx = venues.set_index("venue")
home_airport = venues.dropna(subset=["home_team"]).set_index("home_team")

tg = pd.concat([
    games.assign(team=games.home_tri, opp=games.away_tri, is_home=True),
    games.assign(team=games.away_tri, opp=games.home_tri, is_home=False),
], ignore_index=True)

for col in ["iata", "lat", "lon", "utc_std", "region"]:
    tg[col] = tg.venue.map(vx[col])
tg = tg.sort_values(["team", "game_date", "game_id"]).reset_index(drop=True)

assert len(tg) == 2 * len(games)
assert tg.iata.notna().all() and tg.lat.notna().all()

EUROPE = tg.region.eq("Europe")
print(f"  {int(EUROPE.sum())} team-games in Europe "
      f"({sorted(tg.loc[EUROPE, 'team'].unique())})")

# Rest days are computed BEFORE any European game is dropped: a team's recovery
# between its real games does not change because we chose not to count the
# flight that got it there.
tg["rest_days"] = tg.groupby("team").game_date.diff().dt.days

write(tg, "team_games")

# %% the itinerary
# One row per place a team sleeps, in order. kind is:
#   season_start  the home arena, before game 1
#   game          a scheduled game
#   break_home    a return home inserted across a >= HOME_GAP_DAYS gap
itin = tg[~EUROPE].copy() if EXCLUDE_EUROPE else tg.copy()

stop_rows = []
for tri, g in itin.groupby("team"):
    g = g.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    h = home_airport.loc[tri]
    home_stop = {"team": tri, "kind": "season_start", "date": g.game_date.iloc[0],
                 "iata": h.iata, "lat": h.lat, "lon": h.lon,
                 "utc_std": h.utc_std, "game_id": pd.NA, "is_home_game": pd.NA}
    stops = [home_stop]
    on_road = False
    prev_date = None
    for r in g.itertuples(index=False):
        # send the team home across a long gap, or across a league-mandated
        # break, unless it is already going home for the next game anyway
        spans_break = (prev_date is not None and any(
            d in LEAGUE_BREAK_DATES
            for d in pd.date_range(prev_date, r.game_date, inclusive="neither")))
        if (on_road and prev_date is not None
                and ((r.game_date - prev_date).days >= HOME_GAP_DAYS or spans_break)
                and r.iata != h.iata):
            stops.append({**home_stop, "kind": "break_home",
                          "date": prev_date + pd.Timedelta(days=1)})
            on_road = False
        stops.append({"team": tri, "kind": "game", "date": r.game_date,
                      "iata": r.iata, "lat": r.lat, "lon": r.lon,
                      "utc_std": r.utc_std, "game_id": r.game_id,
                      "is_home_game": r.is_home})
        on_road = not r.is_home
        prev_date = r.game_date
    stop_rows.extend(stops)

stops = pd.DataFrame(stop_rows)
stops["seq"] = stops.groupby("team").cumcount()
n_break = int(stops.kind.eq("break_home").sum())
print(f"  {len(stops):,} stops, including {n_break} returns home across a "
      f">= {HOME_GAP_DAYS}-day gap or a league break")
# NOTE: stops is written at the END of the road-trips cell below, not here, so
# the persisted table carries is_away_game and trip_id and can be joined to
# trips.parquet. Writing it here left a table that could not.

# %% legs
# One leg per stop after the first: where the team came from, where it landed.
prev = stops.groupby("team").shift(1)
legs = pd.DataFrame({
    "team": stops.team,
    "date": stops.date,
    "kind": stops.kind,
    "arrive_for_game_id": stops.game_id,
    "is_home_game": stops.is_home_game,
    "from_iata": prev.iata,
    "to_iata": stops.iata,
    "km": haversine_km(prev.lat, prev.lon, stops.lat, stops.lon),
    # positive = eastward, the direction the circadian literature treats as the
    # harder one for the body to absorb
    "tz_delta": stops.utc_std - prev.utc_std,
}, index=stops.index).dropna(subset=["from_iata"])

# keep the stop each leg lands on, so trip distances can be joined back without
# relying on positional alignment
legs["stop_index"] = legs.index
legs = legs.reset_index(drop=True)
legs["leg_index"] = legs.groupby("team").cumcount()
legs["miles"] = legs.km / KM_PER_MI
legs["is_flight"] = legs.km > BUS_KM

# leg-chain integrity: leg i must depart from where leg i-1 landed
chk = legs.assign(prev_to=legs.groupby("team").to_iata.shift(1))
broken = chk[chk.prev_to.notna() & (chk.prev_to != chk.from_iata)]
assert broken.empty, f"broken leg chain:\n{broken.head()}"
assert legs.km.ge(0).all() and legs.km.notna().all()
print(f"  {len(legs):,} legs, {int(legs.is_flight.sum()):,} of them flights "
      f"(> {BUS_KM:.0f} km)")
write(legs, "legs")

# %% road trips
# A trip is a maximal run of consecutive away-game stops. A break_home stop
# ends one, which is exactly what the HOME_GAP_DAYS rule is for.
# A new trip starts at an away game whose PREVIOUS STOP was not an away game.
# Reading the predecessor off stops rather than off the games is what makes the
# break_home rule bite: it sits between the two away games and splits them.
stops["is_away_game"] = stops.kind.eq("game") & stops.is_home_game.eq(False)
prev_away = stops.groupby("team").is_away_game.shift(1).eq(True)
stops["trip_id"] = (stops.is_away_game & ~prev_away).cumsum()

km_by_stop = legs.set_index("stop_index").km
away = stops[stops.is_away_game].copy()
away["leg_km"] = km_by_stop.reindex(away.index).values

trips = (away.groupby(["team", "trip_id"])
         .agg(start=("date", "first"), end=("date", "last"),
              n_games=("date", "size"), km=("leg_km", "sum"))
         .reset_index())
trips["road_days"] = (trips.end - trips.start).dt.days + 1
print(f"  {len(trips):,} road trips, {trips.n_games.mean():.2f} games and "
      f"{trips.road_days.mean():.1f} days each on average, "
      f"longest {trips.road_days.max()} days")
write(trips, "trips")
write(stops, "stops")      # now carries is_away_game and trip_id

# %% weekly travel, for the within-team lumpiness measure
SEASON_START = games.game_date.min()
legs["week"] = ((legs.date - SEASON_START).dt.days // 7).astype(int)
n_weeks = legs.week.max() + 1

team_weeks = (legs.groupby(["team", "week"], as_index=False).km.sum()
              .set_index(["team", "week"])
              .reindex(pd.MultiIndex.from_product(
                  [sorted(legs.team.unique()), range(n_weeks)],
                  names=["team", "week"]), fill_value=0.0)
              .reset_index())
team_weeks["week_start"] = SEASON_START + pd.to_timedelta(team_weeks.week * 7, "D")
print(f"  {n_weeks} season weeks")
write(team_weeks, "team_weeks")


def rolling_max_km(g, days):
    """Heaviest `days`-day stretch of travel for one team, in km."""
    s = g.set_index("date").km.resample("D").sum()
    return s.rolling(f"{days}D").sum().max()


# %% per-team metrics
rows = []
for tri, lk in legs.groupby("team"):
    g = itin[itin.team == tri].sort_values(["game_date", "game_id"])
    tp = trips[trips.team == tri]
    fl = lk[lk.is_flight]
    wk = team_weeks.loc[team_weeks.team == tri, "km"]

    # tight turnarounds, on the games themselves rather than the stops
    d = g.game_date.reset_index(drop=True)
    venue_iata = g.iata.reset_index(drop=True)
    b2b = d.diff().dt.days.eq(1)
    b2b_travel = b2b & venue_iata.ne(venue_iata.shift())
    # km flown on the second half of a travel back-to-back, keyed on game id so
    # the inserted break_home legs cannot shift the alignment
    km_by_game = lk.dropna(subset=["arrive_for_game_id"]).set_index("arrive_for_game_id").km
    b2b_ids = g.game_id.reset_index(drop=True)[b2b_travel]
    three_in_four = int((d - d.shift(2)).dt.days.le(3).sum())

    rows.append({
        "team": tri,
        # distance
        "total_km": lk.km.sum(),
        "total_miles": lk.miles.sum(),
        "n_flights": int(len(fl)),
        "mean_flight_km": fl.km.mean(),
        "max_leg_km": lk.km.max(),
        # time away
        "n_trips": len(tp),
        "road_days": int(tp.road_days.sum()),
        "longest_trip_days": int(tp.road_days.max()),
        "longest_trip_games": int(tp.n_games.max()),
        "longest_trip_km": tp.km.max(),
        # circadian
        "tz_crossings": lk.tz_delta.abs().sum(),
        "eastward_hours": lk.tz_delta.clip(lower=0).sum(),
        # density
        "b2b": int(b2b.sum()),
        "b2b_with_travel": int(b2b_travel.sum()),
        "b2b_travel_km": float(km_by_game.reindex(b2b_ids).sum()),
        "three_in_four": three_in_four,
        # lumpiness
        "week_km_gini": gini(wk),
        "max_7day_km": rolling_max_km(lk, 7),
        "max_14day_km": rolling_max_km(lk, 14),
    })

tt = pd.DataFrame(rows).set_index("team")

# %% rest deficit
# Days of rest each side brought to the game. Computed on team_games, so the
# European games still count as rest for the four teams that play them - only
# their travel is excluded, not their existence.
rest = tg[["game_id", "team", "rest_days"]]
m = rest.merge(rest, on="game_id", suffixes=("", "_opp"))
m = m[m.team != m.team_opp].dropna(subset=["rest_days", "rest_days_opp"])
tt["rest_deficit_games"] = (m.assign(deficit=m.rest_days_opp > m.rest_days)
                            .groupby("team").deficit.sum())
tt["mean_rest_days"] = m.groupby("team").rest_days.mean()

# %% the Travel Burden Index
# Five pillars, each an average of its own z-scores so a pillar measured by two
# columns does not outweigh one measured by a single column, then an unweighted
# mean of the five. Every pillar keeps its own rank below, so the composite can
# always be taken apart.
PILLARS = {
    "p_distance": ["total_km"],
    "p_time_away": ["road_days", "longest_trip_days"],
    "p_circadian": ["tz_crossings", "eastward_hours"],
    "p_density": ["b2b_with_travel", "three_in_four"],
    "p_recovery": ["rest_deficit_games"],
}
for pillar, cols in PILLARS.items():
    tt[pillar] = pd.concat([z(tt[c]) for c in cols], axis=1).mean(axis=1)
    tt[pillar + "_rank"] = tt[pillar].rank(ascending=False, method="min").astype(int)

# Two composites the Part 2 analysis leans on, persisted here so every script
# shares one definition rather than recomputing it three different ways.
#   trav_z  what geography imposes: distance, time zones, nights away
#   cal_z   what the schedule chooses: when the games fall, and against whom
# comb weights the two evenly, which is NOT what the TBI does (it is 3:2 across
# the pillars and also counts trip length) - the two rankings differ by a mean
# of 3.4 places and must not be described as the same thing.
TRAVEL_COLS = ["total_km", "tz_crossings", "road_days"]
CALENDAR_COLS = ["b2b_with_travel", "three_in_four", "rest_deficit_games"]
tt["trav_z"] = pd.concat([z(tt[c]) for c in TRAVEL_COLS], axis=1).mean(axis=1)
tt["cal_z"] = pd.concat([z(tt[c]) for c in CALENDAR_COLS], axis=1).mean(axis=1)
tt["comb"] = (tt.trav_z + tt.cal_z) / 2
for col in ("trav_z", "cal_z", "comb"):
    tt[col.replace("_z", "") + "_rank"] = (
        tt[col].rank(ascending=False, method="min").astype(int))

tt["tbi"] = tt[list(PILLARS)].mean(axis=1)
tt["tbi_rank"] = tt.tbi.rank(ascending=False, method="min").astype(int)
tt["km_rank"] = tt.total_km.rank(ascending=False, method="min").astype(int)
tt["lumpiness_rank"] = tt.week_km_gini.rank(ascending=False, method="min").astype(int)

tt = tt.sort_values("tbi", ascending=False).reset_index()

# %% verification
assert len(tt) == 32
assert tt.tbi_rank.is_unique and tt.km_rank.is_unique
lo, hi = tt.total_km.min(), tt.total_km.max()
print(f"\n  per-team distance {lo:,.0f} - {hi:,.0f} km")
assert 30_000 < lo and hi < 110_000, "outside the range an 84-game season gives"

# known-distance spot checks against published great-circle figures
ap = venues.drop_duplicates("iata").set_index("iata")
for a, b, want in [("YVR", "YYZ", 3346), ("LAX", "BOS", 4180), ("EWR", "JFK", 34)]:
    got = float(haversine_km(ap.loc[a].lat, ap.loc[a].lon, ap.loc[b].lat, ap.loc[b].lon))
    assert abs(got - want) < max(30, 0.03 * want), f"{a}-{b}: {got:.0f} != ~{want}"
    print(f"  spot check {a}-{b}  {got:,.0f} km (expected ~{want:,})")

assert trips.road_days.max() <= 15, ("a road trip longer than 15 days almost "
                                     "certainly straddles a break")
season_days = (games.game_date.max() - games.game_date.min()).days + 1
frac = tt.road_days / season_days
print(f"  road days are {frac.min():.0%}-{frac.max():.0%} of the "
      f"{season_days}-day season; longest single trip "
      f"{trips.road_days.max()} days")
assert frac.between(0.15, 0.65).all()

write(tt, "team_travel")

# %% headline numbers
print("\n" + "=" * 78)
print(f"LEAGUE INEQUALITY  (2026-27 regular season, "
      f"{'excluding' if EXCLUDE_EUROPE else 'including'} the European games)")
print("=" * 78)
for col, label in [("total_km", "distance flown"), ("road_days", "days on the road"),
                   ("tz_crossings", "time-zone hours crossed"),
                   ("n_flights", "flights")]:
    v = tt[col]
    print(f"  {label:26s} Gini {gini(v):.3f}   "
          f"spread {v.min():>9,.0f} - {v.max():>9,.0f}   ratio {v.max()/v.min():.2f}x")

top5, bot5 = tt.nlargest(5, "total_km"), tt.nsmallest(5, "total_km")
gap = top5.total_km.mean() - bot5.total_km.mean()
print(f"\n  top 5 average {top5.total_km.mean():,.0f} km vs bottom 5 "
      f"{bot5.total_km.mean():,.0f} km  (gap {gap:,.0f} km, {gap/KM_PER_MI:,.0f} miles)")
print(f"  TBI vs raw distance, Spearman: "
      f"{tt.tbi.corr(tt.total_km, method='spearman'):.3f}")
