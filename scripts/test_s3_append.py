import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

import logging
from datetime import datetime, timezone
from app.nhl.service_depth import append_live_depth_snapshot
from app.core.config import S3_BUCKET

# Enable logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

# Create a dummy snapshot
dummy_snapshot = {
    'timestamp': datetime.now(timezone.utc),
    'game_id': 9999999,  # Fake game ID so we don't pollute real data
    'season': 20252026,
    'game_date': datetime.now(timezone.utc).date(),
    'period': 1,
    'time_remaining': '15:00',
    'game_state': 'LIVE',
    'home_abbrev': 'TEST',
    'away_abbrev': 'FAKE',
    'home_tdi': 0.5,
    'away_tdi': -0.3,
    'home_weighted_depth': 0.55,
    'away_weighted_depth': 0.52,
    'home_sog_depth': 0.54,
    'away_sog_depth': 0.52,
    'home_cf_depth': 0.61,
    'away_cf_depth': 0.59,
    'home_xg_depth': 0.41,
    'away_xg_depth': 0.39,
    'home_toi_depth': 0.84,
    'away_toi_depth': 0.82,
}

print("Testing S3 append with dummy data...")
print(f"S3 path will be: s3://{S3_BUCKET}/live_game_depth/season=20252026/game_id=9999999.parquet")

# First write - should create new file
print("\n=== First write (should create file) ===")
result1 = append_live_depth_snapshot(9999999, 20252026, dummy_snapshot)
print(f"Result: {result1}")

# Second write immediately - should skip (deduplication)
print("\n=== Second write immediately (should skip - dedupe) ===")
result2 = append_live_depth_snapshot(9999999, 20252026, dummy_snapshot)
print(f"Result: {result2}")

# Third write with updated timestamp - should succeed
print("\n=== Third write with new timestamp (should succeed) ===")
import time
time.sleep(2)  # Wait 2 seconds
dummy_snapshot['timestamp'] = datetime.now(timezone.utc)
dummy_snapshot['time_remaining'] = '14:58'
result3 = append_live_depth_snapshot(9999999, 20252026, dummy_snapshot)
print(f"Result: {result3}")

print("\n✅ Test complete! Check S3 to verify file exists.")
print(f"Path: s3://{S3_BUCKET}/live_game_depth/season=20252026/game_id=9999999.parquet")