import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')
from app.nhl.league_stats import save_current_rolling_averages
from app.core.config import get_current_season

# This will read the master parquet and save rolling_averages.json to S3
result = save_current_rolling_averages(season=get_current_season())
print(f"Saved rolling averages for {len(result['data'])} teams")