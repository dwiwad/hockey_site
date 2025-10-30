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

        # Build the snapshot dictionary (with blended values)
        snapshot = {
            # Metadata
            'timestamp': datetime.now(timezone.utc),
            'game_id': game_id,
            'season': season,
            'game_date': game_date,

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