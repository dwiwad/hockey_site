import sys
sys.path.insert(0, '/Users/dwiwad/dev/hockey_site')

import logging

# Enable detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

from app.core.depth_job import track_live_game_depth

print("Running depth tracking job manually...\n")
track_live_game_depth()
print("\n✅ Job completed")