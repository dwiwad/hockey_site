import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

import logging
from datetime import datetime, timezone
from app.nhl.service_depth import write_final_depth
import s3fs

# Enable logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

# Clean up any existing test master file
print("Cleaning up any existing test master file...")

s3 = s3fs.S3FileSystem()
test_path = 'hockey-decoded/depth_scores/depth_scores_test.parquet'

if s3.exists(test_path):
    s3.rm(test_path)
    print("✅ Deleted old test file\n")
else:
    print("✅ No old test file to clean\n")

# Create dummy FINAL game snapshot
dummy_snapshot = {
    'timestamp': datetime.now(timezone.utc),
    'game_id': 8888888,  # Fake game ID
    'season': 20252026,
    'game_date': datetime.now(timezone.utc).date(),
    'period': 3,
    'time_remaining': '00:00',
    'game_state': 'FINAL',
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

print("Testing master file write...")
print(f"Master path: s3://hockey-decoded/depth_scores/depth_scores.parquet\n")

# First write - should create file
print("=== First write (should create master file) ===")
result1 = write_final_depth(8888888, 20252026, dummy_snapshot)
print(f"Result: {result1}\n")

# Second write with same game_id - should skip (idempotency)
print("=== Second write same game (should skip - idempotency) ===")
result2 = write_final_depth(8888888, 20252026, dummy_snapshot)
print(f"Result: {result2}\n")

# Third write with different game_id - should succeed
print("=== Third write different game (should succeed) ===")
dummy_snapshot['game_id'] = 8888889
dummy_snapshot['home_tdi'] = 1.2
dummy_snapshot['away_tdi'] = -0.8

result3 = write_final_depth(8888889, 20252026, dummy_snapshot)

print(f"Result: {result3}\n")
print("✅ Test complete! Check S3 to verify master file.")
print("Path: s3://hockey-decoded/depth_scores/depth_scores.parquet")