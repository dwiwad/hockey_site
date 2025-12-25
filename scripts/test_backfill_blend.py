import sys
sys.path.insert(0, '.')

from app.nhl.depth_tracker import backfill_game_minute_snapshots
import pandas as pd
import s3fs
from app.core.config import S3_BUCKET

# Test on game 2025020534 (the one with Oilers volatility)
game_id = 2025020534
season = 20252026

print(f"Testing blending on game {game_id}...")
print()

# Run the backfill with new blending logic
success = backfill_game_minute_snapshots(game_id, season)

if success:
    print("✅ Backfill completed!")
    print()
    print("Reading results...")

    # Read the backfilled data
    s3 = s3fs.S3FileSystem(anon=False)
    s3_path = f's3://{S3_BUCKET}/live_game_depth/season={season}/game_id={game_id}.parquet'

    from fastparquet import ParquetFile
    with s3.open(s3_path, 'rb') as f:
        pf = ParquetFile(f)
        df = pf.to_pandas()

    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 300)
    pd.set_option('display.float_format', lambda x: f'{x:.3f}')

    print(f"Total snapshots: {len(df)}")
    print()
    print("First 15 snapshots (first 30 minutes):")
    print()

    cols = ['game_minute', 'home_weighted_depth', 'away_weighted_depth',
            'debug_home_shots', 'debug_away_shots',
            'debug_home_live_weight', 'debug_away_live_weight',
            'debug_blending_occurred']

    print(df[cols].head(30).to_string(index=False))

    print()
    print("What to look for:")
    print("1. Early minutes should have low weights (0.0 - 0.3)")
    print("2. Weights should gradually increase")
    print("3. By minute 30-40, weights should be near 1.0")
    print("4. home_weighted_depth and away_weighted_depth should be smoother (no wild swings)")
    print("5. debug_blending_occurred should be True")
else:
    print("❌ Backfill failed")