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