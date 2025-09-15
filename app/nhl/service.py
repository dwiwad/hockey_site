"""
This is going to be my data librarian for the play-by-play data. Fetch the 
play-by-play, cache it, allow it to be parsed later for metrics.

Created on Sat Sep 13 09:16:18 2025

@author: dwiwad
"""
# The API endpoint that has game play-by-play is:
# https://api-web.nhle.com/v1/gamecenter/GAMEIDHERE/play-by-play

from __future__ import annotations
import json, time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import httpx

# Import the base url for the play-by-play endpoint
BASE = "https://api-web.nhle.com/v1/gamecenter/{game_id}/play-by-play"
# Set the cache directory for where the data will be stored
CACHE_DIR = Path("data/cache/gamecenter")
# Great this directory on the chance it does not exist
CACHE_DIR.mkdir(parents=True, exist_ok=True)

###################################################################
# HELPERS
###################################################################

# Function that directs where to store the pulled game files
def _paths(game_id: int, season: int) -> Tuple[Path, Path]:
    season_dir = CACHE_DIR / str(season)
    season_dir.mkdir(parents=True, exist_ok=True)   # <-- ensure folder exists
    data = season_dir / f"{game_id}.json"
    meta = season_dir / f"{game_id}.meta.json"
    return data, meta

# function that loads metadata or returns an empty dictionary
def _load_meta(meta_path: Path) -> Dict[str, Any]:
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    return {}

# Save the meta
def _save_meta(meta_path: Path, etag: Optional[str], last_modified: Optional[str]) -> None:
    meta = {}
    if etag: meta["etag"] = etag
    if last_modified: meta["last_modified"] = last_modified
    meta_path.write_text(json.dumps(meta))

    
###################################################################
# GET THE PLAY BY PLAY DATA
###################################################################

def fetch_game_pbp(game_id: int, season: int, ttl_seconds: int = 5) -> Dict[str, Any]:
    """
    Return the PBP JSON for a game, with:
      - disk caching
      - conditional GET (If-None-Match / If-Modified-Since)
      - a tiny TTL so we don't hammer the server if called rapidly
    """
    
    # Look for the cached game and meta data
    data_path, meta_path = _paths(game_id, season)
    headers = {}
    meta = _load_meta(meta_path)
    
    
    # If cache is very fresh, just reuse it to avoid bursty calls
    if data_path.exists():
        age = time.time() - data_path.stat().st_mtime
        if age < ttl_seconds:
            return json.loads(data_path.read_text())
    
    # Avoid the call if we already have cached data
    if etag := meta.get("etag"):
        headers["If-None-Match"] = etag
    if lm := meta.get("last_modified"):
        headers["If-Modified-Since"] = lm
    
    # Build the actual url and make the call
    url = BASE.format(game_id=game_id)
    with httpx.Client(timeout=15) as client:
        r = client.get(url, headers=headers)
        
        # check if nothing changed; use cache
        if r.status_code == 304 and data_path.exists():
            return json.loads(data_path.read_text())
        
        r.raise_for_status()
        body = r.json()
        
        # Save new data body + metadata
        data_path.write_text(json.dumps(body))
        _save_meta(
            meta_path,
            etag=r.headers.get("Etag"),
            last_modified=r.headers.get("Last-Modified"),
            )
        return body
    
    