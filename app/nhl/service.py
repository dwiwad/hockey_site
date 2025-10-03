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
