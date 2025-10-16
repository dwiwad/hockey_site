import logging
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


def _parse_game_start_time(start_str: str, game_date) -> datetime:
    """
    Parse NHL start time string like '7:00 PM ET' to datetime.
    """
    if not start_str:
        return None
    match = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', start_str)

    if not match:
        return None
    
    hour = int(match.group(1))
    minute = int(match.group(2))
    am_pm = match.group(3)

    if am_pm == 'PM' and hour != 12:
        hour += 12
    elif am_pm == 'AM' and hour == 12:
        hour = 0

    try:
        return datetime.combine(game_date, datetime.min.time().replace(hour=hour, minute=minute))
    except ValueError:
        return None


def schedule_depth_tracking_for_today():
    """
    Manager job that runs once per day at 5 AM.
    
    Checks today's schedule and dynamically adds the minute-by-minute
    tracking job ONLY if games are scheduled.
    """
    logger.info("=== Depth tracking scheduler manager started ===")

    # Get today's schedule
    today = datetime.now().date()
    from app.nhl.get_todays_games import get_games_for_date
    schedule_df = get_games_for_date(today)

    # No games today - don't schedule anything
    if schedule_df is None or len(schedule_df) == 0:
        logger.info("No games today - depth tracking will not run")
        return

    # Find earliest game start time
    earliest_start = None
    for _, game in schedule_df.iterrows():
        start_str = game.get('start')
        if start_str:
            game_start = _parse_game_start_time(start_str, today)
            if game_start:
                if earliest_start is None or game_start < earliest_start:
                    earliest_start = game_start

    if not earliest_start:
        logger.warning("Games scheduled but couldn't parse start times - defaulting to 4 PM start")
        earliest_start = datetime.combine(today, datetime.min.time().replace(hour=16))

    # Calculate tracking window
    tracking_start = earliest_start - timedelta(minutes=30)
    tracking_end = datetime.combine(today, datetime.min.time().replace(hour=2)) + timedelta(days=1)  # 2 AM next day

    logger.info(f"Games today! Scheduling depth tracking from {tracking_start.strftime('%I:%M %p')} to {tracking_end.strftime('%I:%M %p')}")

    # Get scheduler and add the minute-by-minute job
    from fastapi import FastAPI
    from app.core.scheduler import get_scheduler
    from apscheduler.triggers.cron import CronTrigger

    scheduler = get_scheduler()

    # Remove existing tracking job if it exists
    try:
        scheduler.remove_job('track_live_depth_active')
    except:
        pass

    # Add minute-by-minute job for today's game window
    scheduler.add_job(
        track_live_game_depth,
        trigger=CronTrigger(
            hour=f'{tracking_start.hour}-23,0-{tracking_end.hour}',
            minute='*'
        ),
        id='track_live_depth_active',
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=30,
    )

    logger.info("Depth tracking job scheduled for today's game window")


def track_live_game_depth():
    """
    Minute-by-minute tracking job.
    Only runs during scheduled window (added by manager job).
    """
    logger.info("=== Depth tracking job started ===")

    # Get active games
    from app.nhl.get_todays_games import get_active_games
    active_games = get_active_games()

    if not active_games:
        logger.debug("No active games to track")
        return

    logger.info(f"Tracking {len(active_games)} active game(s)")

    tracked_count = 0
    finalized_count = 0

    # Process each active game
    for game_id, season in active_games:
        try:
            logger.info(f"Processing game {game_id}...")

            # Fetch game data
            from app.nhl.service import fetch_game_pbp, fetch_game_box, fetch_moneypuck_player_xg_csv, fetch_game_shifts
            pbp = fetch_game_pbp(game_id, season, ttl_seconds=5)
            box = fetch_game_box(game_id, season, ttl_seconds=5)
            xg = fetch_moneypuck_player_xg_csv(game_id, season, ttl_seconds=5)
            shifts = fetch_game_shifts(game_id, season, ttl_seconds=5)

            # Calculate snapshot
            from app.nhl.depth_tracker import calculate_game_depth_snapshot
            snapshot = calculate_game_depth_snapshot(game_id, season, pbp, box, xg, shifts)

            if snapshot is None:
                logger.info(f"Game {game_id} - no snapshot (pregame/intermission/insufficient data)")
                continue

            # Append to live tracking
            from app.nhl.service_depth import append_live_depth_snapshot, write_final_depth
            wrote_live = append_live_depth_snapshot(game_id, season, snapshot)
            if wrote_live:
                tracked_count += 1

            # Check if game finished
            game_state = snapshot.get('game_state', '')
            if game_state in ['FINAL', 'OFF']:
                logger.info(f"Game {game_id} finished - writing to master")
                wrote_final = write_final_depth(game_id, season, snapshot)
                if wrote_final:
                    finalized_count += 1

        except Exception as e:
            logger.error(f"Error processing game {game_id}: {e}", exc_info=True)
            continue

    logger.info(f"=== Depth tracking complete: tracked {tracked_count}, finalized {finalized_count} ===")