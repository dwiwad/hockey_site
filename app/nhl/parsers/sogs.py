"""
This parses SOGs from the pbp data

Created on Sat Sep 13 13:46:54 2025

@author: dwiwad
"""

from __future__ import annotations

###################################################################
# HELPERS
###################################################################

# function to identify and pull SOGs
def _is_sog(play: dict) -> bool:
    k = (play.get("typeDescKey") or "").lower()
    return k in ("shot-on-goal", "goal")

# Build id -> abbrev lookup from the game object
def build_team_lookup(pbp: dict) -> dict[int, str]:
    lookup = {}
    for side in ("homeTeam", "awayTeam"):
        t = pbp.get(side) or {}
        if "id" in t and "abbrev" in t:
            lookup[int(t["id"])] = t["abbrev"]
    return lookup

# Optionally: quick helper to grab team id from a play
def _team_id_for_play(play: dict) -> int | None:
    det = play.get("details") or {}
    if "eventOwnerTeamId" in det and det["eventOwnerTeamId"] is not None:
        return int(det["eventOwnerTeamId"])
    t = play.get("team") or {}
    tid = t.get("id")
    return int(tid) if tid is not None else None

# Get team abbrev for a play (uses lookup when no abbrev on the play)
def _team_abbrev_for_play(play: dict, team_lookup: dict[int, str]) -> str | None:
    det = play.get("details") or {}

    # Best case: play already carries the abbrev
    if "eventOwnerTeamAbbrev" in det and det["eventOwnerTeamAbbrev"]:
        return det["eventOwnerTeamAbbrev"]

    # Otherwise: map the id to abbrev
    tid = _team_id_for_play(play)
    if tid is not None:
        abbr = team_lookup.get(tid)
        if abbr:
            return abbr

    # Last resort: look at the nested team object on the play
    t = play.get("team") or {}
    return t.get("abbrev") or t.get("triCode")

###################################################################
# GET THE SOGS DATA
###################################################################

# Count SOGs by team
def sog_by_team(pbp: dict) -> dict:
    """Return simple labels + SOG counts for away/home teams"""
    away = pbp.get("awayTeam", {}) or {}
    home = pbp.get("homeTeam", {}) or {}

    # Labels and abbreviations
    away_place = (away.get("placeName") or {}).get("default") or ""
    home_place = (home.get("placeName") or {}).get("default") or ""
    away_name  = (away.get("commonName") or {}).get("default") or away.get("abbrev") or "Away"
    home_name  = (home.get("commonName") or {}).get("default") or home.get("abbrev") or "Home"
    away_abbrev = away.get("abbrev") or away.get("triCode") or ""
    home_abbrev = home.get("abbrev") or home.get("triCode") or ""

    # Build lookup once
    team_lookup = build_team_lookup(pbp)

    # Also keep numeric IDs for a robust fallback comparison
    away_id = int(away.get("id")) if away.get("id") is not None else None
    home_id = int(home.get("id")) if home.get("id") is not None else None

    a = h = 0
    for p in pbp.get("plays", []):
        if not _is_sog(p):
            continue
        
        # skip shootout shots - this bug was a bitch.
        pd = p.get("periodDescriptor") or {}
        if (pd.get("periodType") or "").upper() == "SO":
            continue

        # Try abbrev path first
        team_abbr = _team_abbrev_for_play(p, team_lookup)
        if team_abbr:
            if team_abbr == away_abbrev:
                a += 1
                continue
            if team_abbr == home_abbrev:
                h += 1
                continue

        # Fallback: compare team IDs if abbrev didn’t match
        tid = _team_id_for_play(p)
        if tid is not None:
            if away_id is not None and tid == away_id:
                a += 1
            elif home_id is not None and tid == home_id:
                h += 1
    
    total = a + h

    if total > 0:
        away_share = round((a / total), 2)
        home_share = round((1 - away_share), 2)
        has_shots  = True
    else:
        away_share = 0.5
        home_share = 0.5
        has_shots  = False

    return {
        "away_place": away_place,
        "home_place": home_place,
        "away_label": away_name,
        "home_label": home_name,
        "away_abbrev": away_abbrev,
        "home_abbrev": home_abbrev,
        "away_sog": a,
        "home_sog": h,
        "total_shots": total,
        "away_share": away_share,
        "home_share": home_share,
        "has_shots": has_shots
    }
