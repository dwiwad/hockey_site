# app/nhl/parsers/depth.py
from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
import pandas as pd
from app.nhl.models.depth_sem_config import FACTOR_SCORE_COEFFICIENTS, DEPTH_MEANS, DEPTH_SDS, FACTOR_SCORE_MEAN, FACTOR_SCORE_SD

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
    """Gini coefficient using efficient sorted-array formula (matches historical calculation)."""
    import numpy as np

    a = np.asarray(values, dtype=np.float64)
    n = a.size

    if n < 2:
        return 0.0

    # Shift up if any negatives
    amin = a.min()
    if amin < 0:
        a = a - amin

    s = a.sum()
    if s <= 0:
        return 0.0

    # Sort and apply vectorized formula
    a = np.sort(a)
    idx = np.arange(1, n + 1, dtype=np.float64)
    return ((2 * idx - n - 1) @ a) / (n * s + 1e-9)

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
        # Exclude goalies (match historical calculation)
        pos = (r.get("position") or r.get("positionCode") or "").upper()
        if pos == "G":
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
            # Exclude goalies (match historical calculation)
            pos = (r.get("position") or r.get("positionCode") or "").upper()
            if pos == "G":
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

# ---------- SHIFT (TOI) depth from boxscore JSON ----------

from math import isnan

def _parse_mmss_to_sec(mmss: str) -> int:
    if not isinstance(mmss, str) or ":" not in mmss:
        return 0
    try:
        mm, ss = mmss.strip().split(":")
        return int(mm) * 60 + int(ss)
    except Exception:
        return 0

def _safe_toi_5050(home_abbrev: str | None, away_abbrev: str | None) -> Dict[str, Any]:
    return {
        "no_toi": True,
        "toi_home": {"team": home_abbrev, "total_seconds": 0, "ineq": 0.0, "depth": 0.0},
        "toi_away": {"team": away_abbrev, "total_seconds": 0, "ineq": 0.0, "depth": 0.0},
        "toi_depth_share": {"home_pct": 50.0, "away_pct": 50.0},
        "toi": {"toi_home": {}, "toi_away": {}},
    }

def toi_depth_from_shifts(
    pbp: Dict[str, Any],
    shifts_json: Dict[str, Any],
    roster_rows: List[Dict[str, Any]] | None = None,
    include_goalies: bool = False
) -> Dict[str, Any]:
    """
    Compute TOI-based depth (1 - Gini) from NHL shiftcharts JSON.

    Parameters
    ----------
    pbp : dict
        The game PBP JSON (used only to resolve home/away abbrevs/ids).
    shifts_json : dict
        Raw toi payload as cached by service (shape: {"data": [...]}).
    roster_rows : list of dict, optional
        Roster rows to back-fill zeros per player (keys: teamAbbrev, playerId, position/positionCode).
    include_goalies : bool
        Include goalies in the Gini distribution (default False).

    Returns
    -------
    dict shaped like other depth payloads, using 'toi_*' keys.
    """
    home_meta, away_meta = _home_away_meta(pbp)
    home_abbrev = home_meta.get("abbrev") or home_meta.get("triCode")
    away_abbrev = away_meta.get("abbrev") or away_meta.get("triCode")
    if not home_abbrev or not away_abbrev:
        return _safe_toi_5050(home_abbrev, away_abbrev)

    rows = []
    if isinstance(shifts_json, dict):
        rows = shifts_json.get("data") or []
    if not isinstance(rows, list):
        rows = []

    # Accumulate seconds per player by team
    toi_home: Dict[str, int] = {}
    toi_away: Dict[str, int] = {}

    for r in rows:
        if not isinstance(r, dict):
            continue
        # Keep only actual shift rows; detailCode==0 in your static pipeline
        dc = r.get("detailCode")
        try:
            dc = int(dc) if dc is not None else None
        except Exception:
            dc = None
        if dc != 0:
            continue

        # Team abbrev is usually "teamAbbrev" or "playerTeamAbbrev"
        team_abbrev = r.get("teamAbbrev") or r.get("playerTeamAbbrev")
        if not team_abbrev:
            # fall back: compare teamId with pbp meta ids if present
            tid = r.get("teamId")
            try:
                tid = int(tid) if tid is not None else None
            except Exception:
                tid = None
            if tid is not None:
                if int(away_meta.get("id") or -1) == tid:
                    team_abbrev = away_abbrev
                elif int(home_meta.get("id") or -1) == tid:
                    team_abbrev = home_abbrev
        if team_abbrev not in (home_abbrev, away_abbrev):
            continue

        # Player + position
        pid = r.get("playerId")
        if pid is None:
            continue
        try:
            pid_str = str(int(pid))
        except Exception:
            pid_str = str(pid)

        pos = (r.get("position") or r.get("positionCode") or "").upper()
        if not include_goalies and pos == "G":
            continue

        # Duration is "MM:SS" (some feeds also include startTime/endTime)
        dur = r.get("duration") or ""
        sec = _parse_mmss_to_sec(dur)
        if sec <= 0:
            # fallback if duration missing: derive from start/end when available
            start = _parse_mmss_to_sec(r.get("startTime") or "")
            end = _parse_mmss_to_sec(r.get("endTime") or "")
            sec = max(0, end - start)
        if sec <= 0:
            continue

        if team_abbrev == home_abbrev:
            toi_home[pid_str] = toi_home.get(pid_str, 0) + sec
        else:
            toi_away[pid_str] = toi_away.get(pid_str, 0) + sec

    # Back-fill zeros using roster so the distribution includes all skaters
    for rr in (roster_rows or []):
        ab = rr.get("teamAbbrev")
        if ab not in (home_abbrev, away_abbrev):
            continue
        pid = rr.get("playerId")
        if pid is None:
            continue
        pos = (rr.get("position") or rr.get("positionCode") or "").upper()
        if not include_goalies and pos == "G":
            continue
        try:
            pid_str = str(int(pid))
        except Exception:
            pid_str = str(pid)
        if ab == home_abbrev:
            toi_home.setdefault(pid_str, 0)
        else:
            toi_away.setdefault(pid_str, 0)

    home_total = sum(toi_home.values())
    away_total = sum(toi_away.values())
    if (home_total + away_total) == 0:
        return _safe_toi_5050(home_abbrev, away_abbrev)

    def _team_stats(d: Dict[str, int]) -> Dict[str, float]:
        vals = list(d.values())
        g = _gini(vals)
        return {"ineq": g, "depth": 1.0 - g}

    h_stats = _team_stats(toi_home)
    a_stats = _team_stats(toi_away)

    h, a = h_stats["depth"], a_stats["depth"]
    denom = (h + a) if (h + a) > 0 else 1.0
    home_pct = round(100.0 * (h / denom), 1)
    away_pct = round(100.0 - home_pct, 1)

    return {
        "no_toi": False,
        "toi_home": {"team": home_abbrev, "total_seconds": int(home_total), **h_stats},
        "toi_away": {"team": away_abbrev, "total_seconds": int(away_total), **a_stats},
        "toi_depth_share": {"home_pct": home_pct, "away_pct": away_pct},
        "toi": {"toi_home": toi_home, "toi_away": toi_away},
        "params": {"include_goalies": include_goalies},
    }

def calculate_tdi(cf_gini: float, sog_gini: float, toi_gini: float, xgoal_gini: float) -> float:
      """
      Calculate Total Depth Index (TDI) using SEM factor loadings.
      
      This implements the structural equation model:
          depth =~ cf_depth_z + sog_depth_z + toi_depth_z + xgoal_depth_z
      
      Args:
          cf_gini: Corsi For Gini coefficient (raw, unstandardized)
          sog_gini: Shots on Goal Gini coefficient (raw)
          toi_gini: Time on Ice Gini coefficient (raw)
          xgoal_gini: Expected Goals Gini coefficient (raw)
      
      Returns:
          Total Depth Index (TDI) - latent factor score
          Higher values = more depth (more equal distribution)
          Lower values = less depth (more concentrated)
      """
      # Step 1: Convert Gini to Depth (1 - Gini)
      cf_depth = 1.0 - cf_gini
      sog_depth = 1.0 - sog_gini
      toi_depth = 1.0 - toi_gini
      xgoal_depth = 1.0 - xgoal_gini

      # Step 2: Z-score depth values using training data parameters
      cf_z = (cf_depth - DEPTH_MEANS['cf_depth']) / DEPTH_SDS['cf_depth']
      sog_z = (sog_depth - DEPTH_MEANS['sog_depth']) / DEPTH_SDS['sog_depth']
      toi_z = (toi_depth - DEPTH_MEANS['toi_depth']) / DEPTH_SDS['toi_depth']
      xgoal_z = (xgoal_depth - DEPTH_MEANS['xgoal_depth']) / DEPTH_SDS['xgoal_depth']

      # Step 3: Apply factor score coefficients (weighted sum)
      raw_tdi = (
          FACTOR_SCORE_COEFFICIENTS['cf_depth_z'] * cf_z +
          FACTOR_SCORE_COEFFICIENTS['sog_depth_z'] * sog_z +
          FACTOR_SCORE_COEFFICIENTS['toi_depth_z'] * toi_z +
          FACTOR_SCORE_COEFFICIENTS['xgoal_depth_z'] * xgoal_z
      )

      # Step 4: Z-score the factor scores (matches scipy.stats.zscore in analysis.py)
      tdi_zscore = (raw_tdi - FACTOR_SCORE_MEAN) / FACTOR_SCORE_SD

      return tdi_zscore, raw_tdi

def toi_depth_from_boxscore(
      pbp: Dict[str, Any],
      box: Dict[str, Any],
      roster_rows: List[Dict[str, Any]] | None = None,
      include_goalies: bool = False
  ) -> Dict[str, Any]:
      """
      Compute TOI-based depth (1 - Gini) from NHL boxscore JSON.
      
      Parameters
      ----------
      pbp : dict
          The game PBP JSON (used only to resolve home/away abbrevs/ids).
      box : dict
          Boxscore data with playerByGameStats section.
      roster_rows : list of dict, optional
          Roster rows to back-fill zeros per player (keys: teamAbbrev, playerId, position/positionCode).
      include_goalies : bool
          Include goalies in the Gini distribution (default False).
      
      Returns
      -------
      dict shaped like other depth payloads, using 'toi_*' keys.
      """
      home_meta, away_meta = _home_away_meta(pbp)
      home_abbrev = home_meta.get("abbrev") or home_meta.get("triCode")
      away_abbrev = away_meta.get("abbrev") or away_meta.get("triCode")
      if not home_abbrev or not away_abbrev:
          return _safe_toi_5050(home_abbrev, away_abbrev)

      # Check if playerByGameStats exists (won't exist in pre-game)
      player_stats = box.get("playerByGameStats")
      if not player_stats:
          return _safe_toi_5050(home_abbrev, away_abbrev)

      # Accumulate seconds per player by team
      toi_home: Dict[str, int] = {}
      toi_away: Dict[str, int] = {}

      # Process both teams
      for team_key, toi_dict in [("homeTeam", toi_home), ("awayTeam", toi_away)]:
          team_data = player_stats.get(team_key, {})

          # Loop through all position groups (forwards, defense, goalies)
          for position_group in ["forwards", "defense", "goalies"]:
              players = team_data.get(position_group, [])

              for player in players:
                  # Skip goalies if not including them
                  pos = player.get("position", "").upper()
                  if not include_goalies and pos == "G":
                      continue

                  # Get player ID
                  pid = player.get("playerId")
                  if pid is None:
                      continue
                  try:
                      pid_str = str(int(pid))
                  except Exception:
                      pid_str = str(pid)

                  # Get TOI string (format: "12:40")
                  toi_str = player.get("toi", "0:00")
                  sec = _parse_mmss_to_sec(toi_str)

                  if sec > 0:
                      toi_dict[pid_str] = toi_dict.get(pid_str, 0) + sec

      # Back-fill zeros using roster so the distribution includes all skaters
      for rr in (roster_rows or []):
          ab = rr.get("teamAbbrev")
          if ab not in (home_abbrev, away_abbrev):
              continue
          pid = rr.get("playerId")
          if pid is None:
              continue
          pos = (rr.get("position") or rr.get("positionCode") or "").upper()
          if not include_goalies and pos == "G":
              continue
          try:
              pid_str = str(int(pid))
          except Exception:
              pid_str = str(pid)
          if ab == home_abbrev:
              toi_home.setdefault(pid_str, 0)
          else:
              toi_away.setdefault(pid_str, 0)

      home_total = sum(toi_home.values())
      away_total = sum(toi_away.values())
      if (home_total + away_total) == 0:
          return _safe_toi_5050(home_abbrev, away_abbrev)

      def _team_stats(d: Dict[str, int]) -> Dict[str, float]:
          vals = list(d.values())
          g = _gini(vals)
          return {"ineq": g, "depth": 1.0 - g}

      h_stats = _team_stats(toi_home)
      a_stats = _team_stats(toi_away)

      h, a = h_stats["depth"], a_stats["depth"]
      denom = (h + a) if (h + a) > 0 else 1.0
      home_pct = round(100.0 * (h / denom), 1)
      away_pct = round(100.0 - home_pct, 1)

      return {
          "no_toi": False,
          "toi_home": {"team": home_abbrev, "total_seconds": int(home_total), **h_stats},
          "toi_away": {"team": away_abbrev, "total_seconds": int(away_total), **a_stats},
          "toi_depth_share": {"home_pct": home_pct, "away_pct": away_pct},
          "toi": {"toi_home": toi_home, "toi_away": toi_away},
          "params": {"include_goalies": include_goalies},
      }