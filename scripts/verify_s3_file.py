import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

import pandas as pd
from app.core.config import S3_BUCKET

s3_path = f"s3://{S3_BUCKET}/live_game_depth/season=20252026/game_id=9999999.parquet"

print(f"Reading {s3_path}...\n")
df = pd.read_parquet(s3_path, engine='fastparquet')

print(f"✅ File has {len(df)} rows and {len(df.columns)} columns\n")
print("Columns:", list(df.columns))
print("\n" + "="*80)
print("First row:")
print("="*80)
for col in df.columns:
    print(f"{col:25s}: {df.iloc[0][col]}")

if len(df) > 1:
    print("\n" + "="*80)
    print("Last row:")
    print("="*80)
    for col in df.columns:
        print(f"{col:25s}: {df.iloc[-1][col]}")
else:
    print("\n(Only one row in file)")