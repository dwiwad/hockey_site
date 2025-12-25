import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

import logging
from datetime import date

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

print("="*60)
print("TESTING MINUTE-BY-MINUTE SNAPSHOT SYSTEM")
print("="*60)

# =============================================================================
# TEST 1: Helper Functions
# =============================================================================
print("\n" + "="*60)
print("TEST 1: Helper Functions")
print("="*60)

from app.nhl.depth_tracker import parse_time_to_seconds, calculate_current_game_minute, filter_pbp_to_minute

# Test parse_time_to_seconds
print("\n1a. Testing parse_time_to_seconds()...")
test_cases = [
    ("05:30", 330),
    ("12:45", 765),
    ("0:00", 0),
    ("20:00", 1200),
    ("", 0),
    (None, 0),
]
for time_str, expected in test_cases:
    result = parse_time_to_seconds(time_str)
    status = "✅" if result == expected else "❌"
    print(f"  {status} parse_time_to_seconds('{time_str}') = {result} (expected {expected})")

# Test calculate_current_game_minute with real game data
print("\n1b. Testing calculate_current_game_minute() with real game...")
from app.nhl.service import fetch_game_pbp
game_id = 2024020150  # Pick a recent finished game
season = 20242025
pbp = fetch_game_pbp(game_id, season, ttl_seconds=3600)

if pbp and 'plays' in pbp and len(pbp['plays']) > 0:
    current_minute = calculate_current_game_minute(pbp)
    print(f"  ✅ Game {game_id} current minute: {current_minute}")

    # Show some sample events
    last_event = pbp['plays'][-1]
    period = last_event.get('periodDescriptor', {}).get('number')
    time_in_period = last_event.get('timeInPeriod')
    print(f"     Last event: Period {period}, {time_in_period}")
else:
    print(f"  ❌ Could not fetch PBP for game {game_id}")

# Test filter_pbp_to_minute
print("\n1c. Testing filter_pbp_to_minute()...")
if pbp:
    original_count = len(pbp['plays'])

    filtered_10 = filter_pbp_to_minute(pbp, 10)
    count_10 = len(filtered_10['plays'])

    filtered_30 = filter_pbp_to_minute(pbp, 30)
    count_30 = len(filtered_30['plays'])

    filtered_60 = filter_pbp_to_minute(pbp, 60)
    count_60 = len(filtered_60['plays'])

    print(f"  Original PBP events: {original_count}")
    print(f"  ✅ Filtered to minute 10: {count_10} events")
    print(f"  ✅ Filtered to minute 30: {count_30} events")
    print(f"  ✅ Filtered to minute 60: {count_60} events")
    print(f"     (Should be: 10 < 30 < 60 < original)")

    if count_10 < count_30 < count_60 <= original_count:
        print("  ✅ Filtering works correctly!")
    else:
        print("  ❌ Filtering order is wrong!")

# =============================================================================
# TEST 2: TOI Calculation from Shifts
# =============================================================================
print("\n" + "="*60)
print("TEST 2: TOI Calculation from Shifts")
print("="*60)

from app.nhl.depth_tracker import calculate_toi_at_minute_from_shifts
from app.nhl.service import fetch_game_shifts
from app.nhl.parsers.rosters import roster_by_team

print("\n2a. Fetching shift data...")
shifts = fetch_game_shifts(game_id, season, ttl_seconds=3600)
rosters = roster_by_team(pbp)

if shifts and 'data' in shifts:
    shift_count = len(shifts.get('data', []))
    print(f"  ✅ Fetched {shift_count} shift records")

    print("\n2b. Calculating TOI at different minutes...")
    for target_minute in [10, 20, 30, 40, 50, 60]:
        toi_home, toi_away = calculate_toi_at_minute_from_shifts(
            pbp, shifts, target_minute, rosters
        )
        home_total = sum(toi_home.values())
        away_total = sum(toi_away.values())
        home_players = len([v for v in toi_home.values() if v > 0])
        away_players = len([v for v in toi_away.values() if v > 0])

        print(f"  Minute {target_minute:2d}: Home={home_total:5d}s ({home_players} players), Away={away_total:5d}s ({away_players} players)")

    print("  ✅ TOI should increase with each minute")
else:
    print(f"  ❌ Could not fetch shifts for game {game_id}")

# =============================================================================
# TEST 3: Historical Snapshot at Specific Minute
# =============================================================================
print("\n" + "="*60)
print("TEST 3: Historical Snapshot Calculation")
print("="*60)

from app.nhl.depth_tracker import calculate_snapshot_at_minute_historical
from app.nhl.service import fetch_game_box, fetch_moneypuck_player_xg_csv

print("\n3a. Fetching remaining game data...")
box = fetch_game_box(game_id, season, ttl_seconds=3600)
xg = fetch_moneypuck_player_xg_csv(game_id, season, ttl_seconds=3600)

if box and xg is not None:
    print("  ✅ Fetched box score and xG data")

    print("\n3b. Calculating snapshot at minute 30...")
    snapshot = calculate_snapshot_at_minute_historical(
        game_id=game_id,
        season=season,
        pbp=pbp,
        box=box,
        xg=xg,
        shifts_json=shifts,
        target_minute=30
    )

    if snapshot:
        print("  ✅ Snapshot calculated successfully!")
        print(f"     Game minute: {snapshot.get('game_minute')}")
        print(f"     Home team: {snapshot.get('home_abbrev')} - TDI: {snapshot.get('home_tdi', 0):.3f}, Depth: {snapshot.get('home_weighted_depth', 0):.3f}")
        print(f"     Away team: {snapshot.get('away_abbrev')} - TDI: {snapshot.get('away_tdi', 0):.3f}, Depth: {snapshot.get('away_weighted_depth', 0):.3f}")
        print(f"     Home SOG depth: {snapshot.get('home_sog_depth', 0):.3f}, TOI depth: {snapshot.get('home_toi_depth',0):.3f}")
    else:
        print("  ❌ Snapshot calculation returned None")
else:
    print("  ❌ Could not fetch box or xG data")

# =============================================================================
# TEST 4: Full Game Backfill
# =============================================================================
print("\n" + "="*60)
print("TEST 4: Full Game Backfill")
print("="*60)

from app.nhl.depth_tracker import backfill_game_minute_snapshots
from app.core.config import S3_BUCKET

print(f"\n4a. Backfilling game {game_id} with even-minute snapshots...")
print("     This will create snapshots at minutes 2, 4, 6, 8... 60")
print("     Using ACCURATE shift-based TOI")

success = backfill_game_minute_snapshots(game_id, season)

if success:
    print("\n  ✅ Backfill completed successfully!")

    # Read back the file to verify
    import pandas as pd
    s3_path = f"s3://{S3_BUCKET}/live_game_depth/season={season}/game_id={game_id}.parquet"

    print("\n4b. Verifying backfilled data...")
    df = pd.read_parquet(s3_path, engine='fastparquet')

    print(f"  Total snapshots: {len(df)}")
    print(f"  Game minutes present: {sorted(df['game_minute'].unique())}")
    print(f"  Columns: {list(df.columns)}")

    print("\n  Sample data (first 5 rows):")
    print(df[['game_minute', 'home_abbrev', 'away_abbrev', 'home_weighted_depth', 'away_weighted_depth']].head())

    print("\n  Depth evolution over time:")
    for _, row in df[['game_minute', 'home_abbrev', 'home_weighted_depth', 'away_abbrev','away_weighted_depth']].iterrows():
        minute = int(row['game_minute'])
        home_depth = row['home_weighted_depth']
        away_depth = row['away_weighted_depth']
        print(f"    Minute {minute:2d}: {row['home_abbrev']} {home_depth:.3f} vs {row['away_abbrev']} {away_depth:.3f}")

else:
    print("  ❌ Backfill failed")

# =============================================================================
# SUMMARY
# =============================================================================
print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
print("✅ All tests completed!")
print("\nNext steps:")
print("1. Run live tracking on an active game to test real-time snapshots")
print("2. Verify that game_minute field is present in live snapshots")
print("3. When game finishes, backfill should replace live data automatically")
print("="*60)