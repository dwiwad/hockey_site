import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')
from app.nhl.league_stats import save_current_rolling_averages

# This will read the master parquet and save rolling_averages.json to S3
result = save_current_rolling_averages(season=2025)
print(f"Saved rolling averages for {len(result['data'])} teams")