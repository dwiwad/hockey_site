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
import s3fs

TZ_APP = ZoneInfo("America/Toronto")   # your app/user timezone
TZ_ET  = ZoneInfo("America/Toronto")   # ET == Toronto for NHL use

S3_BUCKET = "hockey-decoded"
S3_PREFIX = "live-data-cache/daily-schedule"   
fs = s3fs.S3FileSystem(anon=False)            # sets my AWS credentials

def _s3_path(d: date) -> str:
    # s3://hockey-decoded/live-data-cache/daily-schedule/DATE.parquet
    return f"s3://{S3_BUCKET}/{S3_PREFIX}/{d.isoformat()}.parquet"

def get_games_for_date(target_date: date, force_refresh: bool = False) -> pd.DataFrame:
    """
    Fetch NHL games for a specific calendar date (Toronto/ET),
    returning: game_id, season, start, away, home, away_tri, home_tri.
    Reads/writes a parquet file at:
    s3://hockey-decoded/live-data-cache/daily-schedule/YYYY-MM-DD.parquet
    """
    s3_path = _s3_path(target_date)

    # 1) If exists on S3 and not forcing, read from S3
    if fs.exists(s3_path) and not force_refresh:
        return pd.read_parquet(s3_path)

    # 2) Otherwise fetch from NHL API
    url = f"https://api-web.nhle.com/v1/schedule/{target_date.isoformat()}"

    try:
        resp = requests.get(url, timeout=(5, 20))
        resp.raise_for_status()
        data = resp.json()

        # Find the day-block within the returned week that matches target_date
        day_block = next(
            (block for block in data.get("gameWeek", []) if block.get("date") == target_date.isoformat()),
            None
        )
        games_list = (day_block or {}).get("games", [])

        if not games_list:
            # Return empty DF with expected columns (also write an empty file if you want)
            cols = ["game_id","season","start","away","home","away_tri","home_tri"]
            empty_df = pd.DataFrame(columns=cols)
            # optional: empty_df.to_parquet(s3_path, index=False)
            return empty_df

        games = pd.json_normalize(games_list)

        # Parse UTC start, convert to ET (Toronto). Then format e.g., "7:00 PM ET"
        games["start_dt_utc"] = pd.to_datetime(games["startTimeUTC"], utc=True)
        games["start_et"] = games["start_dt_utc"].dt.tz_convert(TZ_ET)
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

        # 3) Write to S3 and return
        df.to_parquet(s3_path, index=False)
        return df

    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Error fetching NHL schedule for {target_date}: {e}")
        return pd.DataFrame(columns=["game_id","season","start","away","home","away_tri","home_tri"])


    
