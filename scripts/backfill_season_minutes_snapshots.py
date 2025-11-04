import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

import logging
from datetime import date, timedelta

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Date range: Oct 5, 2024 to today
start_date = date(2025, 11, 1)
end_date = date.today()

logger.info(f"🏒 Backfilling 2024-2025 season from {start_date} to {end_date}")

from app.nhl.get_todays_games import get_games_for_date
from app.nhl.depth_tracker import backfill_game_minute_snapshots

total_games = 0
successful = 0
failed = 0
skipped = 0

current_date = start_date
while current_date <= end_date:
    logger.info(f"📆 Processing {current_date}")

    schedule_df = get_games_for_date(current_date)

    if schedule_df is None or len(schedule_df) == 0:
        logger.info(f"  No games on {current_date}")
        current_date += timedelta(days=1)
        continue

    logger.info(f"  Found {len(schedule_df)} game(s)")

    for idx, game_row in schedule_df.iterrows():
        game_id = game_row.get('game_id')
        season = game_row.get('season')
        home = game_row.get('home_tri')
        away = game_row.get('away_tri')
        total_games += 1

        logger.info(f"  [{successful + failed + skipped}/{total_games}] {away} @ {home} (game {game_id})")

        try:
            success = backfill_game_minute_snapshots(game_id, season)
            if success:
                successful += 1
                logger.info(f"    ✅ Success")
            else:
                skipped += 1
                logger.info(f"    ⚠️  Skipped (insufficient data)")
        except Exception as e:
            logger.error(f"    ❌ Error: {e}")
            failed += 1

    current_date += timedelta(days=1)

logger.info(f"\n{'='*60}")
logger.info(f"🏁 SEASON BACKFILL COMPLETE")
logger.info(f"Total games: {total_games}")
logger.info(f"✅ Success: {successful}")
logger.info(f"⚠️  Skipped: {skipped}")
logger.info(f"❌ Failed: {failed}")
logger.info(f"{'='*60}")