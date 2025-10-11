# app/nhl/parsers/depth.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple

# ---------- mirror sogs.py helpers ----------
def _is_sog(play: dict) -> bool:
    k = (play.get("typeDescKey") or "").lower()
    return k in ("shot-on-goal", "goal")

def _team_id_for_play(play: dict) -> int | None:
    det = play.get("details") or {}
    if "eventOwnerTeamId" in det and det["eventOwnerTeamId"] is not None:
        return int(det["eventOwnerTeamId"])
    t = play.get("team") or {}
    tid = t.get("id")
    return int(tid) if tid is not None else None

def _team_abbrev_for_play(play: dict, team_lookup: Dict[int, str]) -> str | None:
    det = play.get("details") or {}
    if det.get("eventOwnerTeamAbbrev"):
        return det["eventOwnerTeamAbbrev"]
    tid = _team_id_for_play(play)
    if tid is not None and tid in team_lookup:
        return team_lookup[tid]
    t = play.get("team") or {}
    return t.get("abbrev") or t.get("triCode")

def _build_team_lookup(pbp: dict) -> Dict[int, str]:
    lookup = {}
    for side in ("homeTeam", "awayTeam"):
        t = pbp.get(side) or {}
        if "id" in t and "abbrev" in t:
            lookup[int(t["id"])] = t["abbrev"]
    return lookup

def _home_away_meta(pbp: dict) -> Tuple[dict, dict]:
    return (pbp.get("homeTeam") or {}), (pbp.get("awayTeam") or {})

# ---------- math ----------
def _gini(values: List[int]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    s = sum(values)
    if s == 0:
        return 0.0
    diffsum = 0
    for i in range(n):
        vi = values[i]
        for j in range(n):
            diffsum += abs(vi - values[j])
    mean = s / n
    return diffsum / (2.0 * n * n * mean)

def _safe_5050(home_abbrev: str | None, away_abbrev: str | None) -> Dict[str, Any]:
    return {
        "no_shots": True,
        "home": {"team": home_abbrev, "total_shots": 0, "ineq": None, "depth": None},
        "away": {"team": away_abbrev, "total_shots": 0, "ineq": None, "depth": None},
        "depth_share": {"home_pct": 50.0, "away_pct": 50.0},
        "shots": {"home": {}, "away": {}},
    }

# ---------- main ----------
def shot_depth_from_pbp(pbp: Dict[str, Any], roster_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    home_meta, away_meta = _home_away_meta(pbp)
    home_abbrev = home_meta.get("abbrev") or home_meta.get("triCode")
    away_abbrev = away_meta.get("abbrev") or away_meta.get("triCode")
    if not home_abbrev or not away_abbrev:
        return _safe_5050(home_abbrev, away_abbrev)

    team_lookup = _build_team_lookup(pbp)

    # Count by shooter for SOG-only (same as sogs.py)
    shots_home: Dict[str, int] = {}
    shots_away: Dict[str, int] = {}

    events = pbp.get("plays") or []
    for p in events:
        if not isinstance(p, dict):
            continue
        if not _is_sog(p):
            continue

        # skip shootout like sogs.py
        pd = p.get("periodDescriptor") or {}
        if (pd.get("periodType") or "").upper() == "SO":
            continue

        team_abbr = _team_abbrev_for_play(p, team_lookup)
        if not team_abbr:
            # fallback to teamId match if abbrev resolution failed
            tid = _team_id_for_play(p)
            if tid is None:
                continue
            if int(away_meta.get("id")) == tid:
                team_abbr = away_abbrev
            elif int(home_meta.get("id")) == tid:
                team_abbr = home_abbrev
            else:
                continue

        det = p.get("details") or {}
        pid = det.get("shootingPlayerId") or det.get("scoringPlayerId")
        if pid is None:
            continue
        try:
            pid = str(int(pid))
        except Exception:
            pid = str(pid)

        if team_abbr == home_abbrev:
            shots_home[pid] = shots_home.get(pid, 0) + 1
        elif team_abbr == away_abbrev:
            shots_away[pid] = shots_away.get(pid, 0) + 1
        # else: ignore stray/neutral entries

    # Back-fill zeros from roster so Gini sees full roster distribution
    for r in (roster_rows or []):
        ab = r.get("teamAbbrev")
        pid = r.get("playerId")
        if pid is None or ab not in (home_abbrev, away_abbrev):
            continue
        try:
            pid = str(int(pid))
        except Exception:
            pid = str(pid)
        if ab == home_abbrev:
            shots_home.setdefault(pid, 0)
        else:
            shots_away.setdefault(pid, 0)

    home_total = sum(shots_home.values())
    away_total = sum(shots_away.values())
    if (home_total + away_total) == 0:
        return _safe_5050(home_abbrev, away_abbrev)

    def _team_stats(d: Dict[str, int]) -> Dict[str, float]:
        vals = list(d.values())
        g = _gini(vals)
        return {"ineq": g, "depth": 1.0 - g}

    h_stats = _team_stats(shots_home)
    a_stats = _team_stats(shots_away)
    h, a = h_stats["depth"], a_stats["depth"]
    denom = (h + a) if (h + a) > 0 else 1.0
    home_pct = round(100.0 * (h / denom), 1)
    away_pct = round(100.0 - home_pct, 1)

    return {
        "no_shots": False,
        "home": {"team": home_abbrev, "total_shots": home_total, **h_stats},
        "away": {"team": away_abbrev, "total_shots": away_total, **a_stats},
        "depth_share": {"home_pct": home_pct, "away_pct": away_pct},
        "shots": {"home": shots_home, "away": shots_away},
    }


def _is_cf_shot(play: dict) -> bool:
    k = (play.get("typeDescKey") or "").lower()
    return k in ("shot-on-goal", "goal", "blocked-shot", "missed-shot")

def cf_depth_from_pbp(pbp: Dict[str, Any], roster_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    home_meta, away_meta = _home_away_meta(pbp)
    home_abbrev = home_meta.get("abbrev") or home_meta.get("triCode")
    away_abbrev = away_meta.get("abbrev") or away_meta.get("triCode")
    if not home_abbrev or not away_abbrev:
        return _safe_5050(home_abbrev, away_abbrev)

    team_lookup = _build_team_lookup(pbp)

    # Count by shooter for SOG-only (same as sogs.py)
    cf_home: Dict[str, int] = {}
    cf_away: Dict[str, int] = {}

    events = pbp.get("plays") or []
    for p in events:
        if not isinstance(p, dict):
            continue
        if not _is_cf_shot(p):
            continue

        # skip shootout like sogs.py
        pd = p.get("periodDescriptor") or {}
        if (pd.get("periodType") or "").upper() == "SO":
            continue

        team_abbr = _team_abbrev_for_play(p, team_lookup)
        if not team_abbr:
            # fallback to teamId match if abbrev resolution failed
            tid = _team_id_for_play(p)
            if tid is None:
                continue
            if int(away_meta.get("id")) == tid:
                team_abbr = away_abbrev
            elif int(home_meta.get("id")) == tid:
                team_abbr = home_abbrev
            else:
                continue

        det = p.get("details") or {}
        pid = det.get("shootingPlayerId") or det.get("scoringPlayerId")
        if pid is None:
            continue
        try:
            pid = str(int(pid))
        except Exception:
            pid = str(pid)

        if team_abbr == home_abbrev:
            cf_home[pid] = cf_home.get(pid, 0) + 1
        elif team_abbr == away_abbrev:
            cf_away[pid] = cf_away.get(pid, 0) + 1
        # else: ignore stray/neutral entries

    # Back-fill zeros from roster so Gini sees full roster distribution
    for r in (roster_rows or []):
        ab = r.get("teamAbbrev")
        pid = r.get("playerId")
        if pid is None or ab not in (home_abbrev, away_abbrev):
            continue
        try:
            pid = str(int(pid))
        except Exception:
            pid = str(pid)
        if ab == home_abbrev:
            cf_home.setdefault(pid, 0)
        else:
            cf_away.setdefault(pid, 0)

    home_total = sum(cf_home.values())
    away_total = sum(cf_away.values())
    if (home_total + away_total) == 0:
        return _safe_5050(home_abbrev, away_abbrev)

    def _team_stats(d: Dict[str, int]) -> Dict[str, float]:
        vals = list(d.values())
        g = _gini(vals)
        return {"ineq": g, "depth": 1.0 - g}

    h_stats = _team_stats(cf_home)
    a_stats = _team_stats(cf_away)
    h, a = h_stats["depth"], a_stats["depth"]
    denom = (h + a) if (h + a) > 0 else 1.0
    home_pct = round(100.0 * (h / denom), 1)
    away_pct = round(100.0 - home_pct, 1)

    return {
        "no_shots": False,
        "cf_home": {"team": home_abbrev, "total_shots": home_total, **h_stats},
        "cf_away": {"team": away_abbrev, "total_shots": away_total, **a_stats},
        "cf_depth_share": {"home_pct": home_pct, "away_pct": away_pct},
        "cf": {"cf_home": cf_home, "cf_away": cf_away},
    }
