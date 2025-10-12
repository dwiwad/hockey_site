"""
This is going to be my data librarian for the play-by-play data. Fetch the 
play-by-play, cache it, allow it to be parsed later for metrics.

Created on Sat Sep 13 09:16:18 2025

@author: dwiwad
"""
# The API endpoint that has game play-by-play is:
# https://api-web.nhle.com/v1/gamecenter/GAMEIDHERE/play-by-play

from __future__ import annotations
from datetime import datetime, timezone
import json, time
from typing import Any, Dict, Optional
import httpx
import s3fs
import io
import pandas as pd

# Import the base url for the play-by-play endpoint
BASE = "https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
# Set the directory for where the data will be stored in s3 and creds
S3_BUCKET = "hockey-decoded"
S3_PREFIX = "live-data-cache/game-center"   
fs = s3fs.S3FileSystem(anon=False)  

###################################################################
# HELPERS
###################################################################

# Set the s3 paths for the json and the meta json for pbp
def _s3_path(season: int, game_id: int) -> str:
    # Data body: s3://hockey-decoded/live-data-cache/game-center/SEASON/GAMEID.json
    return f"s3://{S3_BUCKET}/{S3_PREFIX}/{season}/{game_id}.json"

def _s3_meta_path(season: int, game_id: int) -> str:
    # Meta alongside body: s3://.../SEASON/GAMEID.meta.json
    return f"s3://{S3_BUCKET}/{S3_PREFIX}/{season}/{game_id}.meta.json"

# Check to see if a file exists
def _s3_exists(path: str) -> bool:
    try:
        return fs.exists(path)
    except Exception:
        return False
    
# Check how old the file is, if it exists
def _s3_age_seconds(path: str) -> Optional[float]:
    """Return object age in seconds, or None if it doesn't exist."""
    try:
        if not fs.exists(path):
            return None
        info = fs.info(path)  # dict with keys like 'LastModified', 'ETag', 'Size'
        # s3fs returns LastModified as a datetime (newer versions) or ISO string (older)
        lm = info.get("LastModified") or info.get("last_modified") or info.get("updated")
        if isinstance(lm, str):
            # Fallback: parse ISO-ish string
            lm_dt = datetime.fromisoformat(lm.replace("Z", "+00:00"))
        elif isinstance(lm, datetime):
            lm_dt = lm
        else:
            return None
        now = datetime.now(timezone.utc)
        return (now - lm_dt.replace(tzinfo=timezone.utc)).total_seconds()
    except Exception:
        return None  

# Functions to read and write the json game and metadata files
def _s3_read_json(path: str) -> Dict[str, Any]:
    with fs.open(path, "rb") as f:
        return json.loads(f.read())

def _s3_write_json(path: str, obj: Dict[str, Any]) -> None:
    # Persist compact JSON; you can change to indent=2 if you prefer readability over size
    data = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    with fs.open(path, "wb") as f:
        f.write(data)

def _load_meta_s3(meta_path: str) -> Dict[str, Any]:
    if not _s3_exists(meta_path):
        return {}
    try:
        return _s3_read_json(meta_path)
    except Exception:
        return {}

def _save_meta_s3(meta_path: str, etag: Optional[str], last_modified: Optional[str]) -> None:
    meta: Dict[str, Any] = {}
    if etag:
        meta["etag"] = etag
    if last_modified:
        meta["last_modified"] = last_modified
    _s3_write_json(meta_path, meta)
    
###################################################################
# GET THE PLAY BY PLAY DATA
###################################################################

def fetch_game_pbp(
    game_id: int,
    season: int,
    ttl_seconds: int = 5,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Return the PBP JSON for a game, with S3-backed caching:
      - S3 TTL check to avoid bursty calls
      - Conditional GET (If-None-Match / If-Modified-Since) via S3-stored meta
      - Retry on timeouts, with cached fallback if available
    """
    data_path = _s3_path(season, game_id)
    meta_path = _s3_meta_path(season, game_id)

    # 1) TTL short-circuit: if recent S3 object exists and not forcing, use it
    if not force_refresh:
        age = _s3_age_seconds(data_path)
        if age is not None and age < ttl_seconds:
            return _s3_read_json(data_path)

    # 2) Build conditional headers from S3 meta (unless force refresh)
    headers: Dict[str, str] = {}
    meta = {} if force_refresh else _load_meta_s3(meta_path)
    etag = meta.get("etag")
    last_modified = meta.get("last_modified")
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    url = BASE.format(game_id=game_id)

    # 3) Make the request with light retry logic for transient failures
    backoffs = [1.5, 3.0]  # two retries
    attempts = len(backoffs) + 1
    for i in range(attempts):
        try:
            with httpx.Client(timeout=(5, 15)) as client:
                r = client.get(url, headers=headers)

            # 304 Not Modified → return cached S3 if present
            if r.status_code == 304:
                if _s3_exists(data_path):
                    return _s3_read_json(data_path)
                else:
                    # Rare: server says "unchanged" but we don't have a cache.
                    # Do an unconditional GET (no headers) once.
                    with httpx.Client(timeout=(5, 15)) as client:
                        fresh = client.get(url)
                    fresh.raise_for_status()
                    body = fresh.json()
                    _s3_write_json(data_path, body)
                    _save_meta_s3(
                        meta_path,
                        fresh.headers.get("ETag") or fresh.headers.get("Etag"),
                        fresh.headers.get("Last-Modified"),
                    )
                    return body

            # 200 OK (or other 2xx) → write body + meta to S3
            r.raise_for_status()
            body = r.json()
            _s3_write_json(data_path, body)
            _save_meta_s3(
                meta_path,
                r.headers.get("ETag") or r.headers.get("Etag"),
                r.headers.get("Last-Modified"),
            )
            return body

        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            # Retry timeouts with backoff; if we exhaust retries, fall back to cache if possible
            if i < len(backoffs):
                time.sleep(backoffs[i])
                continue
            if _s3_exists(data_path):
                return _s3_read_json(data_path)
            raise

        except httpx.HTTPStatusError as e:
            # For 5xx, try retries; for 4xx (other than 304) don't.
            status = e.response.status_code if e.response is not None else None
            if status and 500 <= status < 600 and i < len(backoffs):
                time.sleep(backoffs[i])
                continue
            # If we have cache, serve it; otherwise re-raise.
            if _s3_exists(data_path):
                return _s3_read_json(data_path)
            raise


###################################################################
# HELPERS AND BOX SCORE
###################################################################

# Import the base url for the boxscore endpoint
BOX_BASE = "https://api-web.nhle.com/v1/gamecenter/{game_id}/boxscore"

# Set the s3 paths for the json and the meta json for boxscore
def _s3_path_box(season: int, game_id: int) -> str:
    # Data body: s3://hockey-decoded/live-data-cache/game-center/SEASON/GAMEID_box.json
    return f"s3://{S3_BUCKET}/{S3_PREFIX}/{season}/{game_id}_box.json"

def _s3_meta_path_box(season: int, game_id: int) -> str:
    # Meta alongside body: s3://.../SEASON/GAMEID_box.meta.json
    return f"s3://{S3_BUCKET}/{S3_PREFIX}/{season}/{game_id}_box.meta.json" 

def fetch_game_box(
    game_id: int,
    season: int,
    ttl_seconds: int = 5,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Return the boxscore JSON for a game, with S3-backed caching:
      - S3 TTL check to avoid bursty calls
      - Conditional GET (If-None-Match / If-Modified-Since) via S3-stored meta
      - Retry on timeouts, with cached fallback if available
    """
    data_path = _s3_path_box(season, game_id)
    meta_path = _s3_meta_path_box(season, game_id)

    # 1) TTL short-circuit: if recent S3 object exists and not forcing, use it
    if not force_refresh:
        age = _s3_age_seconds(data_path)
        if age is not None and age < ttl_seconds:
            return _s3_read_json(data_path)

    # 2) Build conditional headers from S3 meta (unless force refresh)
    headers: Dict[str, str] = {}
    meta = {} if force_refresh else _load_meta_s3(meta_path)
    etag = meta.get("etag")
    last_modified = meta.get("last_modified")
    if etag:
        headers["If-None-Match"] = etag
    if last_modified:
        headers["If-Modified-Since"] = last_modified

    url = BOX_BASE.format(game_id=game_id)

    # 3) Make the request with light retry logic for transient failures
    backoffs = [1.5, 3.0]  # two retries
    attempts = len(backoffs) + 1
    for i in range(attempts):
        try:
            with httpx.Client(timeout=(5, 15)) as client:
                r = client.get(url, headers=headers)

            # 304 Not Modified → return cached S3 if present
            if r.status_code == 304:
                if _s3_exists(data_path):
                    return _s3_read_json(data_path)
                else:
                    # Rare: server says "unchanged" but we don't have a cache.
                    # Do an unconditional GET (no headers) once.
                    with httpx.Client(timeout=(5, 15)) as client:
                        fresh = client.get(url)
                    fresh.raise_for_status()
                    body = fresh.json()
                    _s3_write_json(data_path, body)
                    _save_meta_s3(
                        meta_path,
                        fresh.headers.get("ETag") or fresh.headers.get("Etag"),
                        fresh.headers.get("Last-Modified"),
                    )
                    return body

            # 200 OK (or other 2xx) → write body + meta to S3
            r.raise_for_status()
            body = r.json()
            _s3_write_json(data_path, body)
            _save_meta_s3(
                meta_path,
                r.headers.get("ETag") or r.headers.get("Etag"),
                r.headers.get("Last-Modified"),
            )
            return body

        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            # Retry timeouts with backoff; if we exhaust retries, fall back to cache if possible
            if i < len(backoffs):
                time.sleep(backoffs[i])
                continue
            if _s3_exists(data_path):
                return _s3_read_json(data_path)
            raise

        except httpx.HTTPStatusError as e:
            # For 5xx, try retries; for 4xx (other than 304) don't.
            status = e.response.status_code if e.response is not None else None
            if status and 500 <= status < 600 and i < len(backoffs):
                time.sleep(backoffs[i])
                continue
            # If we have cache, serve it; otherwise re-raise.
            if _s3_exists(data_path):
                return _s3_read_json(data_path)
            raise

# =========================
# MoneyPuck xG CSV Caching
# =========================

MP_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/118.0.0.0 Safari/537.36"),
    "Referer": "https://moneypuck.com/",
}
MP_TIMEOUT = (5, 20)  # connect, read

def _empty_player_df() -> pd.DataFrame:
    # Keep common columns you rely on; you can add others as needed
    cols = [
        "playerName", "playerId", "team", "position", "situation",
        "I_F_xGoals", "I_F_flurryAdjustedxGoals", "I_F_scoreVenueAdjustedxGoals",
        "I_F_flurryScoreVenueAdjustedxGoals",
    ]
    return pd.DataFrame({c: pd.Series(dtype="object") for c in cols})

def _empty_game_df() -> pd.DataFrame:
    cols = ["homeTeamAbbrev", "awayTeamAbbrev", "homeTeam", "awayTeam", "gameId"]
    return pd.DataFrame({c: pd.Series(dtype="object") for c in cols})

def _mp_season_folder(game_id: int) -> str:
    y = int(str(game_id)[:4])
    return f"{y}{y+1}"

def _mp_player_url(game_id: int) -> str:
    # Per-game *player* CSV (live)
    return f"https://moneypuck.com/moneypuck/playerData/games/{_mp_season_folder(game_id)}/{game_id}.csv"

def _mp_game_url(game_id: int) -> str:
    # Per-game *team/game* CSV (live; has home/away metadata)
    return f"https://moneypuck.com/moneypuck/gameData/{_mp_season_folder(game_id)}/{game_id}.csv"

# ---- S3 paths (CSV + meta) ----
def _s3_mp_dir(season: int) -> str:
    return f"s3://{S3_BUCKET}/{S3_PREFIX}/{season}/moneypuck"

def _s3_mp_player_path(season: int, game_id: int) -> str:
    return f"{_s3_mp_dir(season)}/{game_id}_player.csv"

def _s3_mp_player_meta(season: int, game_id: int) -> str:
    return f"{_s3_mp_dir(season)}/{game_id}_player.meta.json"

def _s3_mp_game_path(season: int, game_id: int) -> str:
    return f"{_s3_mp_dir(season)}/{game_id}_game.csv"

def _s3_mp_game_meta(season: int, game_id: int) -> str:
    return f"{_s3_mp_dir(season)}/{game_id}_game.meta.json"

def _s3_read_text(path: str) -> str:
    with fs.open(path, "rb") as f:
        return f.read().decode("utf-8")

def _s3_write_text(path: str, text: str) -> None:
    data = text.encode("utf-8")
    # ensure parent "directory" exists (no-op if already there)
    fs.makedirs(path.rsplit("/", 1)[0], exist_ok=True)
    with fs.open(path, "wb") as f:
        f.write(data)

def _http_get_with_conditionals(url: str, headers: Dict[str, str]) -> httpx.Response:
    with httpx.Client(timeout=MP_TIMEOUT) as client:
        return client.get(url, headers=headers)

def _fetch_csv_with_cache(
    url: str,
    csv_path: str,
    meta_path: str,
    ttl_seconds: int,
    force_refresh: bool,
    extra_headers: Optional[Dict[str, str]] = None,
    on_not_started: str = "empty",  # "empty" | "none" | "raise"
) -> Optional[str]:
    """
    Core fetcher for CSV with S3 caching + conditional GET.
    Returns CSV text, or None if on_not_started == "none" and the game hasn't started.
    """
    # TTL short-circuit
    if not force_refresh:
        age = _s3_age_seconds(csv_path)
        if age is not None and age < ttl_seconds:
            text = _s3_read_text(csv_path)
            return text if text.strip() else (None if on_not_started == "none" else "")

    # Build conditional headers
    headers: Dict[str, str] = dict(MP_HEADERS)
    if extra_headers:
        headers.update(extra_headers)
    if not force_refresh:
        meta = _load_meta_s3(meta_path)
        if (etag := meta.get("etag")):
            headers["If-None-Match"] = etag
        if (lm := meta.get("last_modified")):
            headers["If-Modified-Since"] = lm

    backoffs = [1.5, 3.0]
    attempts = len(backoffs) + 1
    for i in range(attempts):
        try:
            r = _http_get_with_conditionals(url, headers)

            # 304: use cache
            if r.status_code == 304 and _s3_exists(csv_path):
                text = _s3_read_text(csv_path)
                return text if text.strip() else (None if on_not_started == "none" else "")

            # 404: game not started yet (don’t cache)
            if r.status_code == 404:
                if on_not_started == "raise":
                    r.raise_for_status()
                return None if on_not_started == "none" else ""

            r.raise_for_status()
            text = r.text

            # MoneyPuck sometimes serves HTML for errors; guard that
            if not text.strip() or text.lstrip().startswith("<!DOCTYPE html"):
                # treat as not-started; don't cache
                return None if on_not_started == "none" else ""

            _s3_write_text(csv_path, text)
            _save_meta_s3(
                meta_path,
                r.headers.get("ETag") or r.headers.get("Etag"),
                r.headers.get("Last-Modified"),
            )
            return text

        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            if i < len(backoffs):
                time.sleep(backoffs[i]); continue
            if _s3_exists(csv_path):
                text = _s3_read_text(csv_path)
                return text if text.strip() else (None if on_not_started == "none" else "")
            # no cache; bubble up
            raise

        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else None
            if status and 500 <= status < 600 and i < len(backoffs):
                time.sleep(backoffs[i]); continue
            if _s3_exists(csv_path):
                text = _s3_read_text(csv_path)
                return text if text.strip() else (None if on_not_started == "none" else "")
            if status == 404 and on_not_started != "raise":
                return None if on_not_started == "none" else ""
            raise

# ---- Public APIs ----

def fetch_moneypuck_player_xg_csv(
    game_id: int,
    season: int,
    ttl_seconds: int = 30,
    force_refresh: bool = False,
    return_df: bool = True,
    on_not_started: str = "empty",   # "empty" | "none" | "raise"
) -> pd.DataFrame | str | None:
    url = _mp_player_url(game_id)
    csv_path = _s3_mp_player_path(season, game_id)
    meta_path = _s3_mp_player_meta(season, game_id)
    csv_text = _fetch_csv_with_cache(
        url, csv_path, meta_path, ttl_seconds, force_refresh, on_not_started=on_not_started
    )

    if not return_df:
        return csv_text  # may be "" or None per on_not_started

    if not csv_text:
        return _empty_player_df()

    try:
        df = pd.read_csv(io.StringIO(csv_text))
    except Exception:
        # Malformed or HTML slipped through — treat as empty
        return _empty_player_df()
    return df


def fetch_moneypuck_game_csv(
    game_id: int,
    season: int,
    ttl_seconds: int = 60,
    force_refresh: bool = False,
    return_df: bool = True,
    on_not_started: str = "empty",   # "empty" | "none" | "raise"
) -> pd.DataFrame | str | None:
    url = _mp_game_url(game_id)
    csv_path = _s3_mp_game_path(season, game_id)
    meta_path = _s3_mp_game_meta(season, game_id)
    csv_text = _fetch_csv_with_cache(
        url, csv_path, meta_path, ttl_seconds, force_refresh, on_not_started=on_not_started
    )

    if not return_df:
        return csv_text  # may be "" or None per on_not_started

    if not csv_text:
        return _empty_game_df()

    try:
        df = pd.read_csv(io.StringIO(csv_text))
    except Exception:
        return _empty_game_df()
    return df


# =========================
# Shiftcharts (per-game)
# =========================

SHIFT_BASE = "https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={game_id}"

def _s3_path_shifts(season: int, game_id: int) -> str:
    # s3://hockey-decoded/live-data-cache/game-center/SEASON/GAMEID_shifts.json
    return f"s3://{S3_BUCKET}/{S3_PREFIX}/{season}/{game_id}_shifts.json"

def _s3_meta_path_shifts(season: int, game_id: int) -> str:
    return f"s3://{S3_BUCKET}/{S3_PREFIX}/{season}/{game_id}_shifts.meta.json"

def fetch_game_shifts(
    game_id: int,
    season: int,
    ttl_seconds: int = 15,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Return the raw shiftcharts JSON for a game with S3-backed caching.
    Shape (from NHL stats REST) is a dict like:
      {"data":[{...shift row...}, ...], "total": N, ...}
    """
    data_path = _s3_path_shifts(season, game_id)
    meta_path = _s3_meta_path_shifts(season, game_id)

    # TTL short-circuit
    if not force_refresh:
        age = _s3_age_seconds(data_path)
        if age is not None and age < ttl_seconds:
            return _s3_read_json(data_path)

    # Conditional headers from S3 meta (If-None-Match / If-Modified-Since)
    headers: Dict[str, str] = {
        "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/118.0.0.0 Safari/537.36"),
        "Referer": "https://www.nhl.com/",
        "Accept": "application/json",
    }
    if not force_refresh:
        meta = _load_meta_s3(meta_path)
        if (etag := meta.get("etag")):
            headers["If-None-Match"] = etag
        if (lm := meta.get("last_modified")):
            headers["If-Modified-Since"] = lm

    url = SHIFT_BASE.format(game_id=game_id)
    backoffs = [1.5, 3.0]
    attempts = len(backoffs) + 1

    for i in range(attempts):
        try:
            with httpx.Client(timeout=(5, 20)) as client:
                r = client.get(url, headers=headers)

            # 304 -> serve cache
            if r.status_code == 304 and _s3_exists(data_path):
                return _s3_read_json(data_path)

            r.raise_for_status()
            body = r.json()

            # Guard: some upstream hiccups can return HTML or empty bodies
            if not isinstance(body, dict) or "data" not in body:
                # If we have cache, return it; else persist minimal stub
                if _s3_exists(data_path):
                    return _s3_read_json(data_path)
                body = {"data": [], "total": 0}

            _s3_write_json(data_path, body)
            _save_meta_s3(
                meta_path,
                r.headers.get("ETag") or r.headers.get("Etag"),
                r.headers.get("Last-Modified"),
            )
            return body

        except (httpx.ReadTimeout, httpx.ConnectTimeout):
            if i < len(backoffs):
                time.sleep(backoffs[i]); continue
            if _s3_exists(data_path):
                return _s3_read_json(data_path)
            raise

        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response is not None else None
            # Retry 5xx; don't for most 4xx
            if status and 500 <= status < 600 and i < len(backoffs):
                time.sleep(backoffs[i]); continue
            if _s3_exists(data_path):
                return _s3_read_json(data_path)
            raise
