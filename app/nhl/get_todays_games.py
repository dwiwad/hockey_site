"""
Get today's NHL games and return a dataframe of game_id, away team, and home team.
Intended to run daily at 3am Central to power live dashboards.

Created on Sat Aug 16 09:32:12 2025

@author: dwiwad
"""
# app/nhl/get_todays_games.py  (rename if you like)
import requests
import pandas as pd
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ_APP = ZoneInfo("America/Toronto")   # your app/user timezone
TZ_ET  = ZoneInfo("America/Toronto")   # ET == Toronto for NHL use

def _cache_path(d: date) -> Path:
    return Path(f"data/cache/schedule/{d.isoformat()}.parquet")

def get_games_for_date(target_date: date, force_refresh: bool = False) -> pd.DataFrame:
    """
    Fetch NHL games for a specific calendar date (Toronto/ET),
    returning: game_id, season, start, away, home, away_tri, home_tri
    """
    cache_file = _cache_path(target_date)

    if cache_file.exists() and not force_refresh:
        return pd.read_parquet(cache_file)

    # NHL endpoint returns a *week* containing target_date
    url = f"https://api-web.nhle.com/v1/schedule/{target_date.isoformat()}"

    try:
        resp = requests.get(url, timeout=(5, 20))
        resp.raise_for_status()
        data = resp.json()

        # Find the day-block within the week that matches target_date
        # Each entry in gameWeek looks like: {"date": "2025-09-23", "games": [...]}
        day_block = None
        for block in data.get("gameWeek", []):
            if block.get("date") == target_date.isoformat():
                day_block = block
                break

        games_list = (day_block or {}).get("games", [])

        if not games_list:
            # still return an empty DF with expected columns
            return pd.DataFrame(columns=[
                "game_id","season","start","away","home","away_tri","home_tri"
            ])

        games = pd.json_normalize(games_list)

        # Parse UTC start, convert to ET (Toronto). Then format as e.g., "7:00 PM ET"
        games["start_dt_utc"] = pd.to_datetime(games["startTimeUTC"], utc=True)
        games["start_et"] = games["start_dt_utc"].dt.tz_convert(TZ_ET)

        # Cross-platform hour without leading zero:
        # Windows doesn't support %-I; use %I then lstrip("0")
        games["start_et_str"] = games["start_et"].dt.strftime("%I:%M %p ET").str.lstrip("0")

        df = pd.DataFrame({
            "game_id" : games["id"],
            "season"  : games["season"],
            "start"   : games["start_et_str"],
            "away"    : games["awayTeam.commonName.default"],
            "home"    : games["homeTeam.commonName.default"],
            "away_tri": games["awayTeam.abbrev"],
            "home_tri": games["homeTeam.abbrev"],
        })

        cache_file.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cache_file, index=False)
        return df

    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error fetching NHL schedule for {target_date}: {e}")
        return pd.DataFrame(columns=[
            "game_id","season","start","away","home","away_tri","home_tri"
        ])

    
