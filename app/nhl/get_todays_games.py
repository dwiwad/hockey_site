"""
Get today's NHL games and return a dataframe of game_id, away team, and home team.
Intended to run daily at 3am Central to power live dashboards.

Created on Sat Aug 16 09:32:12 2025

@author: dwiwad
"""
# The API endpoint that has the games is:
# https://api-web.nhle.com/v1/schedule/now"

import requests 
import pandas as pd
from datetime import date

def get_todays_games():

    # FOR NOW, JUST MAKE THIS THE FIRST DAY SO WE HAVE SOMETHING TO WORK WITH
    # today = date.today()
    # url = f'https://api-web.nhle.com/v1/schedule/{today}'
    url = 'https://api-web.nhle.com/v1/schedule/2025-03-13'
    
    try:
        response = requests.get(url)
        data = response.json()
        
        # Pull the first block of today's games
        game_list = data['gameWeek'][0]['games']
        
        # Flatten the json
        games = pd.json_normalize(game_list)
        
        # Convert start to datetime in UTC
        games["start_dt"] = pd.to_datetime(games["startTimeUTC"], utc=True)

        # Convert to Eastern Time (IANA tz name for NY covers DST automatically)
        games["start_et"] = games["start_dt"].dt.tz_convert("America/New_York")
        
        # Format as string (e.g., "7:00 PM ET")
        games["start_et_str"] = games["start_et"].dt.strftime("%I:%M %p ET")
        
        # Just pull the needed variables and return as a df
        return pd.DataFrame({
                'game_id': games['id'],
                'start': games['start_et_str'],
                'away': games['awayTeam.commonName.default'],
                'home': games['homeTeam.commonName.default'],
                'away_tri': games['awayTeam.abbrev'],
                'home_tri': games['homeTeam.abbrev']
            })
    
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"Error fetching NHL schedule: {e}")
        return pd.DataFrame(columns=['game_id', 'start', 'away', 'home'])

# Run the script when needed
if __name__ == "__main__":
    print(get_todays_games())
    
games_today_df = get_todays_games()
games_today = games_today_df.to_dict(orient="records")
