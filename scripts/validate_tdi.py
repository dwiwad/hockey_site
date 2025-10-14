"""
Validate that Python TDI implementation matches R lavaan results.
"""
import pandas as pd
import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

from app.nhl.parsers.depth import calculate_tdi

# Load your training data
df = pd.read_csv('/Users/dwiwad/dev/hockey_site/data/total-depth-index/all_seasons/final_data_20102025.csv')

print(f"Loaded {len(df)} team-games")
print("\nTesting Python TDI vs R tdi_factor...\n")

# Test on first 10 rows
errors = []
for i in range(10):
    row = df.iloc[i]

    # Calculate using Python
    python_tdi = calculate_tdi(
      cf_gini=row['cf_gini'],
      sog_gini=row['sog_gini'],
      toi_gini=row['toi_gini'],
      xgoal_gini=row['xgoal_gini']
    )

    # Compare to R
    r_tdi = row['tdi_factor']
    diff = abs(python_tdi - r_tdi)

    print(f"Row {i}: Python={python_tdi:.4f}, R={r_tdi:.4f}, Diff={diff:.6f}")

    if diff > 0.01:  # tolerance
        errors.append((i, diff))

print("\n" + "="*60)
if errors:
    print(f"⚠️  WARNING: {len(errors)} rows had differences > 0.01")
    for idx, diff in errors:
        print(f"  Row {idx}: difference = {diff:.6f}")
else:
    print("✅ SUCCESS: All test cases match within tolerance!")
print("="*60)

# Statistical summary across all rows
df['python_tdi'] = df.apply(
    lambda row: calculate_tdi(row['cf_gini'], row['sog_gini'], row['toi_gini'], row['xgoal_gini']),
    axis=1
)
df['tdi_diff'] = abs(df['python_tdi'] - df['tdi_factor'])

print(f"\nStats across all {len(df)} rows:")
print(f"  Mean absolute difference: {df['tdi_diff'].mean():.6f}")
print(f"  Max absolute difference:  {df['tdi_diff'].max():.6f}")
print(f"  Rows with diff > 0.01:    {(df['tdi_diff'] > 0.01).sum()}")