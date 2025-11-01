from datetime import datetime, timezone
import logging

from app.nhl.parsers.rosters import roster_by_team
from app.nhl.parsers.depth import (
    shot_depth_from_pbp,
    cf_depth_from_pbp,
    xgoal_depth_from_players,
    toi_depth_from_boxscore,
    calculate_tdi
)

from app.nhl.parsers.scoreboard import scoreboard
from app.nhl.models.depth_sem_config import FACTOR_SCORE_COEFFICIENTS

def parse_time_to_seconds(time_str: str) -> int:
    """
    Parse time string "MM:SS" to total seconds.
      
    Examples:
        "05:30" → 330 seconds
        "12:45" → 765 seconds
        "0:00" → 0 seconds
      
    Args:
        time_str: Time in format "MM:SS"
      
    Returns:
        Total seconds as integer
    """
    if not time_str or not isinstance(time_str, str):
        return 0

    try:
        parts = time_str.strip().split(':')
        if len(parts) != 2:
            return 0
        mins = int(parts[0])
        secs = int(parts[1])
        return mins * 60 + secs
    except (ValueError, AttributeError):
        return 0
    
def calculate_current_game_minute(pbp: dict) -> int:
    """
    Calculate current game minute from most recent PBP event.
      
    Game minutes:
        Period 1: 0-20 (minutes 0-19)
        Period 2: 20-40 (minutes 20-39)
        Period 3: 40-60 (minutes 40-59)
        OT: 60+ (minutes 60+)
      
    Args:
        pbp: Play-by-play data dict with 'plays' list
      
    Returns:
        Current game minute as integer (0-60+)
        Returns 0 if no events found
      
    Examples:
        Period 1, timeInPeriod="05:30" → 5 minutes
        Period 2, timeInPeriod="10:00" → 30 minutes (20 + 10)
        Period 3, timeInPeriod="15:45" → 55 minutes (40 + 15)
    """
    if not pbp or 'plays' not in pbp:
        return 0
    
    plays = pbp.get('plays', [])
    if not plays or len(plays) == 0:
        return 0

    # Get the last event
    last_event = plays[-1]

    # Extract period number
    period_desc = last_event.get('periodDescriptor', {})
    period = period_desc.get('number', 1)

    # Extract time in period
    time_in_period = last_event.get('timeInPeriod', '00:00')
    time_seconds = parse_time_to_seconds(time_in_period)
    elapsed_minutes = time_seconds / 60.0

    # Calculate total game minutes based on period
    if period == 1:
        return int(elapsed_minutes)
    elif period == 2:
        return int(20 + elapsed_minutes)
    elif period == 3:
        return int(40 + elapsed_minutes)
    else:  # OT (period 4+)
        return int(60 + elapsed_minutes)
    
def filter_pbp_to_minute(pbp: dict, target_minute: int) -> dict:
    """
    Filter PBP events to only include those up to target_minute.
      
    Creates a "snapshot in time" - as if the game was paused at target_minute.
    This filtered PBP can then be passed to existing depth calculation functions.
      
    Args:
        pbp: Full play-by-play data dict
        target_minute: Game minute to filter to (0-60+)
      
    Returns:
        Filtered PBP dict with only events up to target_minute
      
    Examples:
        target_minute=12 → Include first 12 minutes of P1
        target_minute=25 → Include all P1 + first 5 min of P2
        target_minute=50 → Include all P1, P2 + first 10 min of P3
    """
    if not pbp or 'plays' not in pbp:
        return pbp

    # Determine target period and seconds within that period
    if target_minute <= 20:
        target_period = 1
        target_seconds_in_period = target_minute * 60
    elif target_minute <= 40:
        target_period = 2
        target_seconds_in_period = (target_minute - 20) * 60
    elif target_minute <= 60:
        target_period = 3
        target_seconds_in_period = (target_minute - 40) * 60
    else:  # OT
        target_period = 4
        target_seconds_in_period = (target_minute - 60) * 60

    filtered_plays = []

    for play in pbp['plays']:
        if not isinstance(play, dict):
            continue

        # Get event period and time
        period_desc = play.get('periodDescriptor', {})
        period = period_desc.get('number', 1)
        time_in_period_str = play.get('timeInPeriod', '00:00')
        event_seconds = parse_time_to_seconds(time_in_period_str)

        # Include if from earlier period
        if period < target_period:
            filtered_plays.append(play)
        # Include if from target period and before target time
        elif period == target_period and event_seconds <= target_seconds_in_period:
            filtered_plays.append(play)
        # Skip if from later period or after target time

    # Create filtered PBP (copy original but replace plays)
    filtered_pbp = pbp.copy()
    filtered_pbp['plays'] = filtered_plays

    return filtered_pbp

def calculate_toi_at_minute_from_shifts(
      pbp: dict,
      shifts_json: dict,
      target_minute: int,
      roster_rows: list = None
  ) -> tuple[dict, dict]:
      """
      Calculate each player's TOI (in seconds) up to target_minute using shift data.
      
      This provides ACCURATE historical TOI by summing actual shifts.
      
      Args:
          pbp: Play-by-play data (used to get team abbrevs)
          shifts_json: Raw shifts data from fetch_game_shifts()
          target_minute: Game minute to calculate TOI up to (0-60+)
          roster_rows: Optional roster data to include zero-TOI players
      
      Returns:
          Tuple of (toi_home, toi_away) where each is dict of {player_id: seconds}
      
      Examples:
          target_minute=25 → Sum all shifts through minute 25
          A shift from 24:30-25:30 would count 30 seconds (partial)
      """
      from app.nhl.parsers.scoreboard import scoreboard

      # Get team info from PBP
      home_meta = pbp.get("homeTeam") or {}
      away_meta = pbp.get("awayTeam") or {}
      home_abbrev = home_meta.get("abbrev") or home_meta.get("triCode")
      away_abbrev = away_meta.get("abbrev") or away_meta.get("triCode")

      if not home_abbrev or not away_abbrev:
          return {}, {}

      # Convert target_minute to period and seconds
      if target_minute <= 20:
          target_period = 1
          target_seconds_in_period = target_minute * 60
      elif target_minute <= 40:
          target_period = 2
          target_seconds_in_period = (target_minute - 20) * 60
      elif target_minute <= 60:
          target_period = 3
          target_seconds_in_period = (target_minute - 40) * 60
      else:  # OT
          target_period = 4
          target_seconds_in_period = (target_minute - 60) * 60

      # Get shifts data
      shifts = []
      if isinstance(shifts_json, dict):
          shifts = shifts_json.get("data") or []
      if not isinstance(shifts, list):
          shifts = []

      player_toi = {}  # {player_id: total_seconds}

      for shift in shifts:
          if not isinstance(shift, dict):
              continue

          # Filter to actual shift rows (detailCode==0)
          detail_code = shift.get("detailCode")
          try:
              detail_code = int(detail_code) if detail_code is not None else None
          except Exception:
              detail_code = None
          if detail_code != 0:
              continue

          player_id = shift.get('playerId')
          period = shift.get('period', 1)
          start_time_str = shift.get('startTime', '00:00')
          end_time_str = shift.get('endTime', '00:00')

          if not player_id:
              continue

          try:
              player_id = str(int(player_id))
          except Exception:
              player_id = str(player_id)

          # Parse shift times to seconds
          start_seconds = parse_time_to_seconds(start_time_str)
          end_seconds = parse_time_to_seconds(end_time_str)

          # Initialize player if not seen
          if player_id not in player_toi:
              player_toi[player_id] = 0

          # Case 1: Shift from earlier period (count entire shift)
          if period < target_period:
              shift_duration = end_seconds - start_seconds
              player_toi[player_id] += shift_duration

          # Case 2: Shift from target period
          elif period == target_period:
              # Case 2a: Shift ended before target time (count entire shift)
              if end_seconds <= target_seconds_in_period:
                  shift_duration = end_seconds - start_seconds
                  player_toi[player_id] += shift_duration

              # Case 2b: Shift started before target, still ongoing (partial shift)
              elif start_seconds < target_seconds_in_period:
                  partial_duration = target_seconds_in_period - start_seconds
                  player_toi[player_id] += partial_duration

              # Case 2c: Shift started after target time (don't count)

          # Case 3: Shift from later period (don't count)

      # Split by team using roster or team info from shifts
      toi_home = {}
      toi_away = {}

      # First, assign players to teams using shifts data
      player_teams = {}  # {player_id: team_abbrev}
      for shift in shifts:
          if not isinstance(shift, dict):
              continue
          player_id = shift.get('playerId')
          if not player_id:
              continue
          try:
              player_id = str(int(player_id))
          except Exception:
              player_id = str(player_id)

          team_abbrev = shift.get("teamAbbrev") or shift.get("playerTeamAbbrev")
          if team_abbrev:
              player_teams[player_id] = team_abbrev

      # Distribute TOI to home/away based on team
      for player_id, toi_seconds in player_toi.items():
          team = player_teams.get(player_id, "")
          if team == home_abbrev:
              toi_home[player_id] = toi_seconds
          elif team == away_abbrev:
              toi_away[player_id] = toi_seconds

      # Back-fill zeros from roster (exclude goalies)
      if roster_rows:
          for r in roster_rows:
              ab = r.get("teamAbbrev")
              pid = r.get("playerId")
              if pid is None or ab not in (home_abbrev, away_abbrev):
                  continue
              # Exclude goalies
              pos = (r.get("position") or r.get("positionCode") or "").upper()
              if pos == "G":
                  continue
              try:
                  pid = str(int(pid))
              except Exception:
                  pid = str(pid)
              if ab == home_abbrev:
                  toi_home.setdefault(pid, 0)
              else:
                  toi_away.setdefault(pid, 0)

      return toi_home, toi_away

def calculate_snapshot_at_minute_historical(
      game_id: int,
      season: int,
      pbp: dict,
      box: dict,
      xg,  # pandas DataFrame
      shifts_json: dict,
      target_minute: int
  ) -> dict | None:
      """
      Calculate depth snapshot at a specific game minute using SHIFT-BASED TOI.
      
      This is the HISTORICAL/ACCURATE version that uses real shift data for TOI.
      Use this for:
      - Backfilling historical games
      - Post-game enrichment (replacing interpolated TOI)
      
      Args:
          game_id: NHL game ID
          season: Season year
          pbp: Full play-by-play data
          box: Box score data
          xg: MoneyPuck xG DataFrame
          shifts_json: Shift data from fetch_game_shifts()
          target_minute: Game minute to snapshot (0-60+)
      
      Returns:
          Snapshot dict (same format as calculate_game_depth_snapshot)
          Returns None if insufficient data
      """
      from app.nhl.parsers.rosters import roster_by_team
      from app.nhl.parsers.scoreboard import scoreboard

      logger = logging.getLogger(__name__)

      # Filter PBP to target minute (for shots, CF, xG)
      filtered_pbp = filter_pbp_to_minute(pbp, target_minute)

      # Parse rosters
      rosters = roster_by_team(pbp)

      # Calculate shot depth (using filtered PBP)
      shot_depth_payload = shot_depth_from_pbp(filtered_pbp, rosters)

      # Calculate CF depth (using filtered PBP)
      cf_depth_payload = cf_depth_from_pbp(filtered_pbp, rosters)

      # Calculate xG depth (using filtered PBP)
      # Note: MoneyPuck xG is cumulative, so we use filtered PBP to match events
      xg_depth_payload = xgoal_depth_from_players(
          pbp=filtered_pbp,
          roster_rows=rosters,
          xg_df=xg,
          situation="all",
          adjusted=False,
          include_goalies=False,
      )

      # Calculate TOI from shifts (ACCURATE - uses shift data up to target minute)
      toi_home, toi_away = calculate_toi_at_minute_from_shifts(
          pbp, shifts_json, target_minute, rosters
      )

      # Build TOI depth payload manually (mimics toi_depth_from_boxscore format)
      home_meta = pbp.get("homeTeam") or {}
      away_meta = pbp.get("awayTeam") or {}
      home_abbrev = home_meta.get("abbrev") or home_meta.get("triCode")
      away_abbrev = away_meta.get("abbrev") or away_meta.get("triCode")

      home_total = sum(toi_home.values())
      away_total = sum(toi_away.values())

      # Calculate Gini for TOI
      def _gini(values: list) -> float:
          import numpy as np
          a = np.asarray(values, dtype=np.float64)
          n = a.size
          if n < 2:
              return 0.0
          amin = a.min()
          if amin < 0:
              a = a - amin
          s = a.sum()
          if s <= 0:
              return 0.0
          a = np.sort(a)
          idx = np.arange(1, n + 1, dtype=np.float64)
          return ((2 * idx - n - 1) @ a) / (n * s + 1e-9)

      home_toi_gini = _gini(list(toi_home.values())) if toi_home else 0.0
      away_toi_gini = _gini(list(toi_away.values())) if toi_away else 0.0

      toi_depth_payload = {
          "no_toi": False,
          "toi_home": {"team": home_abbrev, "total_seconds": int(home_total), "ineq": home_toi_gini, "depth": 1.0 - home_toi_gini},
          "toi_away": {"team": away_abbrev, "total_seconds": int(away_total), "ineq": away_toi_gini, "depth": 1.0 - away_toi_gini},
      }

      # Check if we have enough data
      has_shot_data = not shot_depth_payload.get('no_shots', True)
      has_cf_data = not cf_depth_payload.get('no_shots', True)
      has_xg_data = not xg_depth_payload.get('no_xg', True)
      has_toi_data = (home_total + away_total) > 0

      if not (has_shot_data and has_cf_data and has_xg_data and has_toi_data):
          logger.info(f"Game {game_id} minute {target_minute} - insufficient data")
          return None

      # Extract Gini coefficients
      home_sog_gini = shot_depth_payload['home']['ineq']
      away_sog_gini = shot_depth_payload['away']['ineq']
      home_cf_gini = cf_depth_payload['cf_home']['ineq']
      away_cf_gini = cf_depth_payload['cf_away']['ineq']
      home_xg_gini = xg_depth_payload['xg_home']['ineq']
      away_xg_gini = xg_depth_payload['xg_away']['ineq']
      home_toi_gini = toi_depth_payload['toi_home']['ineq']
      away_toi_gini = toi_depth_payload['toi_away']['ineq']

      # Calculate TDI (no blending for historical snapshots)
      home_tdi, home_raw_tdi = calculate_tdi(
          home_cf_gini, home_sog_gini, home_toi_gini, home_xg_gini
      )
      away_tdi, away_raw_tdi = calculate_tdi(
          away_cf_gini, away_sog_gini, away_toi_gini, away_xg_gini
      )

      # Calculate weighted depth
      home_weighted_depth = (
          FACTOR_SCORE_COEFFICIENTS['cf_depth_z'] * (1 - home_cf_gini) +
          FACTOR_SCORE_COEFFICIENTS['sog_depth_z'] * (1 - home_sog_gini) +
          FACTOR_SCORE_COEFFICIENTS['toi_depth_z'] * (1 - home_toi_gini) +
          FACTOR_SCORE_COEFFICIENTS['xgoal_depth_z'] * (1 - home_xg_gini)
      )
      away_weighted_depth = (
          FACTOR_SCORE_COEFFICIENTS['cf_depth_z'] * (1 - away_cf_gini) +
          FACTOR_SCORE_COEFFICIENTS['sog_depth_z'] * (1 - away_sog_gini) +
          FACTOR_SCORE_COEFFICIENTS['toi_depth_z'] * (1 - away_toi_gini) +
          FACTOR_SCORE_COEFFICIENTS['xgoal_depth_z'] * (1 - away_xg_gini)
      )

      # Extract game date
      from datetime import datetime, timezone
      game_date_str = box.get('gameDate')
      if game_date_str:
          game_date = datetime.fromisoformat(game_date_str.split('T')[0]).date()
      else:
          game_date = datetime.now(timezone.utc).date()

      # Get game state from boxscore
      boxscore = scoreboard(pbp)

      # Build snapshot
      snapshot = {
          # Metadata
          'timestamp': datetime.now(timezone.utc),
          'game_id': game_id,
          'season': season,
          'game_date': game_date,
          'game_minute': target_minute,  # NEW: track which minute this snapshot represents

          # Game state
          'period': boxscore.get('period'),
          'time_remaining': None,  # Not applicable for historical snapshots
          'game_state': boxscore.get('gameState'),

          # Teams
          'home_abbrev': home_abbrev,
          'away_abbrev': away_abbrev,

          # Composite metrics
          'home_tdi': home_tdi,
          'away_tdi': away_tdi,
          'home_weighted_depth': home_weighted_depth,
          'away_weighted_depth': away_weighted_depth,

          # Individual depth components
          'home_sog_depth': 1 - home_sog_gini,
          'away_sog_depth': 1 - away_sog_gini,
          'home_cf_depth': 1 - home_cf_gini,
          'away_cf_depth': 1 - away_cf_gini,
          'home_xg_depth': 1 - home_xg_gini,
          'away_xg_depth': 1 - away_xg_gini,
          'home_toi_depth': 1 - home_toi_gini,
          'away_toi_depth': 1 - away_toi_gini,

          # Debug fields (no blending in historical mode)
          'debug_home_prior_depth': None,
          'debug_away_prior_depth': None,
          'debug_home_live_weight': 1.0,  # 100% live data
          'debug_away_live_weight': 1.0,
          'debug_home_shots': shot_depth_payload['home']['total_shots'],
          'debug_away_shots': shot_depth_payload['away']['total_shots'],
          'debug_time_elapsed': float(target_minute),
          'debug_blending_occurred': False,
      }

      return snapshot

def backfill_game_minute_snapshots(
      game_id: int,
      season: int
  ) -> bool:
      """
      Backfill a finished game with clean even-minute snapshots using shift data.
      
      Creates snapshots at minutes 2, 4, 6, 8... 60 using ACCURATE shift-based TOI.
      Replaces the messy live tracking file with clean historical data.
      
      Args:
          game_id: NHL game ID
          season: Season year
      
      Returns:
          True if successful, False otherwise
      
      Usage:
          Called post-game to replace live polling data with accurate snapshots.
      """
      import pandas as pd

      logger = logging.getLogger(__name__)
      logger.info(f"Starting post-game backfill for game {game_id}")

      try:
          # Fetch all game data (using long cache since game is finished)
          from app.nhl.service import fetch_game_pbp, fetch_game_box, fetch_moneypuck_player_xg_csv, fetch_game_shifts

          pbp = fetch_game_pbp(game_id, season, ttl_seconds=3600)
          box = fetch_game_box(game_id, season, ttl_seconds=3600)
          xg = fetch_moneypuck_player_xg_csv(game_id, season, ttl_seconds=3600)
          shifts = fetch_game_shifts(game_id, season, ttl_seconds=3600)

          if not pbp or not box or xg is None or not shifts:
              logger.warning(f"Game {game_id} - missing required data for backfill")
              return False

          # Calculate max game minute from actual PBP events
          max_minute = calculate_current_game_minute(pbp)

          # For regulation games (60 minutes), cap at 60
          # For OT games, we'll get 61, 62, 63, etc. which is correct
          if max_minute == 60:
              # Standard regulation game
              pass
          elif max_minute > 60:
              # OT game - use actual final minute
              logger.info(f"Game {game_id} went to OT (minute {max_minute})")
          else:
              # Game might have incomplete data
              logger.warning(f"Game {game_id} only reached minute {max_minute} (expected 60+)")

          # Generate even minutes to backfill (2, 4, 6... up to max)
          target_minutes = [m for m in range(2, min(max_minute + 1, 61), 2)]

          logger.info(f"Game {game_id} - backfilling {len(target_minutes)} snapshots (up to minute {max_minute})")

          # Calculate snapshot for each even minute
          snapshots = []
          successful = 0
          failed = 0

          for minute in target_minutes:
              try:
                  snapshot = calculate_snapshot_at_minute_historical(
                      game_id=game_id,
                      season=season,
                      pbp=pbp,
                      box=box,
                      xg=xg,
                      shifts_json=shifts,
                      target_minute=minute
                  )

                  if snapshot:
                      snapshots.append(snapshot)
                      successful += 1
                  else:
                      logger.debug(f"Game {game_id} minute {minute} - no snapshot (insufficient data)")
                      failed += 1

              except Exception as e:
                  logger.error(f"Game {game_id} minute {minute} - error: {e}")
                  failed += 1

          if not snapshots:
              logger.warning(f"Game {game_id} - no successful snapshots")
              return False

          # Convert to DataFrame
          df = pd.DataFrame(snapshots)

          # Convert game_date to string if needed
          if 'game_date' in df.columns:
              df['game_date'] = df['game_date'].apply(
                  lambda x: x.isoformat() if hasattr(x, 'isoformat') else x
              )

          # Write to S3 (REPLACES live tracking file with clean historical data)
          s3_path = f"s3://hockey-decoded/live_game_depth/season={season}/game_id={game_id}.parquet"

          df.to_parquet(
              s3_path,
              engine='fastparquet',
              compression='snappy',
              index=False
          )

          logger.info(f"Game {game_id} - backfill complete: {successful} snapshots written, {failed} failed")
          return True

      except Exception as e:
          logger.error(f"Game {game_id} - backfill failed: {e}", exc_info=True)
          return False

def smooth_depth_component_if_outlier(
          game_id: int, 
          season: int, 
          current_home_gini: float, 
          current_away_gini: float,
          component_name: str,  # 'xg', 'sog', or 'cf'
          home_abbrev: str, 
          away_abbrev: str) -> tuple[float, float]:
          """
          Smooth Gini values if they appear to be outliers compared to recent snapshots.
          Works for any depth component (xG, SOG, CF).

          Returns: (smoothed_home_gini, smoothed_away_gini)
          """
          import s3fs
          import pandas as pd

          try:
              s3_path = f"s3://hockey-decoded/live_game_depth/season={season}/game_id={game_id}.parquet"
              df = pd.read_parquet(s3_path, engine='fastparquet')

              if len(df) < 3:
                  # Not enough history, return current values
                  return current_home_gini, current_away_gini

              # Get last 5 snapshots
              recent = df.tail(5)

              # Map component name to column name
              depth_col_map = {
                  'xg': 'home_xg_depth',
                  'sog': 'home_sog_depth',
                  'cf': 'home_cf_depth'
              }

              home_col = depth_col_map.get(component_name, 'home_xg_depth')
              away_col = home_col.replace('home_', 'away_')

              # Calculate median gini from recent depth values
              home_median = recent[home_col].apply(lambda x: 1 - x).median()
              away_median = recent[away_col].apply(lambda x: 1 - x).median()

              # Define outlier threshold
              OUTLIER_THRESHOLD = 0.15

              # Check home team
              if abs(current_home_gini - home_median) > OUTLIER_THRESHOLD:
                  logger.info(f"Game {game_id} - Smoothing {home_abbrev} {component_name} gini outlier: {current_home_gini:.3f} -> {home_median:.3f}")
                  current_home_gini = home_median

              # Check away team
              if abs(current_away_gini - away_median) > OUTLIER_THRESHOLD:
                  logger.info(f"Game {game_id} - Smoothing {away_abbrev} {component_name} gini outlier: {current_away_gini:.3f} -> {away_median:.3f}")
                  current_away_gini = away_median

          except Exception as e:
              logger.debug(f"Game {game_id} - Could not apply {component_name} smoothing: {e}")
              pass

          return current_home_gini, current_away_gini

logger = logging.getLogger(__name__)

def calculate_game_depth_snapshot(
        game_id: int,
        season: int,
        pbp: dict,
        box: dict,
        xg,  # pandas DataFrame
        allow_final: bool = False  # New parameter
    ) -> dict | None:
        """
        Calculate all depth metrics for a game at this moment in time.
          
        Args:
            game_id: NHL game ID (e.g., 2024030416)
            season: Season year (e.g., 20242025)
            pbp: Play-by-play data from fetch_game_pbp()
            box: Box score data from fetch_game_box()
            xg: Expected goals data from fetch_moneypuck_player_xg_csv()
          
        Returns:
            Dict with depth snapshot data including:
            - timestamp, game_id, season
            - period, time_remaining, game_state
            - home/away abbreviations
            - TDI scores (z-scored)
            - Weighted depths (blended with priors if early in game)
            - Individual depth metrics (shot, CF, xG, TOI)
              
            Returns None if insufficient data to calculate TDI.
        """
        # Check if we have the required data
        if pbp is None or box is None or xg is None:
            logger.warning(f"Game {game_id} - missing source data (game may not have started)")
            return None

        # Skip intermission snapshots (no new events, would just duplicate previous snapshot)
        clock_data = box.get("clock", {}) or {}
        in_intermission = clock_data.get('inIntermission', False)
        if in_intermission:
                logger.info(f"Game {game_id} - in intermission, skipping snapshot")
                return None

        # Parse rosters
        rosters = roster_by_team(pbp)

        # Calculate the 4 depth metrics
        shot_depth_payload = shot_depth_from_pbp(pbp, rosters)
        cf_depth_payload = cf_depth_from_pbp(pbp, rosters)
        toi_depth_payload = toi_depth_from_boxscore(pbp, box, rosters)
        xg_depth_payload = xgoal_depth_from_players(
            pbp=pbp,
            roster_rows=rosters,
            xg_df=xg,
            situation="all",
            adjusted=False,
            include_goalies=False,
        )

        # Check if we have enough data to calculate TDI
        has_shot_data = not shot_depth_payload.get('no_shots', True)
        has_cf_data = not cf_depth_payload.get('no_shots', True)
        has_xg_data = not xg_depth_payload.get('no_xg', True)
        has_toi_data = not toi_depth_payload.get('no_toi', True)

        if not (has_shot_data and has_cf_data and has_xg_data and has_toi_data):
            logger.info(f"Game {game_id} - insufficient data for TDI calculation")
            return None

        # Extract Gini coefficients from each depth payload
        home_sog_gini = shot_depth_payload['home']['ineq']
        away_sog_gini = shot_depth_payload['away']['ineq']

        home_cf_gini = cf_depth_payload['cf_home']['ineq']
        away_cf_gini = cf_depth_payload['cf_away']['ineq']

        home_xg_gini = xg_depth_payload['xg_home']['ineq']
        away_xg_gini = xg_depth_payload['xg_away']['ineq']

        home_toi_gini = toi_depth_payload['toi_home']['ineq']
        away_toi_gini = toi_depth_payload['toi_away']['ineq']

        # Get team abbreviations from depth payload (needed for blending)
        home_abbrev = shot_depth_payload.get('home', {}).get('team')
        away_abbrev = shot_depth_payload.get('away', {}).get('team')

        # Smooth gini values to handle data anomalies
        home_sog_gini, away_sog_gini = smooth_depth_component_if_outlier(
            game_id, season, home_sog_gini, away_sog_gini, 'sog', home_abbrev, away_abbrev
        )
        home_cf_gini, away_cf_gini = smooth_depth_component_if_outlier(
            game_id, season, home_cf_gini, away_cf_gini, 'cf', home_abbrev, away_abbrev
        )
        home_xg_gini, away_xg_gini = smooth_depth_component_if_outlier(
            game_id, season, home_xg_gini, away_xg_gini, 'xg', home_abbrev, away_abbrev
        )

        # BAYESIAN BLENDING: Blend Ginis with priors based on data accumulation
        boxscore = scoreboard(pbp)
        game_state = boxscore.get('gameState', '')

        # Skip FINAL/OFF games ONLY during live tracking (not during backfill)
        if not allow_final and game_state in ('FINAL', 'OFF'):
            logger.info(f"Game {game_id} - game finished, skipping live snapshot")
            return None

        # Initialize debug data 
        debug_data = {
            'home_prior_weighted_depth': None,
            'away_prior_weighted_depth': None,
            'home_live_weight': None,
            'away_live_weight': None,
            'home_shots': None,
            'away_shots': None,
            'time_elapsed': None,
            'blending_occurred': False
        }

        # Only blend if game is live (not final)
        if game_state not in ('FINAL', 'OFF'):
            period = boxscore.get('period', 1)
            time_remaining = clock_data.get('timeRemaining', '20:00')

            # Calculate time elapsed (in minutes)
            try:
                mins, secs = time_remaining.split(':')
                time_remaining_mins = int(mins) + int(secs) / 60
            except:
                time_remaining_mins = 20.0

            if period == 1:
                time_elapsed = 20 - time_remaining_mins
            elif period == 2:
                time_elapsed = 20 + (20 - time_remaining_mins)
            elif period == 3:
                time_elapsed = 40 + (20 - time_remaining_mins)
            else:  # OT or later
                time_elapsed = 60

            # Check for backwards time (intermission bug where period shows 2/00:00 then jumps to 2/16:25)
            try:
                import s3fs
                import pandas as pd
                s3_path = f"s3://hockey-decoded/live_game_depth/season={season}/game_id={game_id}.parquet"
                prev_df = pd.read_parquet(s3_path, engine='fastparquet')
                if len(prev_df) > 0:
                    last_time = prev_df.iloc[-1].get('debug_time_elapsed')
                    if pd.notna(last_time) and time_elapsed < last_time - 1.0:  # Allow 1 min tolerance
                        logger.warning(f"Game {game_id} - Time went backwards: {last_time:.1f} → {time_elapsed:.1f}, skipping")
                        return None
            except Exception as e:
                logger.debug(f"Game {game_id} - Could not check previous time: {e}")
                pass  # No previous data or read error, continue

            # Get shot counts for each team
            home_shots = shot_depth_payload['home']['total_shots']
            away_shots = shot_depth_payload['away']['total_shots']

            # Blending thresholds
            SHOTS_THRESHOLD = 25.0
            TIME_THRESHOLD = 40.0

            # Calculate live weights for each team
            shots_weight_home = min(1.0, (home_shots / SHOTS_THRESHOLD) ** 2)
            shots_weight_away = min(1.0, (away_shots / SHOTS_THRESHOLD) ** 2)
            time_weight = min(1.0, time_elapsed / TIME_THRESHOLD)

            weight_live_home = max(shots_weight_home, time_weight)
            weight_live_away = max(shots_weight_away, time_weight)

            # Component-specific minimums: don't use live data if sample size too small
            MIN_SHOTS_FOR_SOG = 5
            MIN_SHOTS_FOR_CF = 5  # Corsi events usually > shots

            # Override weights to 0 for components with insufficient data
            sog_weight_home = weight_live_home if home_shots >= MIN_SHOTS_FOR_SOG else 0.0
            sog_weight_away = weight_live_away if away_shots >= MIN_SHOTS_FOR_SOG else 0.0

            # For CF, estimate CF events as ~1.5x shots (rough approximation)
            cf_weight_home = weight_live_home if home_shots >= MIN_SHOTS_FOR_CF else 0.0
            cf_weight_away = weight_live_away if away_shots >= MIN_SHOTS_FOR_CF else 0.0

            # xG and TOI: use normal weight (more stable early)
            xg_weight_home = weight_live_home
            xg_weight_away = weight_live_away
            toi_weight_home = weight_live_home
            toi_weight_away = weight_live_away

            # Store debug data for weights/shots/time
            debug_data['home_shots'] = home_shots
            debug_data['away_shots'] = away_shots
            debug_data['time_elapsed'] = time_elapsed
            debug_data['home_live_weight'] = weight_live_home
            debug_data['away_live_weight'] = weight_live_away

            # Only blend if we haven't reached full confidence yet
            if weight_live_home < 1.0 or weight_live_away < 1.0:
                # Load rolling averages
                from app.nhl.league_stats import get_current_rolling_averages
                rolling_avgs = get_current_rolling_averages(season=2025)

                if rolling_avgs:
                    home_data = rolling_avgs.get(home_abbrev)
                    away_data = rolling_avgs.get(away_abbrev)

                    if home_data and away_data:
                        # Store prior depths for debugging
                        debug_data['home_prior_weighted_depth'] = home_data['weighted_depth']
                        debug_data['away_prior_weighted_depth'] = away_data['weighted_depth']
                        debug_data['blending_occurred'] = True

                        # Blend home team Ginis (component-specific weights)
                        if sog_weight_home < 1.0:
                            weight_prior = 1.0 - sog_weight_home
                            home_sog_gini = (weight_prior * home_data['shot_gini']) + (sog_weight_home * home_sog_gini)

                        if cf_weight_home < 1.0:
                            weight_prior = 1.0 - cf_weight_home
                            home_cf_gini = (weight_prior * home_data['cf_gini']) + (cf_weight_home * home_cf_gini)

                        if xg_weight_home < 1.0:
                            weight_prior = 1.0 - xg_weight_home
                            home_xg_gini = (weight_prior * home_data['xg_gini']) + (xg_weight_home * home_xg_gini)

                        if toi_weight_home < 1.0:
                            weight_prior = 1.0 - toi_weight_home
                            home_toi_gini = (weight_prior * home_data['toi_gini']) + (toi_weight_home * home_toi_gini)

                        logger.debug(f"Game {game_id} - Blended {home_abbrev} (SOG wt={sog_weight_home:.2f}, CF wt={cf_weight_home:.2f})")

                        # Blend away team Ginis (component-specific weights)
                        if sog_weight_away < 1.0:
                            weight_prior = 1.0 - sog_weight_away
                            away_sog_gini = (weight_prior * away_data['shot_gini']) + (sog_weight_away * away_sog_gini)

                        if cf_weight_away < 1.0:
                            weight_prior = 1.0 - cf_weight_away
                            away_cf_gini = (weight_prior * away_data['cf_gini']) + (cf_weight_away * away_cf_gini)

                        if xg_weight_away < 1.0:
                            weight_prior = 1.0 - xg_weight_away
                            away_xg_gini = (weight_prior * away_data['xg_gini']) + (xg_weight_away * away_xg_gini)

                        if toi_weight_away < 1.0:
                            weight_prior = 1.0 - toi_weight_away
                            away_toi_gini = (weight_prior * away_data['toi_gini']) + (toi_weight_away * away_toi_gini)

                        logger.debug(f"Game {game_id} - Blended {away_abbrev} (SOG wt={sog_weight_away:.2f}, CF wt={cf_weight_away:.2f})")

        # Calculate TDI using SEM factor scores (now with blended Ginis)
        home_tdi, home_raw_tdi = calculate_tdi(
            home_cf_gini, home_sog_gini, home_toi_gini, home_xg_gini
        )
        away_tdi, away_raw_tdi = calculate_tdi(
            away_cf_gini, away_sog_gini, away_toi_gini, away_xg_gini
        )

        # Calculate weighted depth for visualization (using blended Ginis)
        home_weighted_depth = (
            FACTOR_SCORE_COEFFICIENTS['cf_depth_z'] * (1 - home_cf_gini) +
            FACTOR_SCORE_COEFFICIENTS['sog_depth_z'] * (1 - home_sog_gini) +
            FACTOR_SCORE_COEFFICIENTS['toi_depth_z'] * (1 - home_toi_gini) +
            FACTOR_SCORE_COEFFICIENTS['xgoal_depth_z'] * (1 - home_xg_gini)
        )

        away_weighted_depth = (
            FACTOR_SCORE_COEFFICIENTS['cf_depth_z'] * (1 - away_cf_gini) +
            FACTOR_SCORE_COEFFICIENTS['sog_depth_z'] * (1 - away_sog_gini) +
            FACTOR_SCORE_COEFFICIENTS['toi_depth_z'] * (1 - away_toi_gini) +
            FACTOR_SCORE_COEFFICIENTS['xgoal_depth_z'] * (1 - away_xg_gini)
        )

        # Extract game date from box data
        game_date_str = box.get('gameDate')
        if game_date_str:
            # Parse ISO date string to date object
            game_date = datetime.fromisoformat(game_date_str.split('T')[0]).date()
        else:
            # Fallback: use current date in UTC
            game_date = datetime.now(timezone.utc).date()
        
        # Calculate current game minute for this snapshot
        current_minute = calculate_current_game_minute(pbp)

        # Build the snapshot dictionary (with blended values)
        snapshot = {
            # Metadata
            'timestamp': datetime.now(timezone.utc),
            'game_id': game_id,
            'season': season,
            'game_date': game_date,
            'game_minute': current_minute,

            # Game state
            'period': boxscore.get('period'),
            'time_remaining': clock_data.get('timeRemaining'),
            'game_state': boxscore.get('gameState'),

            # Teams
            'home_abbrev': home_abbrev,
            'away_abbrev': away_abbrev,

            # Composite metrics (calculated from blended Ginis)
            'home_tdi': home_tdi,
            'away_tdi': away_tdi,
            'home_weighted_depth': home_weighted_depth,
            'away_weighted_depth': away_weighted_depth,

            # Individual depth components (1 - blended Gini = blended depth)
            'home_sog_depth': 1 - home_sog_gini,
            'away_sog_depth': 1 - away_sog_gini,
            'home_cf_depth': 1 - home_cf_gini,
            'away_cf_depth': 1 - away_cf_gini,
            'home_xg_depth': 1 - home_xg_gini,
            'away_xg_depth': 1 - away_xg_gini,
            'home_toi_depth': 1 - home_toi_gini,
            'away_toi_depth': 1 - away_toi_gini,

            # Debug fields
            'debug_home_prior_depth': debug_data['home_prior_weighted_depth'],
            'debug_away_prior_depth': debug_data['away_prior_weighted_depth'],
            'debug_home_live_weight': debug_data['home_live_weight'],
            'debug_away_live_weight': debug_data['away_live_weight'],
            'debug_home_shots': debug_data['home_shots'],
            'debug_away_shots': debug_data['away_shots'],
            'debug_time_elapsed': debug_data['time_elapsed'],
            'debug_blending_occurred': debug_data['blending_occurred'],
        }

        return snapshot