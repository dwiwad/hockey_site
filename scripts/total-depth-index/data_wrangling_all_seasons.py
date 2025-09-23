"""
Created on Tue Sep 16 07:45:52 2025

@author: dwiwad
"""
import requests
import pandas as pd
import numpy as np
from datetime import date, timedelta
import time
from wakepy import keep
import statsmodels.formula.api as smf
from scipy.stats import zscore

##############################################################################
#
# GET THE GAME DATA THAT I NEED
#
##############################################################################

##############################################################################
# GAME IDS
##############################################################################

# Getting every game_id from 2010 to 2025


# Helper, get mondays in a range inclusive
def get_mondays(start_date, end_date):
    # empty list and date to use
    mondays = []
    current_date = start_date
    # If current date is not a monday, add a day
    while current_date.weekday() != 0:
        current_date += timedelta(days=1)
    # If the current day is less than the end day, keep going to the next week
    # And also, if current date is a monday, add to list
    while current_date <= end_date:
        mondays.append(current_date)
        current_date += timedelta(weeks=1)
    return mondays

# Pull every monday for 15 years
start_date = date(2010, 9, 1)
end_date = date(2025, 6, 23)

mondays = get_mondays(start_date, end_date)

# Okay now a function to get all the games
# Just takes a monday, pulls the games for that week, appends to list if there are games, returns it
def get_all_games(list_of_mondays):
    
    # Initialize a list
    games = []
    n = 1
    
    for monday in list_of_mondays:
        print(f"Working on week { n } of { len(list_of_mondays) }")
        # Make the url, pull the data from that day
        url = f"https://api-web.nhle.com/v1/schedule/{ monday }"
        response = requests.get(url)
        data = response.json()
        
        # Pull the game data for every day that week
        for i in range(7):
            game_list = data['gameWeek'][i]['games']
            if len(game_list) > 0:
                games.extend(game_list)
        n += 1
        
        # Add a quick pause to be polite
        time.sleep(2)
    
    return games
   
# Fetch and flatten
with keep.running():
    games= get_all_games(mondays)

games = pd.json_normalize(games)

# Save the file for later
games.to_csv('~/dev/hockey_site/data/total-depth-index/all_games_meta_20102025.csv', index=False)

##############################################################################
# GAME PLAY-BY-PLAY
##############################################################################   

# Function to get the play by play data for every game
def fetch_game_pbp(list_of_games):
    
    # Initialize a list
    plays = []
    n = 1
    
    for game in list_of_games:
        print(f"working on game { n } of { len(list_of_games) }")
        # Build the actual url and make the call
        url = f"https://api-web.nhle.com/v1/gamecenter/{ game }/play-by-play"
        response = requests.get(url)
        data = response.json()
        
        # I need to add a game_id to each play
        for d in data['plays']:
            d['game_id'] = game
        
        plays.extend(data['plays'])
        
        n += 1
        
        # Add a quick pause to be polite
        time.sleep(2)
    
    return plays

# Get the list of games:
list_of_games = games['id']

# Fetch and flatten
with keep.running():
    pbp = fetch_game_pbp(list_of_games)

pbp = pd.json_normalize(pbp)

# Save the data
pbp.to_csv('~/dev/hockey_site/data/total-depth-index/all_pbp_20102025.csv', index=False)