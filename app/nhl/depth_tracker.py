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

logger = logging.getLogger(__name__)

def calculate_game_depth_snapshot(
    game_id: int,
    season: int,
    pbp: dict,
    box: dict,
    xg  # pandas DataFrame
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
        - Weighted depths
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

     # Calculate TDI using SEM factor scores
    home_tdi, home_raw_tdi = calculate_tdi(
        home_cf_gini, home_sog_gini, home_toi_gini, home_xg_gini
    )
    away_tdi, away_raw_tdi = calculate_tdi(
        away_cf_gini, away_sog_gini, away_toi_gini, away_xg_gini
    )

    # Calculate weighted depth for visualization
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

    # Extract game state info
    boxscore = scoreboard(pbp)
    clock_data = box.get("clock", {}) or {}

    # Get team abbreviations from depth payload
    home_abbrev = shot_depth_payload.get('home', {}).get('team')
    away_abbrev = shot_depth_payload.get('away', {}).get('team')

    # Extract game date from box data
    game_date_str = box.get('gameDate')
    if game_date_str:
        # Parse ISO date string to date object
        game_date = datetime.fromisoformat(game_date_str.split('T')[0]).date()
    else:
        # Fallback: use current date in UTC
        game_date = datetime.now(timezone.utc).date()

    # Build the snapshot dictionary
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

        # Composite metrics
        'home_tdi': home_tdi,
        'away_tdi': away_tdi,
        'home_weighted_depth': home_weighted_depth,
        'away_weighted_depth': away_weighted_depth,

        # Individual depth components (1 - Gini = depth)
        'home_sog_depth': 1 - home_sog_gini,
        'away_sog_depth': 1 - away_sog_gini,
        'home_cf_depth': 1 - home_cf_gini,
        'away_cf_depth': 1 - away_cf_gini,
        'home_xg_depth': 1 - home_xg_gini,
        'away_xg_depth': 1 - away_xg_gini,
        'home_toi_depth': 1 - home_toi_gini,
        'away_toi_depth': 1 - away_toi_gini,
    }

    return snapshot