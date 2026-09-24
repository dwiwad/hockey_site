# NHL 2026-27 travel inequality

Self-contained. Nothing here is wired into the site — no route, no post, no S3
write, no edit to `DATA_WAREHOUSE.md`. Delete this directory and the repo is
exactly as it was.

Ranks all 32 teams on how hard their 2026-27 regular-season travel is, and on
how evenly that travel is spread across the season.

## Run it

```bash
/opt/anaconda3/bin/python "1_get_data.py"     # NHL API + OpenFlights -> data/
/opt/anaconda3/bin/python "2_wrangle.py"      # itineraries + metrics -> data/
TI_EXCLUDE_EUROPE=0 /opt/anaconda3/bin/python "2_wrangle.py"   # sensitivity run
/opt/anaconda3/bin/python "3_figures.py"      # fig1-8  + printed rankings
/opt/anaconda3/bin/python "4_maps.py"         # map1-7  (maps and journeys)
/opt/anaconda3/bin/python "5_rankings.py"     # figures/rankings/  one per metric
/opt/anaconda3/bin/python "6_calendar.py"     # figures/part2/     the Part 2 story
```

Use the anaconda interpreter, not `.venv`. Spyder runs on anaconda, and the
repo `.venv` ships pyarrow 21 against anaconda's 19 — parquet written by one
cannot be read by the other. Each script is also cell-by-cell runnable in
Spyder via its `# %%` markers.

## Where the schedule came from

`s3://hockey-decoded/live-data-cache/daily-schedule/{DATE}.parquet` already
holds the complete 2026-27 season — 193 date files, 1,344 regular-season games,
84 per team, pulled 2026-07-17 to 07-21. It was not used here, because it
stores only `game_id, season, start, start_utc, away, home, away_tri, home_tri`.
No venue, no `neutralSite` flag, no venue timezone, so it silently implies every
game is played at the home team's arena. That is wrong seven times in 2026-27.

`api-web.nhle.com/v1/club-schedule-season/{TEAM}/20262027` returns `venue`,
`neutralSite`, `venueTimezone` and `venueUTCOffset` per game. One request per
team, deduped by game id.

## Modelling decisions

Each is a judgement call, written down so it can be argued with.

**Airports, not arenas.** 37 venues map to 33 airports, hardcoded in
`1_get_data.py` with a comment on every non-obvious choice (NJD and NYR fly out
of Newark, NYI out of JFK, Anaheim out of John Wayne, Washington out of
National). Coordinates come from OpenFlights `airports.dat`, cached to
`data/airports.dat`, rather than from memory. Distances are haversine great
circles on the IUGG mean radius.

**Trans-Atlantic games are excluded from the headline numbers.** Carolina and
Seattle play twice in Helsinki; Chicago and Ottawa twice in Düsseldorf. Those
four games are dropped from the itineraries and the surrounding legs bridged.
Including them would decide the ranking on a once-a-decade quirk: Seattle goes
from 13th in distance to 1st, and from 8th on the composite index to 1st. The
sensitivity table at the bottom of `3_figures.py`'s output shows the full
effect. The three *domestic* neutral sites (Winnipeg outdoor, Rice-Eccles,
AT&T Stadium) are kept — that is ordinary travel, and for Utah and Dallas the
outdoor venue shares an airport with the home arena, so it costs them nothing.

**Teams go home across long gaps.** Read literally, the itinerary puts New
Jersey on one 22-day road trip across the All-Star break and Toronto on a
17-day trip across Christmas. Nobody does that. So a road team is sent home
when the next game is 5 or more days away, or when the gap contains a league-
mandated break. The 5-day threshold is the cliff in the actual distribution:
away-to-away gaps are 1-4 days 748 times, and the only larger ones are 5, 7, 9,
10 and 11 days — ten of them, all byes. The breaks are read off the schedule as
runs of two or more dates on which no game is played anywhere, which in 2026-27
finds exactly December 23-25 and February 4-7.

**Time zones use standard offsets.** The API's `venueUTCOffset` is DST-correct
per game, so differencing it books a phantom crossing every time a team sits
still through the November or March switch. The venue table carries standard-
time offsets instead, so a crossing only happens by moving.

**Bus threshold 400 km**, separating `n_legs` from `n_flights`. NYR/NYI/NJD,
Anaheim/LA and Philadelphia/New York fall below it.

## The Travel Burden Index

Five pillars, each the average of its own z-scores across the 32 teams, then an
unweighted mean of the five. Every pillar keeps its own rank, so the composite
can always be taken apart (that is what `fig4` is for).

| Pillar | Columns |
|---|---|
| Distance | `total_km` |
| Time away | `road_days`, `longest_trip_days` |
| Circadian | `tz_crossings`, `eastward_hours` |
| Density | `b2b_with_travel`, `three_in_four` |
| Recovery | `rest_deficit_games` |

The weighting is a choice, not a finding. TBI correlates with raw distance at
Spearman 0.58 — related but far from redundant, which is the point of building
it. Distance and circadian load move together (ρ = 0.74, unsurprising: the long
flights are the east-west ones), while density runs *against* distance
(ρ = -0.37) — the schedule-maker appears to hand fewer tight turnarounds to the
teams already flying the farthest.

## Reading the lumpiness ranking

`week_km_gini` correlates -0.62 with total distance. Teams that fly least have
the lumpiest schedules, and the mechanism is mechanical rather than mysterious:
a Metropolitan team's baseline week is a couple of near-zero bus trips, so its
one western swing produces a huge spike relative to its own average. High
lumpiness is a statement about a team's variance, not its burden. The two
rankings answer different questions and should be read separately.

## Files

```
1_get_data.py   NHL API + OpenFlights  ->  data/games.parquet, data/venues.parquet
2_wrangle.py    itineraries and metrics ->  data/{team_games,stops,legs,trips,
                                                  team_weeks,team_travel}.parquet
3_figures.py    figures/fig1..fig8.png  +  the printed rankings
4_maps.py       figures/map1..map7.png  - road-trip anatomies, the heaviest and
                lightest seasons, the league air network, a travel calendar and
                the time-zone waveform
5_rankings.py   figures/rankings/rank_NN_*.png - one ranked bar chart per metric
6_calendar.py   figures/part2/p2_01..p2_10.png - calendar burden, and the
                trade-off against travel (Part 2 of the post)
geo.py          Albers projection, curved flight arcs, and a Natural Earth
                basemap (50m land, borders and lakes) - no mapping library
hd_style.py     vendored copy of the house figure style, plus TEAM_COLORS,
                TEAM_NAMES, DIVISION and CONFERENCE
data/           parquet outputs and the cached OpenFlights file (gitignored? no —
                nothing here is in .gitignore, it will show as untracked)
figures/        PNGs at dpi=300, transparent background
```

`FINDINGS.md` interprets every figure and carries the argument about why the
headline Gini understates the inequality.

`team_travel.parquet` is the one table worth keeping: 32 rows, every metric and
every rank. `team_travel_with_europe.parquet` is the same thing from the
sensitivity run.

Both `1_get_data.py` and `2_wrangle.py` have a `WRITE_S3 = False` flag that will
mirror their tables to `s3://hockey-decoded/static-ds-analyses/travel-inequality/`
if you ever want them in the warehouse.

## Checks that run on every execution

Stage 1 asserts 1,344 games, 32 teams, 84 games each, that every venue resolves
to a geocoded airport, and that no non-neutral game is played away from the
home team's arena. Stage 2 asserts the leg chain is unbroken (every leg departs
where the previous one landed), that no road trip exceeds 15 days, that per-team
distance lands in a plausible range, and it spot-checks YVR-YYZ, LAX-BOS and
EWR-JFK against published great-circle distances.
