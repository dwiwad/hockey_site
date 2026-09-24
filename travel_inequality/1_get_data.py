"""1_get_data.py - pull the raw tables the 2026-27 travel-inequality analysis needs.

Writes to travel_inequality/data/:
  games.parquet    one row per 2026-27 regular-season game, with venue
  venues.parquet   one row per venue: city, airport, lat/lon, standard UTC offset

Written for cell-by-cell execution in Spyder (Ctrl+Enter through the # %% cells).
It also runs top-to-bottom as a plain script.

Why club-schedule-season and not the cached daily_schedule
----------------------------------------------------------
s3://hockey-decoded/live-data-cache/daily-schedule/{DATE}.parquet already holds
the complete 2026-27 season - 1,344 regular-season games, 84 per team, verified.
But it stores only game_id, season, start, start_utc, away, home, away_tri,
home_tri. There is no venue and no neutralSite flag, so it silently implies
every game is played at the home team's arena. That is false seven times in
2026-27: CAR/SEA play twice in Helsinki, CHI/OTT twice in Dusseldorf, and there
are three domestic neutral sites. api-web.nhle.com/v1/club-schedule-season
returns venue, neutralSite, venueTimezone and venueUTCOffset per game, which is
what an itinerary actually needs.

Why standard UTC offsets are hardcoded rather than read from the API
--------------------------------------------------------------------
venueUTCOffset is DST-correct for the date of each game. Differencing it across
consecutive games therefore books a phantom one-hour "time zone crossing" every
time a team sits still through the November and March DST transitions. The
travel metric wants the offset difference caused by MOVING, so the venue table
carries each venue's standard-time offset and the legs are differenced on that.
"""

# %% imports and configuration
import sys
import time
from pathlib import Path

import pandas as pd
import requests

try:
    HERE = Path(__file__).resolve().parent
except NameError:                       # Spyder cell execution
    HERE = Path("/Users/dwiwad/dev/hockey_site/travel_inequality")

DATA = HERE / "data"
DATA.mkdir(parents=True, exist_ok=True)

SEASON = 20262027
PACE = 0.4                              # seconds between requests
BASE = "https://api-web.nhle.com/v1"
OPENFLIGHTS = ("https://raw.githubusercontent.com/jpatokal/openflights"
               "/master/data/airports.dat")

WRITE_S3 = False                        # flip to mirror into the warehouse later
S3_PREFIX = "static-ds-analyses/travel-inequality"

TEAMS = ["ANA", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI", "COL", "DAL", "DET",
         "EDM", "FLA", "LAK", "MIN", "MTL", "NJD", "NSH", "NYI", "NYR", "OTT",
         "PHI", "PIT", "SEA", "SJS", "STL", "TBL", "TOR", "UTA", "VAN", "VGK",
         "WPG", "WSH"]

print(f"{len(TEAMS)} teams, season {SEASON} -> {DATA}")

# %% helpers - http
SESSION = requests.Session()            # one connection pool for 32 requests


def fetch(url, retries=6):
    """GET one JSON document, with the house retry behaviour.

    Lifted from scripts/career-player-tenure/1. Get_all_data.py. Two things
    matter here:

    * A 429 sleeps for the full Retry-After (or an exponential fallback) rather
      than retrying straight back into the same wall.
    * It RAISES when every attempt fails, and never returns an empty dict to
      paper over an error. A silent `except: pass` is what left gaps in the
      demographics roster file in the first place.
    """
    last = None
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=45)
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 0)) or 10 * 2 ** attempt
                print(f"    429 - sleeping {wait:.0f}s", flush=True)
                time.sleep(wait)
                last = "429"
                continue
            r.raise_for_status()
            time.sleep(PACE)
            return r.json()
        except Exception as e:          # noqa: BLE001 - retried with backoff
            last = e
            time.sleep(2.0 * (attempt + 1))
    raise RuntimeError(f"{url} failed after {retries} attempts: {last}")


def write(df, name):
    """Write one table to data/, and optionally mirror to S3.

    Guards against writing an empty table: silently replacing good data with a
    zero-row file is the failure that would be hardest to notice later.
    """
    if df.empty:
        raise ValueError(f"refusing to write an empty table: {name}")
    path = DATA / f"{name}.parquet"
    df.to_parquet(path, index=False)
    print(f"  wrote {path}  ({len(df):,} rows)")
    if WRITE_S3:
        from app.core.config import S3_BUCKET
        uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/{name}.parquet"
        df.to_parquet(uri, storage_options={"anon": False}, index=False)
        print(f"  mirrored {uri}")


# %% the venue table
# One row per venue that hosts a 2026-27 regular-season game. Column meanings:
#
#   home_team   tenant tricode, or None for a neutral site
#   iata        the airport a charter would actually use, not always the
#               nearest or the busiest - see the notes below
#   utc_std     standard-time UTC offset in hours, used for time-zone crossings
#   region      None for North America, else the continent, so the European
#               games can be excluded as a group
#
# Airport choices worth defending:
#   ANA  SNA   John Wayne is 3 miles from Honda Center; LAX is 35.
#   NJD  EWR   Prudential Center is 2 miles from Newark Liberty.
#   NYR  EWR   MSG has no obvious airport. Charters out of Manhattan use
#              Newark or Teterboro; Teterboro has no IATA row, so EWR.
#   NYI  JFK   UBS Arena sits at Belmont Park, 13 miles from JFK. Islip is
#              farther from the arena despite being "the Long Island airport".
#   WSH  DCA   National, not Dulles - it is 4 miles from Capital One Arena.
#   FLA  FLL   Fort Lauderdale is closer to Sunrise than Miami International.
#   MIN  MSP   the airport is between Minneapolis and St. Paul either way.
#   UTA  SLC   Delta Center and Rice-Eccles share the same airport, so the
#              Dec 31 outdoor game is a zero-mile "trip" for Utah. Correct.
#   DAL  DFW   AT&T Stadium in Arlington is 20 miles from DFW, same as the
#              American Airlines Center. Also a zero-mile trip for Dallas.
#
VENUES = [
    # venue,                        home, city,            iata,  utc_std, region
    ("Honda Center",                "ANA", "Anaheim",       "SNA",  -8.0, None),
    ("TD Garden",                   "BOS", "Boston",        "BOS",  -5.0, None),
    ("KeyBank Center",              "BUF", "Buffalo",       "BUF",  -5.0, None),
    ("Lenovo Center",               "CAR", "Raleigh",       "RDU",  -5.0, None),
    ("Nationwide Arena",            "CBJ", "Columbus",      "CMH",  -5.0, None),
    ("Scotiabank Saddledome",       "CGY", "Calgary",       "YYC",  -7.0, None),
    ("United Center",               "CHI", "Chicago",       "ORD",  -6.0, None),
    ("Ball Arena",                  "COL", "Denver",        "DEN",  -7.0, None),
    ("American Airlines Center",    "DAL", "Dallas",        "DFW",  -6.0, None),
    ("Little Caesars Arena",        "DET", "Detroit",       "DTW",  -5.0, None),
    ("Rogers Place",                "EDM", "Edmonton",      "YEG",  -7.0, None),
    ("Amerant Bank Arena",          "FLA", "Sunrise",       "FLL",  -5.0, None),
    ("Crypto.com Arena",            "LAK", "Los Angeles",   "LAX",  -8.0, None),
    ("Grand Casino Arena",          "MIN", "St. Paul",      "MSP",  -6.0, None),
    ("Centre Bell",                 "MTL", "Montreal",      "YUL",  -5.0, None),
    ("Prudential Center",           "NJD", "Newark",        "EWR",  -5.0, None),
    ("Bridgestone Arena",           "NSH", "Nashville",     "BNA",  -6.0, None),
    ("UBS Arena",                   "NYI", "Elmont",        "JFK",  -5.0, None),
    ("Madison Square Garden",       "NYR", "New York",      "EWR",  -5.0, None),
    ("Canadian Tire Centre",        "OTT", "Ottawa",        "YOW",  -5.0, None),
    ("Xfinity Mobile Arena",        "PHI", "Philadelphia",  "PHL",  -5.0, None),
    ("PPG Paints Arena",            "PIT", "Pittsburgh",    "PIT",  -5.0, None),
    ("Climate Pledge Arena",        "SEA", "Seattle",       "SEA",  -8.0, None),
    ("SAP Center at San Jose",      "SJS", "San Jose",      "SJC",  -8.0, None),
    ("Enterprise Center",           "STL", "St. Louis",     "STL",  -6.0, None),
    ("Benchmark International Arena", "TBL", "Tampa",       "TPA",  -5.0, None),
    ("Scotiabank Arena",            "TOR", "Toronto",       "YYZ",  -5.0, None),
    ("Delta Center",                "UTA", "Salt Lake City","SLC",  -7.0, None),
    ("Rogers Arena",                "VAN", "Vancouver",     "YVR",  -8.0, None),
    ("T-Mobile Arena",              "VGK", "Las Vegas",     "LAS",  -8.0, None),
    ("Canada Life Centre",          "WPG", "Winnipeg",      "YWG",  -6.0, None),
    ("Capital One Arena",           "WSH", "Washington",    "DCA",  -5.0, None),
    # neutral sites
    ("Veikkaus Arena",              None,  "Helsinki",      "HEL",  +2.0, "Europe"),
    ("PSD Bank Dome",               None,  "Dusseldorf",    "DUS",  +1.0, "Europe"),
    ("Rice-Eccles Stadium",         None,  "Salt Lake City","SLC",  -7.0, None),
    ("AT&T Stadium",                None,  "Arlington",     "DFW",  -6.0, None),
    ("Princess Auto Stadium",       None,  "Winnipeg",      "YWG",  -6.0, None),
]

venues = pd.DataFrame(VENUES, columns=["venue", "home_team", "city", "iata",
                                       "utc_std", "region"])

# %% join airport coordinates from OpenFlights
# Cached so a rerun is offline. OpenFlights airports.dat is headerless; the
# columns used here are name(1), iata(4), lat(6), lon(7).
AIRPORTS = DATA / "airports.dat"
if not AIRPORTS.exists():
    r = SESSION.get(OPENFLIGHTS, timeout=60)
    r.raise_for_status()
    AIRPORTS.write_bytes(r.content)
    print(f"  cached {AIRPORTS}")

af = pd.read_csv(AIRPORTS, header=None, na_values=["\\N"],
                 names=["of_id", "airport", "of_city", "country", "iata", "icao",
                        "lat", "lon", "alt", "of_tz", "dst", "tzdb", "type",
                        "source"])
af = (af[af.iata.notna() & (af.type == "airport")]
      .drop_duplicates("iata")[["iata", "airport", "lat", "lon"]])

venues = venues.merge(af, on="iata", how="left", validate="many_to_one")

missing = venues[venues.lat.isna()]
if len(missing):
    raise ValueError(f"no coordinates for: {missing.iata.tolist()}")
print(f"  {len(venues)} venues, {venues.iata.nunique()} distinct airports, "
      f"all geocoded")

# %% pull the schedule
# One request per team returns that club's full 88-game season (84 regular +
# preseason). Every game therefore arrives twice, once from each participant;
# the dict keyed on game id dedupes it.
rows = {}
for tri in TEAMS:
    doc = fetch(f"{BASE}/club-schedule-season/{tri}/{SEASON}")
    n = 0
    for g in doc["games"]:
        if g["gameType"] != 2:          # 1 = preseason, 2 = regular, 3 = playoffs
            continue
        n += 1
        rows[g["id"]] = {
            "game_id": g["id"],
            "season": g["season"],
            "game_date": g["gameDate"],
            "start_utc": g["startTimeUTC"],
            "venue": g["venue"]["default"],
            "neutral_site": bool(g.get("neutralSite", False)),
            "venue_tz": g.get("venueTimezone"),
            "venue_utc_offset": g.get("venueUTCOffset"),
            "home_tri": g["homeTeam"]["abbrev"],
            "away_tri": g["awayTeam"]["abbrev"],
        }
    print(f"  {tri}  regular-season games={n}", flush=True)

games = (pd.DataFrame(rows.values())
         .sort_values(["game_date", "game_id"])
         .reset_index(drop=True))
games["game_date"] = pd.to_datetime(games["game_date"]).dt.date
games["start_utc"] = pd.to_datetime(games["start_utc"], utc=True)

# %% verify, then write
gp = pd.concat([games.home_tri, games.away_tri]).value_counts()
assert len(games) == 1344, f"expected 1,344 regular-season games, got {len(games)}"
assert len(gp) == 32, f"expected 32 teams, got {len(gp)}"
assert (gp == 84).all(), f"uneven games played: {gp[gp != 84].to_dict()}"

unknown = set(games.venue) - set(venues.venue)
if unknown:
    raise ValueError(f"venues missing from the reference table: {sorted(unknown)}")
unused = set(venues.venue) - set(games.venue)
if unused:
    print(f"  note: reference venues with no 2026-27 game: {sorted(unused)}")

# Every team's home games must be at its own arena unless flagged neutral. This
# is the check that would have caught the Helsinki and Dusseldorf games if the
# cached daily_schedule had been used instead.
home_arena = venues.dropna(subset=["home_team"]).set_index("home_team").venue
mismatch = games[(~games.neutral_site)
                 & (games.venue != games.home_tri.map(home_arena))]
assert mismatch.empty, f"non-neutral games away from the home arena:\n{mismatch}"

print(f"\n{len(games):,} games, {games.game_date.min()} -> {games.game_date.max()}, "
      f"{games.game_date.nunique()} dates")
print(f"{int(games.neutral_site.sum())} neutral-site games:")
for _, g in games[games.neutral_site].iterrows():
    print(f"  {g.game_date}  {g.away_tri} @ {g.home_tri}  {g.venue}")

write(games, "games")
write(venues, "venues")
