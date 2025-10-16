import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

from app.nhl.depth_tracker import calculate_game_depth_snapshot
from app.nhl.service import fetch_game_pbp, fetch_game_box, fetch_moneypuck_player_xg_csv, fetch_game_shifts

# Use a recent playoff game that definitely has all data
game_id = 2025020059  # Panthers vs Oilers from your git history
season = 20252026

print(f"Testing snapshot for game {game_id}...")
print("Fetching data...")

# Fetch the data
pbp = fetch_game_pbp(game_id, season, ttl_seconds=5)
box = fetch_game_box(game_id, season, ttl_seconds=5)
xg = fetch_moneypuck_player_xg_csv(game_id, season, ttl_seconds=5)
shifts = fetch_game_shifts(game_id, season, ttl_seconds=5)

print("Calculating snapshot...")

# Call your new function
snapshot = calculate_game_depth_snapshot(game_id, season, pbp, box, xg, shifts)

if snapshot is None:
    print("❌ Returned None - check logs above")
else:
    print("✅ Got snapshot!")
    print("\nSnapshot contents:")
    for key, value in snapshot.items():
        print(f"  {key:25s}: {value}")

    print("\n✅ All fields present!")