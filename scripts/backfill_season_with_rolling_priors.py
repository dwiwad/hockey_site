#!/usr/bin/env python3
"""
  HISTORICAL SEASON BACKFILL - Isolated Version
  Uses season-specific depth_scores files to avoid touching production data.

  Usage:
      python scripts/backfill_season_isolated.py --season 20172018
      python scripts/backfill_season_isolated.py --season 20172018 --start-from 2017-12-01
      python scripts/backfill_season_isolated.py --season 20172018 --max-games 50
  """

import sys
import argparse
import logging
from datetime import date, timedelta, datetime
from pathlib import Path

sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

logging.basicConfig(
      level=logging.INFO,
      format='%(asctime)s - %(levelname)s - %(message)s',
      datefmt='%H:%M:%S'
  )
logger = logging.getLogger(__name__)

  # Historical rolling averages directory
HISTORICAL_DIR = Path('/Users/dwiwad/dev/hockey_site/historical_backfill')
HISTORICAL_DIR.mkdir(exist_ok=True)


def write_final_depth_for_season(game_id: int, season: int, snapshot: dict) -> bool:
      """
      Write final depth scores to SEASON-SPECIFIC parquet file (isolated from production).
      
      Path: s3://{S3_BUCKET}/depth_scores/season={season}/depth_scores.parquet
      """
      import pandas as pd
      from app.core.config import S3_BUCKET

      # Season-specific file path (NOT the master file)
      s3_path = f"s3://{S3_BUCKET}/depth_scores/season={season}/depth_scores.parquet"

      # Convert game_date to string
      game_date = snapshot['game_date']
      if hasattr(game_date, 'isoformat'):
          game_date = game_date.isoformat()

      # Try to read existing file
      try:
          existing_df = pd.read_parquet(s3_path, engine='fastparquet')
      except FileNotFoundError:
          logger.info(f"      Creating new depth scores file for season {season}")
          existing_df = None
      except Exception as e:
          logger.error(f"      Error reading {s3_path}: {e}")
          return False

      # Check if game already exists (idempotency)
      if existing_df is not None and game_id in existing_df['game_id'].values:
          logger.debug(f"      Game {game_id} already in file, skipping")
          return False

      # Transform to long format (2 rows - one per team)
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
          'total_xg': snapshot['home_total_xg'],
          'goals': snapshot['home_goals'],
          'opponent_total_xg': snapshot['away_total_xg'],
          'opponent_goals': snapshot['away_goals'],
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
          'total_xg': snapshot['away_total_xg'],
          'goals': snapshot['away_goals'],
          'opponent_total_xg': snapshot['home_total_xg'],
          'opponent_goals': snapshot['home_goals'],
      }

      new_rows = pd.DataFrame([home_record, away_record])

      # Append or create
      if existing_df is not None:
          combined_df = pd.concat([existing_df, new_rows], ignore_index=True)
      else:
          combined_df = new_rows

      # Write to S3
      try:
          combined_df.to_parquet(
              s3_path,
              engine='fastparquet',
              compression='snappy',
              index=False
          )
          logger.debug(f"      Wrote to season-specific file ({len(combined_df)} total rows)")
          return True
      except Exception as e:
          logger.error(f"      Error writing to {s3_path}: {e}")
          return False


def save_rolling_averages_for_season(season: int):
      """
      Calculate rolling averages for a season from its SEASON-SPECIFIC depth scores file.
      """
      import pandas as pd
      import json
      from app.core.config import S3_BUCKET

      logger.debug(f"   Calculating rolling averages...")

      try:
          # Read SEASON-SPECIFIC depth scores file
          s3_path = f"s3://{S3_BUCKET}/depth_scores/season={season}/depth_scores.parquet"
          df = pd.read_parquet(s3_path, engine='fastparquet')

          if len(df) == 0:
              logger.warning(f"   No games found")
              return

          # Sort by date
          df['game_date'] = pd.to_datetime(df['game_date'])
          df = df.sort_values(['team_abbrev', 'game_date', 'game_id'])

          # Calculate Ginis from depths
          df['shot_gini'] = 1 - df['sog_depth']
          df['cf_gini'] = 1 - df['cf_depth']
          df['xg_gini'] = 1 - df['xg_depth']
          df['toi_gini'] = 1 - df['toi_depth']

          # Calculate 10-game rolling averages by team (min_periods=1)
          rolling_data = {}

          for team in df['team_abbrev'].unique():
              team_df = df[df['team_abbrev'] == team].copy()

              # Rolling averages
              team_df['rolling_weighted_depth'] = team_df['weighted_depth'].rolling(
                  window=10, min_periods=1
              ).mean()
              team_df['rolling_shot_gini'] = team_df['shot_gini'].rolling(
                  window=10, min_periods=1
              ).mean()
              team_df['rolling_cf_gini'] = team_df['cf_gini'].rolling(
                  window=10, min_periods=1
              ).mean()
              team_df['rolling_xg_gini'] = team_df['xg_gini'].rolling(
                  window=10, min_periods=1
              ).mean()
              team_df['rolling_toi_gini'] = team_df['toi_gini'].rolling(
                  window=10, min_periods=1
              ).mean()

              # Get most recent values
              latest = team_df.iloc[-1]

              rolling_data[team] = {
                  'weighted_depth': float(latest['rolling_weighted_depth']),
                  'shot_gini': float(latest['rolling_shot_gini']),
                  'cf_gini': float(latest['rolling_cf_gini']),
                  'xg_gini': float(latest['rolling_xg_gini']),
                  'toi_gini': float(latest['rolling_toi_gini']),
                  'games_count': len(team_df)
              }

          # Save to historical directory
          output_file = HISTORICAL_DIR / f'rolling_averages_{season}.json'
          with open(output_file, 'w') as f:
              json.dump(rolling_data, f, indent=2)

          logger.debug(f"   Rolling averages: {len(rolling_data)} teams")

      except FileNotFoundError:
          logger.debug(f"   No depth scores file yet for season {season}")
      except Exception as e:
          logger.error(f"   Failed to calculate rolling averages: {e}")


def backfill_game_isolated(game_id: int, season: int) -> tuple[bool, bool]:
      """
      Backfill a single game using season-specific files (completely isolated).
      
      Returns: (depth_scores_success, minutes_success)
      """
      from app.nhl.service import fetch_game_pbp, fetch_game_box, fetch_moneypuck_player_xg_csv
      from app.nhl.depth_tracker import calculate_game_depth_snapshot

      # Step 1: Calculate and save final depth scores
      try:
          pbp = fetch_game_pbp(game_id, season, ttl_seconds=3600)
          box = fetch_game_box(game_id, season, ttl_seconds=3600)
          xg = fetch_moneypuck_player_xg_csv(game_id, season, ttl_seconds=3600)

          snapshot = calculate_game_depth_snapshot(game_id, season, pbp, box, xg, allow_final=True)

          if snapshot is None:
              return False, False

          # Write to SEASON-SPECIFIC file (not master)
          wrote = write_final_depth_for_season(game_id, season, snapshot)

          if not wrote:
              return False, False

      except Exception as e:
          logger.debug(f"      Depth scores error: {e}")
          return False, False

      # Step 2: Backfill minute-by-minute with season-specific rolling averages
      try:
          # Load season-specific rolling averages
          rolling_avgs_file = HISTORICAL_DIR / f'rolling_averages_{season}.json'
          if rolling_avgs_file.exists():
              import json
              with open(rolling_avgs_file, 'r') as f:
                  rolling_avgs = json.load(f)
          else:
              rolling_avgs = {}

          # Temporarily monkey-patch to use season-specific rolling averages
          import app.nhl.league_stats
          original_func = app.nhl.league_stats.get_current_rolling_averages

          def get_season_rolling_averages(season=None):
              return rolling_avgs

          app.nhl.league_stats.get_current_rolling_averages = get_season_rolling_averages

          try:
              # Use existing production function
              from app.nhl.depth_tracker import backfill_game_minute_snapshots
              minutes_success = backfill_game_minute_snapshots(game_id, season)
          finally:
              # Restore original function
              app.nhl.league_stats.get_current_rolling_averages = original_func

          return True, minutes_success

      except Exception as e:
          logger.debug(f"      Minutes error: {e}")
          return True, False


def backfill_season(season: int, start_date: date = None, max_games: int = None):
      """Main backfill workflow."""
      from app.nhl.get_todays_games import get_games_for_date

      logger.info(f"\n{'='*70}")
      logger.info(f"🏒 HISTORICAL BACKFILL FOR SEASON {season}")
      logger.info(f"{'='*70}")

      # Season date ranges
      season_ranges = {
          20172018: (date(2017, 10, 1), date(2018, 6, 30)),
          20182019: (date(2018, 10, 1), date(2019, 6, 30)),
          20192020: (date(2019, 10, 1), date(2020, 10, 1)),
          20202021: (date(2021, 1, 13), date(2021, 10, 1)),
          20212022: (date(2021, 10, 1), date(2022, 6, 30)),
          20222023: (date(2022, 10, 1), date(2023, 6, 30)),
          20232024: (date(2023, 10, 1), date(2024, 6, 30)),
      }

      if season not in season_ranges:
          logger.error(f"❌ Unsupported season: {season}")
          return

      season_start, season_end = season_ranges[season]

      if start_date:
          season_start = max(start_date, season_start)

      logger.info(f"📅 Date range: {season_start} to {season_end}")
      logger.info(f"📂 Season-specific S3: depth_scores/season={season}/")
      logger.info(f"📂 Rolling averages: {HISTORICAL_DIR}/rolling_averages_{season}.json")
      logger.info("")

      # Counters
      total_games = 0
      successful_scores = 0
      successful_minutes = 0
      failed = 0

      # Iterate through dates
      current_date = season_start
      while current_date <= season_end:
          if max_games and total_games >= max_games:
              logger.info(f"\n⏸️  Reached max_games limit ({max_games})")
              break

          logger.info(f"📆 {current_date.strftime('%Y-%m-%d')} ({current_date.strftime('%A')})")

          schedule_df = get_games_for_date(current_date)

          if schedule_df is None or len(schedule_df) == 0:
              logger.info(f"   No games scheduled")
              current_date += timedelta(days=1)
              continue

          logger.info(f"   Found {len(schedule_df)} game(s)")

          for idx, game_row in schedule_df.iterrows():
              game_id = game_row.get('game_id')
              game_season = game_row.get('season')
              home = game_row.get('home_tri')
              away = game_row.get('away_tri')

              if game_season != season:
                  continue

              total_games += 1
              logger.info(f"   🎯 Game {total_games}: {away} @ {home} (ID: {game_id})")

              # Backfill this game
              scores_ok, minutes_ok = backfill_game_isolated(game_id, season)

              if scores_ok:
                  successful_scores += 1
                  logger.info(f"      ✅ Depth scores saved")

                  # Recalculate rolling averages
                  logger.info(f"      🔄 Updating rolling averages...")
                  save_rolling_averages_for_season(season)
              else:
                  logger.warning(f"      ⚠️  Could not calculate depth scores")

              if minutes_ok:
                  successful_minutes += 1
                  logger.info(f"      ✅ Minute-by-minute backfilled")
              else:
                  logger.warning(f"      ⚠️  Minute-by-minute failed")

              if not scores_ok and not minutes_ok:
                  failed += 1

              logger.info("")

          current_date += timedelta(days=1)

      # Summary
      logger.info(f"\n{'='*70}")
      logger.info(f"🏁 BACKFILL COMPLETE")
      logger.info(f"{'='*70}")
      logger.info(f"📊 Total games: {total_games}")
      logger.info(f"✅ Depth scores: {successful_scores}")
      logger.info(f"✅ Minute-by-minute: {successful_minutes}")
      logger.info(f"❌ Failed: {failed}")

      # Show final rolling averages
      rolling_file = HISTORICAL_DIR / f'rolling_averages_{season}.json'
      if rolling_file.exists():
          import json
          with open(rolling_file, 'r') as f:
              rolling_data = json.load(f)
          logger.info(f"\n📈 Final rolling averages: {len(rolling_data)} teams")
          for i, (team, data) in enumerate(list(rolling_data.items())[:5]):
              logger.info(f"   {team}: {data['games_count']} games, depth={data['weighted_depth']:.3f}")

      logger.info(f"{'='*70}\n")


def main():
      parser = argparse.ArgumentParser(description='Backfill historical NHL season (isolated)')
      parser.add_argument('--season', type=int, required=True)
      parser.add_argument('--start-from', type=str, help='Start date YYYY-MM-DD')
      parser.add_argument('--max-games', type=int, help='Max games to process')

      args = parser.parse_args()

      start_date = None
      if args.start_from:
          try:
              start_date = datetime.strptime(args.start_from, '%Y-%m-%d').date()
          except ValueError:
              logger.error(f"Invalid date: {args.start_from}")
              sys.exit(1)

      backfill_season(args.season, start_date, args.max_games)


if __name__ == '__main__':
      main()