import logging
from datetime import datetime, timezone
import pandas as pd

logger = logging.getLogger(__name__)


def append_live_depth_snapshot(
    game_id: int,
    season: int,
    snapshot: dict
) -> bool:
    """
    Append a depth snapshot to S3 live tracking file for this game.
      
    Path: s3://hockey-decoded/live_game_depth/season={season}/game_id={game_id}.parquet
      
    Deduplicates by checking if last snapshot was within 60 seconds.
      
    Args:
        game_id: NHL game ID
        season: Season year
        snapshot: Dict from calculate_game_depth_snapshot()
      
    Returns:
        True if snapshot was written
        False if skipped (deduplicated) or failed
    """
    # Construct S3 path
    s3_path = f"s3://hockey-decoded/live_game_depth/season={season}/game_id={game_id}.parquet"
    logger.debug(f"Writing snapshot to {s3_path}")

    # Convert game_date to string if it's a date object
    if 'game_date' in snapshot and hasattr(snapshot['game_date'], 'isoformat'):
        snapshot['game_date'] = snapshot['game_date'].isoformat()

    # Try to read existing file using fastparquet
    try:
        existing_df = pd.read_parquet(s3_path, engine='fastparquet')
        logger.debug(f"Found existing file with {len(existing_df)} rows")
    except FileNotFoundError:
        logger.info(f"Creating new live tracking file for game {game_id}")
        existing_df = None
    except Exception as e:
        logger.error(f"Error reading {s3_path}: {e}")
        return False

    # Deduplication check
    if existing_df is not None and len(existing_df) > 0:
        last_timestamp = existing_df.iloc[-1]['timestamp']
        current_timestamp = snapshot['timestamp']
        time_diff = (current_timestamp - last_timestamp).total_seconds()

        if time_diff < 60:
            logger.info(f"Skipping snapshot for game {game_id} - last write was {time_diff:.0f}s ago")
            return False

    # Convert snapshot to DataFrame
    new_row = pd.DataFrame([snapshot])

    # Append or create
    if existing_df is not None:
        combined_df = pd.concat([existing_df, new_row], ignore_index=True)
    else:
        combined_df = new_row

    # Write to S3 using fastparquet
    try:
        combined_df.to_parquet(
            s3_path,
            engine='fastparquet',
            compression='snappy',
            index=False
        )
        logger.info(f"Wrote snapshot for game {game_id} (now {len(combined_df)} total rows)")
        return True
    except Exception as e:
        logger.error(f"Error writing to {s3_path}: {e}")
        return False
    
def write_final_depth(
    game_id: int,
    season: int,
    snapshot: dict
) -> bool:
    """
    Write final depth metrics to master parquet file in LONG format (idempotent).
      
    Path: s3://hockey-decoded/depth_scores/depth_scores.parquet
      
    Creates TWO rows per game (one for each team) to enable easy rolling averages by team.
    Only writes if game_id doesn't already exist in the file.
      
    Args:
        game_id: NHL game ID
        season: Season year
        snapshot: Dict from calculate_game_depth_snapshot() (must be FINAL game state)
      
    Returns:
        True if snapshot was written
        False if already exists or failed
    """
    # Master file path (single file for all games)
    s3_path = "s3://hockey-decoded/depth_scores/depth_scores.parquet"
    logger.debug(f"Writing final depth to {s3_path}")

    # Convert game_date to string if it's a date object
    game_date = snapshot['game_date']
    if hasattr(game_date, 'isoformat'):
        game_date = game_date.isoformat()

    # Try to read existing master file
    try:
        existing_df = pd.read_parquet(s3_path, engine='fastparquet')
        logger.debug(f"Found existing master file with {len(existing_df)} rows")
    except FileNotFoundError:
        logger.info("Creating new master depth scores file")
        existing_df = None
    except Exception as e:
        logger.error(f"Error reading {s3_path}: {e}")
        return False

    # Check if game already finalized (idempotency)
    if existing_df is not None and game_id in existing_df['game_id'].values:
        logger.info(f"Game {game_id} already in master file, skipping")
        return False

    # Transform wide format snapshot into LONG format (2 rows - one per team)
    home_record = {
        'game_id': snapshot['game_id'],
        'season': snapshot['season'],
        'game_date': game_date,
        'timestamp': snapshot['timestamp'],
        'game_state': snapshot['game_state'],
        'team_abbrev': snapshot['home_abbrev'],
        'opponent_abbrev': snapshot['away_abbrev'],
        'home_away': 'home',
        'tdi': snapshot['home_tdi'],
        'weighted_depth': snapshot['home_weighted_depth'],
        'sog_depth': snapshot['home_sog_depth'],
        'cf_depth': snapshot['home_cf_depth'],
        'xg_depth': snapshot['home_xg_depth'],
        'toi_depth': snapshot['home_toi_depth'],
    }
    away_record = {
        'game_id': snapshot['game_id'],
        'season': snapshot['season'],
        'game_date': game_date,
        'timestamp': snapshot['timestamp'],
        'game_state': snapshot['game_state'],
        'team_abbrev': snapshot['away_abbrev'],
        'opponent_abbrev': snapshot['home_abbrev'],
        'home_away': 'away',
        'tdi': snapshot['away_tdi'],
        'weighted_depth': snapshot['away_weighted_depth'],
        'sog_depth': snapshot['away_sog_depth'],
        'cf_depth': snapshot['away_cf_depth'],
        'xg_depth': snapshot['away_xg_depth'],
        'toi_depth': snapshot['away_toi_depth'],
    }

    # Create DataFrame with both rows
    new_rows = pd.DataFrame([home_record, away_record])
    # Append or create
    if existing_df is not None:
        combined_df = pd.concat([existing_df, new_rows], ignore_index=True)
    else:
        combined_df = new_rows
    # Write to S3 using fastparquet
    try:
        combined_df.to_parquet(
            s3_path,
            engine='fastparquet',
            compression='snappy',
            index=False
        )
        logger.info(f"Wrote final depth for game {game_id} (master now has {len(combined_df)} team-games)")
        return True
    except Exception as e:
        logger.error(f"Error writing to {s3_path}: {e}")
        return False
