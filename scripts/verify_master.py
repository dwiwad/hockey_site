import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')
import pandas as pd
s3_path = "s3://hockey-decoded/depth_scores/depth_scores.parquet"
print(f"Reading {s3_path}...\n")
df = pd.read_parquet(s3_path, engine='fastparquet')
print(f"✅ Master file has {len(df)} team-games ({len(df)//2} actual games) and {len(df.columns)} columns\n")
print("Columns:", list(df.columns))
print("\n" + "="*80)
print("Sample data (first 4 team-games = 2 games):")
print("="*80)
display_cols = ['game_id', 'team_abbrev', 'opponent_abbrev', 'home_away', 'tdi',
                'sog_depth', 'cf_depth', 'xg_depth', 'toi_depth']
print(df[display_cols].head(4))
# Show rolling average example
if len(df) > 0:
    first_team = df.iloc[0]['team_abbrev']
    team_games = df[df['team_abbrev'] == first_team].sort_values('game_date')
    print(f"\n" + "="*80)
    print(f"Example: {first_team}'s games (for rolling average):")
    print("="*80)
    print(team_games[['game_date', 'opponent_abbrev', 'tdi', 'sog_depth', 'cf_depth']])
    if len(team_games) > 0:
        print(f"\n{first_team}'s average TDI: {team_games['tdi'].mean():.3f}")
        print(f"{first_team}'s average SOG depth: {team_games['sog_depth'].mean():.3f}")