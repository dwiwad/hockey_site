"""
This parses goals, period, and clock from the pbp data

Created on Sat Sep 13 13:46:54 2025

@author: dwiwad
"""

from __future__ import annotations

###################################################################
# HELPERS
###################################################################

# I don't think I'll need any helpers here. Everything I need for the
# scoreboard should exist in the toplevel pbp data, which is already
# pulled in service.py; so I can rely on pbp.get for everything.

###################################################################
# GET THE SCOREBOARD DATA
###################################################################

# Okay we need some stuff to make the scoreboard function work. 
# We need to be able to tell if the game is live or not; pbp['gameState'] FUT, LIVE, FINAL
# If gameState = FUT then 0-0 score and "Game not Started"
# This will determine how we display the period and time. If the game is final just display "Final" or "Game Ended"
# For the of the period, display, if the game is intermission clock['inIntermission] true/false
# So if inIntermission = False display period number, if inIntermission = True display "Intermission"
# Maybe some way to determine first or second? If displayPeriod = 1 and inIntermission = True then "1st Intermission"
# if displayPeriod = 2 and inIntermission = True then "2nd Intermission"

# The scores we can just pull straight; check sogs.py for how I've hacked it right now.

def scoreboard(pbp: dict) -> dict:
    """Return simple labels + SOG counts for away/home teams"""
    away = pbp.get("awayTeam", {}) or {}
    home = pbp.get("homeTeam", {}) or {}
    
    away_score = pbp.get()

    # Labels and abbreviations
    away_score = (away.get("score") or {}) or "0"
    home_score = (home.get("score") or {}) or "0"

    # Build lookup once
    team_lookup = build_team_lookup(pbp)

    # Also keep numeric IDs for a robust fallback comparison
    away_id = int(away.get("id")) if away.get("id") is not None else None
    home_id = int(home.get("id")) if home.get("id") is not None else None


    return {
        "away_score": away_score,
        "home_score": home_score,
    }