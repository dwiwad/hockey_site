# app/nhl/parsers/depth.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd

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
        "home": {"team": home_abbrev, "total_shots": 0, "ineq": 0.0, "depth": 0.0},
        "away": {"team": away_abbrev, "total_shots": 0, "ineq": 0.0, "depth": 0.0},
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

def _safe_cf_5050(home_abbrev: str | None, away_abbrev: str | None) -> Dict[str, Any]:
    return {
        "no_shots": True,
        "cf_home": {"team": home_abbrev, "total_shots": 0, "ineq": 0.0, "depth": 0.0},
        "cf_away": {"team": away_abbrev, "total_shots": 0, "ineq": 0.0, "depth": 0.0},
        "cf_depth_share": {"home_pct": 50.0, "away_pct": 50.0},
        "cf": {"cf_home": {}, "cf_away": {}},
    }

def cf_depth_from_pbp(pbp: Dict[str, Any], roster_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    home_meta, away_meta = _home_away_meta(pbp)
    home_abbrev = home_meta.get("abbrev") or home_meta.get("triCode")
    away_abbrev = away_meta.get("abbrev") or away_meta.get("triCode")
    if not home_abbrev or not away_abbrev:
        return _safe_cf_5050(home_abbrev, away_abbrev)

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
        return _safe_cf_5050(home_abbrev, away_abbrev)

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

# ---------- xG depth from MoneyPuck player CSV ----------
# Expects a pandas DataFrame like the one returned by fetch_moneypuck_player_xg_csv(..., return_df=True)
# Columns used: ["playerName", "playerId", "team", "position", "situation",
#                "I_F_xGoals", "I_F_flurryAdjustedxGoals",
#                "I_F_scoreVenueAdjustedxGoals", "I_F_flurryScoreVenueAdjustedxGoals"]

def _safe_xg_5050(home_abbrev: str | None, away_abbrev: str | None) -> Dict[str, Any]:
    return {
        "no_xg": True,
        "xg_home": {"team": home_abbrev, "total_xg": 0.0, "ineq": 0.0, "depth": 0.0},
        "xg_away": {"team": away_abbrev, "total_xg": 0.0, "ineq": 0.0, "depth": 0.0},
        "xg_depth_share": {"home_pct": 50.0, "away_pct": 50.0},
        "xg": {"xg_home": {}, "xg_away": {}},
    }

def _pick_xg_col(df, adjusted: bool) -> Optional[str]:
    if df is None or getattr(df, "empty", True):
        return None
    if adjusted:
        for c in ("I_F_flurryScoreVenueAdjustedxGoals",
                  "I_F_scoreVenueAdjustedxGoals",
                  "I_F_flurryAdjustedxGoals"):
            if c in df.columns:
                return c
    return "I_F_xGoals" if "I_F_xGoals" in df.columns else None

def _mp_team_matches(team_val: str, abbrev: str) -> bool:
    if not abbrev:
        return False
    return abbrev.lower() in str(team_val).lower()

def xgoal_depth_from_players(
    pbp: Dict[str, Any],
    roster_rows: List[Dict[str, Any]],
    xg_df,                         # pandas.DataFrame (MoneyPuck player CSV)
    situation: str = "all",        # "all" or "5on5"
    adjusted: bool = False,        # choose adjusted xG column if available
    include_goalies: bool = False  # default exclude goalies
) -> Dict[str, Any]:
    """
    Compute xG-based depth (1 - Gini) for home/away using MoneyPuck per-player xG.

    Returns a dict shaped like your other depth payloads, using 'xg_*' keys:
      {
        "no_xg": bool,
        "xg_home": { team, total_xg, ineq, depth },
        "xg_away": { ... },
        "xg_depth_share": { home_pct, away_pct },
        "xg": { "xg_home": {pid: xg}, "xg_away": {pid: xg} }
      }
    """
    home_meta, away_meta = _home_away_meta(pbp)
    home_abbrev = home_meta.get("abbrev") or home_meta.get("triCode")
    away_abbrev = away_meta.get("abbrev") or away_meta.get("triCode")
    if not home_abbrev or not away_abbrev:
        return _safe_xg_5050(home_abbrev, away_abbrev)

    # Guard: no data yet (pregame) or missing expected columns
    if xg_df is None or getattr(xg_df, "empty", True):
        return _safe_xg_5050(home_abbrev, away_abbrev)
    xg_col = _pick_xg_col(xg_df, adjusted=adjusted)
    if xg_col is None or "situation" not in xg_df.columns or "position" not in xg_df.columns:
        return _safe_xg_5050(home_abbrev, away_abbrev)

    # Filter by situation & skater positions
    df = xg_df.copy()
    df = df[df["situation"].str.lower() == str(situation).lower()]
    if not include_goalies:
        df = df[df["position"].isin(["C", "L", "R", "D"])]
    else:
        df = df[df["position"].isin(["C", "L", "R", "D", "G"])]

    if df.empty:
        return _safe_xg_5050(home_abbrev, away_abbrev)

    # Clean numeric xG
    df[xg_col] = pd.to_numeric(df[xg_col], errors="coerce").fillna(0.0)

    # Split by home/away using resilient substring match (e.g., "EDM" in "Edmonton Oilers")
    home_mask = df["team"].apply(lambda t: _mp_team_matches(t, home_abbrev))
    away_mask = df["team"].apply(lambda t: _mp_team_matches(t, away_abbrev))

    home_df = df[home_mask]
    away_df = df[away_mask]

    # Fallback: if both empty (team strings differ), pick top-2 team labels in df
    if home_df.empty and away_df.empty and not df["team"].empty:
        top_two = df["team"].value_counts().index[:2].tolist()
        if len(top_two) == 2:
            home_df = df[df["team"] == top_two[0]]
            away_df = df[df["team"] == top_two[1]]

    # Aggregate xG per playerId
    def _per_player_xg(dsub):
        out: Dict[str, float] = {}
        for _, row in dsub.iterrows():
            pid = row.get("playerId")
            try:
                pid = str(int(pid))
            except Exception:
                pid = str(pid)
            out[pid] = out.get(pid, 0.0) + float(row[xg_col])
        return out

    xg_home: Dict[str, float] = _per_player_xg(home_df)
    xg_away: Dict[str, float] = _per_player_xg(away_df)

    # Back-fill zeros from roster so Gini sees the full roster distribution (skaters by default)
    for r in (roster_rows or []):
        ab = r.get("teamAbbrev")
        pos = (r.get("position") or "").upper()
        if not include_goalies and pos == "G":
            continue
        pid = r.get("playerId")
        if pid is None or ab not in (home_abbrev, away_abbrev):
            continue
        try:
            pid = str(int(pid))
        except Exception:
            pid = str(pid)
        if ab == home_abbrev:
            xg_home.setdefault(pid, 0.0)
        else:
            xg_away.setdefault(pid, 0.0)

    home_total = sum(xg_home.values())
    away_total = sum(xg_away.values())
    if (home_total + away_total) == 0.0:
        return _safe_xg_5050(home_abbrev, away_abbrev)

    def _team_stats(d: Dict[str, float]) -> Dict[str, float]:
        vals = list(d.values())
        g = _gini(vals)  # works fine with floats
        return {"ineq": g, "depth": 1.0 - g}

    h_stats = _team_stats(xg_home)
    a_stats = _team_stats(xg_away)
    h, a = h_stats["depth"], a_stats["depth"]
    denom = (h + a) if (h + a) > 0 else 1.0
    home_pct = round(100.0 * (h / denom), 1)
    away_pct = round(100.0 - home_pct, 1)

    return {
        "no_xg": False,
        "xg_home": {"team": home_abbrev, "total_xg": round(home_total, 3), **h_stats},
        "xg_away": {"team": away_abbrev, "total_xg": round(away_total, 3), **a_stats},
        "xg_depth_share": {"home_pct": home_pct, "away_pct": away_pct},
        "xg": {"xg_home": xg_home, "xg_away": xg_away},
        "params": {
            "situation": situation,
            "adjusted": adjusted,
            "include_goalies": include_goalies,
            "xg_col": xg_col,
        },
    }
