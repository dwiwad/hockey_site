import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

import pandas as pd
from app.nhl.parsers.rosters import roster_by_team
from app.nhl.service import fetch_game_pbp

# Live roster
pbp = fetch_game_pbp(2024030416, 20232024, ttl_seconds=5)
rosters = roster_by_team(pbp)

edm_live = [r for r in rosters if r.get('teamAbbrev') == 'EDM' and r.get('positionCode') != 'G']
fla_live = [r for r in rosters if r.get('teamAbbrev') == 'FLA' and r.get('positionCode') != 'G']

print(f"Live EDM skaters: {len(edm_live)}")
print(f"Live FLA skaters: {len(fla_live)}")

# Historical roster
df_rosters = pd.read_csv('/Users/dwiwad/dev/hockey_site/data/total-depth-index/all_seasons/all_rosters_20102025.csv')
game_rosters = df_rosters[df_rosters['game_id'] == 2024030416]

edm_hist = game_rosters[(game_rosters['teamAbbrev'] == 'EDM') & (game_rosters['positionCode'] != 'G')]
fla_hist = game_rosters[(game_rosters['teamAbbrev'] == 'FLA') & (game_rosters['positionCode'] != 'G')]

print(f"Historical EDM skaters: {len(edm_hist)}")
print(f"Historical FLA skaters: {len(fla_hist)}")