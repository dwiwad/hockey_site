"""
This parses Rosters from the pbp data

Created on Sat Sep 13 13:46:54 2025

@author: dwiwad
"""

from __future__ import annotations

###################################################################
# HELPERS
###################################################################

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
# GET THE ROSTERS DATA
###################################################################

def roster_by_team(pbp: dict) -> list[dict]:
    team_lookup = build_team_lookup(pbp)

    # Accept either a flat rosterSpots list or split under home/away
    roster = (
        pbp.get("rosterSpots")
        or (pbp.get("homeTeam", {}).get("rosterSpots", []) +
            pbp.get("awayTeam", {}).get("rosterSpots", []))
        or []
    )

    def get_path(d: dict, path: list[str]):
        cur = d
        for k in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur

    rows = []
    for spot in roster:
        # teamId → teamAbbrev via your lookup, with sensible fallbacks
        raw_team_id = get_path(spot, ["teamId"]) or get_path(spot, ["team", "id"])
        try:
            team_id = int(raw_team_id) if raw_team_id is not None else None
        except (TypeError, ValueError):
            team_id = None

        team_abbrev = (
            (team_lookup.get(team_id) if team_id is not None else None)
            or get_path(spot, ["team", "abbrev"])
            or get_path(spot, ["team", "triCode"])
        )

        player_id = get_path(spot, ["playerId"]) or get_path(spot, ["player", "id"])
        first = (get_path(spot, ["firstName", "default"])
                 or get_path(spot, ["player", "firstName", "default"]))
        last = (get_path(spot, ["lastName", "default"])
                or get_path(spot, ["player", "lastName", "default"]))

        rows.append({
            "teamAbbrev": team_abbrev,
            "playerId": player_id,
            "firstName": first,
            "lastName": last,
        })

    return rows