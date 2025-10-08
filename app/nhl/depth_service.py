# services/depth_service.py
from __future__ import annotations
from typing import Dict, Any, List
from app.nhl.service import fetch_game_pbp          # you already have this
from app.nhl.parsers.rosters import roster_by_team          # your roster.py entry point
from parsers.depth import compute_game_shot_depth    # from depth.py

def get_shot_depth_payload(game_id: str) -> Dict[str, Any]:
    """
    Returns a payload ready for your template:
    {
      no_shots: bool,
      home: {team, total_shots, ineq, depth},
      away: {team, total_shots, ineq, depth},
      depth_share: {home_pct, away_pct},
      shots: {"home": {pid: n}, "away": {pid: n}}
    }
    """
    pbp = fetch_game_pbp(game_id)  # raw gamecenter JSON (or your normalized dict)

    rosters = roster_by_team(game_id)
    # Expecting something like:
    # rosters = {
    #   "home": {"team": "EDM", "player_ids": ["8478402","8476456", ...]},
    #   "away": {"team": "FLA", "player_ids": [...]}
    # }

    home_abbrev = rosters["home"]["team"]
    away_abbrev = rosters["away"]["team"]
    home_ids: List[str] = [str(pid) for pid in rosters["home"]["player_ids"]]
    away_ids: List[str] = [str(pid) for pid in rosters["away"]["player_ids"]]

    return compute_game_shot_depth(
        pbp=pbp,
        home_abbrev=home_abbrev,
        away_abbrev=away_abbrev,
        roster_home_ids=home_ids,
        roster_away_ids=away_ids,
    )
