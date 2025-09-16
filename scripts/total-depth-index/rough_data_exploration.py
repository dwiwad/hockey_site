"""
Created on Tue Sep 16 07:45:52 2025

@author: dwiwad
"""
import requests
import pandas as pd
from datetime import date, timedelta

##############################################################################
#
# GET THE GAME IDS
#
##############################################################################

# I think first we maybe need all play by play data for the 2024-2025 season
# So maybe let's start with just getting every game_id
# Preseason: September 21, 2024 to October 3, 2024
# Regular season: October 4, 2024 to April 17, 2024
# Playoffs: April 18, 2024 to June 24, 2024

# Helper, get mondays in a range inclusive
def get_mondays(start_date, end_date):
    # empty list and date to use
    mondays = []
    current_date = start_date
    # If current date is not a monday, add a day
    while current_date.weekday() != 0:
        current_date +- timedelta(days=1)
    # If the current day is less than the end day, keep going to the next week
    # And also, if current date is a monday, add to list
    while current_date <= end_date:
        mondays.append(current_date)
        current_date += timedelta(weeks=1)
    return mondays

start_date = date(2024, 9, 16)
end_date = date(2025, 6, 23)

mondays = get_mondays(start_date, end_date)

# Okay now a function to get all the games
# Just takes a monday, pulls the games for that week, appends to list if there are games, returns it
def get_all_games(list_of_mondays):
    
    # Initialize a list
    games = []
    
    for monday in list_of_mondays:
        # Make the url, pull the data from that day
        url = f"https://api-web.nhle.com/v1/schedule/{ monday }"
        response = requests.get(url)
        data = response.json()
        
        # Pull the game data for every day that week
        for i in range(7):
            game_list = data['gameWeek'][i]['games']
            if len(game_list) > 0:
                games.extend(game_list)
    
    return games
   
# Get Games last season 
games = get_all_games(mondays)
games = pd.json_normalize(games)

##############################################################################
#
# GET THE PLAY BY PLAY FOR EVERY GAME
#
##############################################################################    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    