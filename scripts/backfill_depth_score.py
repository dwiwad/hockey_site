import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

import logging
from datetime import date, timedelta
import s3fs

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Delete existing master to start fresh
# s3 = s3fs.S3FileSystem()
# master_path = 'hockey-decoded/depth_scores/depth_scores.parquet'

# if s3.exists(master_path):
#     s3.rm(master_path)
#     logger.info("✅ Deleted old master file")
# else:
#     logger.info("No existing master file")

start_date = date(2025, 11, 8)
end_date = date.today() - timedelta(days=1)  # Yesterday

total_games = 0
successful = 0
skipped = 0
errors = 0

current_date = start_date
while current_date <= end_date:
    logger.info(f"📆 Processing {current_date}")

    # Get games for this date
    from app.nhl.get_todays_games import get_games_for_date
    schedule_df = get_games_for_date(current_date)

    if schedule_df is None or len(schedule_df) == 0:
        logger.info(f"  No games on {current_date}")
        current_date += timedelta(days=1)
        continue

    # Process games...

    current_date += timedelta(days=1)  # Move to next 
    
    for idx, game_row in schedule_df.iterrows():
      game_id = game_row.get('game_id')
      season = game_row.get('season')
      total_games += 1

      logger.info(f"  [{successful + skipped + errors}/{total_games}] Processing game {game_id}...")

      try:
          # Fetch data
          from app.nhl.service import fetch_game_pbp, fetch_game_box, fetch_moneypuck_player_xg_csv, fetch_game_shifts
          pbp = fetch_game_pbp(game_id, season, ttl_seconds=3600)
          box = fetch_game_box(game_id, season, ttl_seconds=3600)
          xg = fetch_moneypuck_player_xg_csv(game_id, season, ttl_seconds=3600)

          # Calculate snapshot
          from app.nhl.depth_tracker import calculate_game_depth_snapshot
          snapshot = calculate_game_depth_snapshot(game_id, season, pbp, box, xg, allow_final=True)

          if snapshot is None:
              logger.info(f"    ⚠️ No snapshot (insufficient data)")
              skipped += 1
              continue

          # Check if FINAL
          game_state = snapshot.get('game_state', '')
          if game_state not in ['FINAL', 'OFF']:
              logger.info(f"    ⚠️ Not finished (state: {game_state})")
              skipped += 1
              continue

          # Write to master
          from app.nhl.service_depth import write_final_depth
          wrote = write_final_depth(game_id, season, snapshot)

          if wrote:
              successful += 1
              logger.info(f"    ✅ Written to master")
          else:
              skipped += 1

      except Exception as e:
          logger.error(f"    ❌ Error: {e}")
          errors += 1

logger.info(f"\n{'='*60}")
logger.info(f"🏁 BACKFILL COMPLETE")
logger.info(f"Total games: {total_games}")
logger.info(f"✅ Written: {successful}")
logger.info(f"⚠️ Skipped: {skipped}")
logger.info(f"❌ Errors: {errors}")
logger.info(f"📁 Master: s3://hockey-decoded/depth_scores/depth_scores.parquet")

# Update rolling averages file
try:
    from app.nhl.league_stats import save_current_rolling_averages
    save_current_rolling_averages(season=2025)
    logger.info("✅ Rolling averages file updated: s3://hockey-decoded/depth_scores/rolling_averages.json")
except Exception as e:
    logger.error(f"❌ Error updating rolling averages: {e}")