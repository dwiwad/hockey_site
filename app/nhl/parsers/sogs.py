"""
This will eventually be my SOGs parser, but right now it is my
standup test

Created on Sat Sep 13 13:46:54 2025

@author: dwiwad
"""

from __future__ import annotations

# function to identify and pulls sogs
def _is_sog(play: dict) -> bool:
    k = (play.get("typeDescKey") or "").lower()
    return k in ("shot-on-goal", "goal")

# Function to get the team abbreviations
def _team_abbrev_for_play(play: dict) -> str | None:
    det = play.get("details") or {}
    team = det.get("eventOwnerTeamAbbrev")
    if team:
        return team
    t = play.get("team") or {}
    return t.get("abbrev") or t.get("triCode")

# function that counts sogs by team
def sog_by_team(pbp: dict) -> dict:
    """Return simple labels + sog counts for away/home teams"""
    away = pbp.get("awayTeam", {}) or {}
    home = pbp.get("homeTeam", {}) or {}
    
    away_name = (away.get("name") or {}).get("default") or away.get("abbrev") or "Away"
    home_name = (home.get("name") or {}).get("default") or home.get("abbrev") or "Home" 
    away_abbrev = away.get("abbrev") or away.get("triCode") or ""
    home_abbrev = home.get("abbrev") or home.get("triCode") or ""
    
    a = h = 0
    for p in pbp.get("plays", []):
        if not _is_sog(p):
            continue
        team = _team_abbrev_for_play(p)
        if team == away_abbrev:
            a += 1
        elif team == home_abbrev:
            h += 1
            
    return {
        "away_label": away_name,
        "home_label": home_name,
        "away_sog": a,
        "home_sog": h
        }