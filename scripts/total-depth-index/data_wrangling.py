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

# I think first we maybe need all play by play data for the 2024-2025 season
# So maybe let's start with just getting every game_id
# Preseason: September 21, 2024 to October 3, 2024
# Regular season: October 4, 2024 to April 17, 2025
# Playoffs: April 18, 2024 to June 24, 2025

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
   
# Fetch and flatten
games = get_all_games(mondays)
games = pd.json_normalize(games)

# Save the file for later
games.to_csv('~/dev/hockey_site/data/total-depth-index/all_games_meta_20242025.csv', index=False)

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
play_test = fetch_game_pbp(list_of_games)
pbp = pd.json_normalize(play_test)

# Save the data
pbp.to_csv('~/dev/hockey_site/data/total-depth-index/all_pbp_20242025.csv', index=False)


##############################################################################
# GET THE ROSTER INFORMATION
############################################################################## 

# For the season make a df that is game_id, away_abbrev, home_abbrev
teams = games[['id', 'awayTeam.abbrev', 'homeTeam.abbrev']].rename(columns = {'id': 'game_id'})

# Merge in the abbrevs
pbp = pd.merge(pbp, teams, on = 'game_id', how = 'inner')

# I need player lookups too... I'm aware this isn't the most efficient way to
# do this. Maybe before posting I'll create a single fetch pbp and roster func.
def fetch_game_roster(list_of_games):
    
    # Initialize a list
    rosters = []
    n = 1
    
    for game in list_of_games:
        print(f"working on game { n } of { len(list_of_games) }")
        # Build the actual url and make the call
        url = f"https://api-web.nhle.com/v1/gamecenter/{ game }/play-by-play"
        response = requests.get(url)
        data = response.json()
        
        # Build a teamId → abbrev lookup
        team_lookup = {}
        for side in ("awayTeam", "homeTeam"):
            t = data.get(side, {})
            if t:
                team_lookup[t.get("id")] = t.get("abbrev")
        
        for d in data['rosterSpots']:
            d['game_id'] = game
            d['teamAbbrev'] = team_lookup.get(d.get("teamId"))
        
        rosters.extend(data['rosterSpots'])
        
        n += 1
        
        # Add a quick pause to be polite
        time.sleep(2)
    
    return rosters

with keep.presenting():
    # Get the list of games:
    list_of_games = games['id']

    # Fetch and flatten
    rosters = fetch_game_roster(list_of_games)

rosters = pd.json_normalize(rosters)

rosters = rosters[['game_id', 'teamId', 'teamAbbrev', 'playerId', 
                   'positionCode', 'firstName.default', 'lastName.default']]

# Save the data
rosters.to_csv('~/dev/hockey_site/data/total-depth-index/all_rosters_20242025.csv', index=False)    

##############################################################################
# GET SHIFT DATA FOR TOI CALCULATIONS
############################################################################## 

# The shift data is here:
# https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId=2024010001
# So I'm gonna need another big pull. Maybe stop here and clean the file is getting messy

# game_id, playerId, duration
# Function to get the shift data for every game
def fetch_toi(list_of_games):
    
    # Initialize a list
    shifts = []
    n = 1
    
    for game in list_of_games:
        print(f"working on game { n } of { len(list_of_games) }")
        # Build the actual url and make the call
        url = f"https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={ game }"
        response = requests.get(url)
        data = response.json()
        
        shifts.extend(data['data'])
        
        n += 1
        
        # Add a quick pause to be polite
        time.sleep(2)
    
    return shifts

# Get the list of games:
list_of_games = games['id']

with keep.presenting():
    # Fetch shifts
    shifts = fetch_toi(list_of_games)

# Flatten
shifts = pd.json_normalize(shifts)

# Save the data
shifts.to_csv('~/dev/hockey_site/data/total-depth-index/all_shifts_20242025.csv', index=False)    
    
##############################################################################
#
# DEFINING, CALCULATING, AND MERGING ALL THE RELEVANT DATA
#
##############################################################################      
    
##############################################################################
# SHOTS-ON-GOAL AND GOAL WITH PLAYER AND TEAM ID
##############################################################################  

# Had to clear the environment. Reload data.
games = pd.read_csv('~/dev/hockey_site/data/total-depth-index/all_games_meta_20242025.csv')
pbp = pd.read_csv('~/dev/hockey_site/data/total-depth-index/all_pbp_20242025.csv')
shifts = pd.read_csv('~/dev/hockey_site/data/total-depth-index/all_shifts_20242025.csv')
rosters = pd.read_csv('~/dev/hockey_site/data/total-depth-index/all_rosters_20242025.csv')

    
# Let's start with team by team. Perhaps just with Edmonton.
# For every game, create a df that is:
# game_id, player_name, shots_on_goal, goals, shot_attempts
# I am just gonna wanna merge counts into the roster data I think, preserving 0s

# What I need to do now is loop through shots and count by player_id and add to rosters.
pbp['typeDescKey'].value_counts()

# For shots, remove shootouts and shrink to shots-on-goal
shots = pbp[pbp['periodDescriptor.periodType'] != 'SO']
shots = shots[shots['typeDescKey'].isin(['shot-on-goal', 'goal'])]    
# Quick check
shots['typeDescKey'].value_counts()    

# Create a playerId col that uses scoring or shooting playerId
shots['playerId'] = np.where(
    shots['typeDescKey'].eq('goal'),
    shots['details.scoringPlayerId'],
    shots['details.shootingPlayerId']
)

# Count shots-on-goal per player per game
game_sogs = (
    shots
    .groupby('game_id')['playerId']
    .value_counts()
    .reset_index(name='sog_count')
)


# Merge into the roster
rosters = pd.merge(rosters, game_sogs, on = ['game_id', 'playerId'], how = 'left').fillna(0)

##############################################################################
# ASSISTS BY PLAYER_ID
##############################################################################

# We can apply the same player counting logic for assists. I'm realizing we don't
# even need to filter the data we can just count
# What I need to do now is loop through shots and count by player_id and add to rosters.
pbp['typeDescKey'].value_counts()

# For shots, remove shootouts and shrink to goals; the only thing w/ assists
goals = pbp[pbp['periodDescriptor.periodType'] != 'SO']
goals = goals[goals['typeDescKey'].isin(['goal'])]    

# Stack both assist columns into one
assists = goals.melt(
    id_vars=['game_id'], 
    value_vars=['details.assist1PlayerId', 'details.assist2PlayerId'],
    value_name='playerId'
)

# Count assists per player per game
game_assists = (
    assists
    .groupby(['game_id', 'playerId'])
    .size()
    .reset_index(name='assist_count')
)

# Merge into the roster
rosters = pd.merge(rosters, game_assists, on = ['game_id', 'playerId'], how = 'left').fillna(0)

##############################################################################
# CORSI FOR - SHOT ATTEMPTS AT EVEN STRENGTH
##############################################################################

pbp['typeDescKey'].value_counts()

# For shots, remove shootouts and shrink to goals; the only thing w/ assists
corsi = pbp[pbp['periodDescriptor.periodType'] != 'SO']
corsi = corsi[corsi['typeDescKey'].isin(['shot-on-goal', 'blocked-shot', 'missed-shot', 'goal'])]  

# It seeeems like situationCode describes players on ice so 1551 is even strength
# https://gitlab.com/dword4/nhlapi/-/issues/112
corsi = corsi[corsi['situationCode'] == 1551]

# Quick check
corsi['typeDescKey'].value_counts()    

# Create a playerId col that uses scoring or shooting playerId
corsi['playerId'] = np.where(
    corsi['typeDescKey'].eq('goal'),
    corsi['details.scoringPlayerId'],
    corsi['details.shootingPlayerId']
)

# Count shots-on-goal per player per game
game_cf = (
    corsi
    .groupby('game_id')['playerId']
    .value_counts()
    .reset_index(name='corsi_for')
)


# Merge into the roster
rosters = pd.merge(rosters, game_cf, on = ['game_id', 'playerId'], how = 'left').fillna(0)

##############################################################################
# TIME ON ICE
##############################################################################

# Need to select rows where detailCode == 0 because this has goals, etc.
# When detailCode is 0, that is just a shift.
# Then convert shift times to seconds and add up by player and game
toi = shifts[shifts['detailCode'] == 0]

# Convert shift time to seconds
# Convert the 'time_str' column to timedelta objects
toi['shift_time'] = pd.to_timedelta("00:" + toi['duration'])

# Extract the total seconds from the timedelta objects
toi['duration_sec'] = toi['shift_time'].dt.total_seconds().astype(int)

toi = toi.rename(columns = {'gameId': 'game_id'})

# Sum shift time per player per game
toi_sums = (
    toi.groupby(['game_id', 'playerId'], as_index=False)['duration_sec']
       .sum()
       .rename(columns={'duration_sec': 'total_ice_time'})
)


# Merge into the roster
rosters = pd.merge(rosters, toi_sums, on = ['game_id', 'playerId'], how = 'left').fillna(0)


##############################################################################
# BUILD GAME LEVEL METRICS AND SAVE
##############################################################################

# Shrink the data to not include goalies
shooters = rosters[rosters['positionCode'] != 'G']

# Bring in Olivia Guest's gini func, modified slightly
# https://github.com/oliviaguest/gini

def gini(x, eps=1e-9):
    """Gini coefficient for a 1D array-like of nonnegative values."""
    a = np.asarray(x, dtype=np.float64).ravel()
    if a.size == 0:
        return np.nan
    # Shift up if any negatives (shouldn't happen for SOG, but safe)
    amin = a.min()
    if amin < 0:
        a = a - amin
    s = a.sum()
    if s <= 0:
        return 0.0  # all zeros -> perfectly equal
    a = np.sort(a)
    n = a.size
    idx = np.arange(1, n + 1, dtype=np.float64)
    return ((2 * idx - n - 1) @ a) / (n * s + eps)


# Shot depth; This will be the root final data we build on
game_data = (
    shooters.groupby(['game_id', 'teamAbbrev'])['sog_count']
      .apply(gini)
      .rename('sog_gini')
      .reset_index()
)

# Get the total sogs by team game
sogs_by_team_game = (
    shooters.groupby(['game_id', 'teamAbbrev'])['sog_count']
      .sum()
      .rename('total_sogs')
      .reset_index()
)

game_data = (
    pd.merge(game_data,
             sogs_by_team_game[['game_id', 'teamAbbrev', 'total_sogs']], 
             on=['game_id', 'teamAbbrev'], 
             how='left')
)

# Bring in the game outcome
games['winAbbrev'] = np.where(games['awayTeam.score'] > games['homeTeam.score'], games['awayTeam.abbrev'], games['homeTeam.abbrev'])

# Merge it in
games = games.rename(columns = {'id': 'game_id'})

game_data = game_data.merge(
    games[["game_id", "winAbbrev"]],
    on="game_id",
    how="left"
)

game_data['outcome'] = np.where(game_data['teamAbbrev'] == game_data['winAbbrev'], 1, 0)

# Get the assist gini
assist_gini = (
    shooters.groupby(['game_id', 'teamAbbrev'])['assist_count']
      .apply(gini)
      .rename('assist_gini')
      .reset_index()
)

game_data = (
    pd.merge(game_data,
             assist_gini[['game_id', 'teamAbbrev', 'assist_gini']], 
             on=['game_id', 'teamAbbrev'], 
             how='left')
)

# CF = shots-on-goal + goal + blocks + misses
# Get the total by team game
cf_by_team_game = (
    shooters.groupby(['game_id', 'teamAbbrev'])['corsi_for']
      .sum()
      .reset_index()
)

game_data = (
    pd.merge(game_data,
             cf_by_team_game[['game_id', 'teamAbbrev', 'corsi_for']], 
             on=['game_id', 'teamAbbrev'], 
             how='left')
)

# Get the TOI gini
toi_gini = (
    shooters.groupby(['game_id', 'teamAbbrev'])['total_ice_time']
      .apply(gini)
      .rename('toi_gini')
      .reset_index()
)

game_data = (
    pd.merge(game_data,
             toi_gini[['game_id', 'teamAbbrev', 'toi_gini']], 
             on=['game_id', 'teamAbbrev'], 
             how='left')
)

# This is just myself wanting it in the right order lol
new_order = ['game_id', 'teamAbbrev', 'outcome', 'total_sogs', 'sog_gini', 
             'assist_gini', 'toi_gini', 'corsi_for']

# Reassign the DataFrame with the new column order
game_data = game_data[new_order]

# Save the data
game_data.to_csv('~/dev/hockey_site/data/total-depth-index/final_data_20242025.csv', index=False)    

##############################################################################
# INTERIM VALIDATION OUT OF CURIOSITY
# AVG GINI BY TEAM
# DOES GINI PREDICT WINS?
# IS GINI ORTHOGONAL TO SHOT COUNT?
##############################################################################

# CF = shots-on-goal + goal + blocks + misses
# Get the total by team game
cf_by_team_game = (
    rosters.groupby(['game_id', 'teamAbbrev'])['corsi_for']
      .sum()
      .reset_index()
)

# I just want to do a quick test. Bring in Olivia Guest's gini func, modified slightly
# https://github.com/oliviaguest/gini

def gini(x, eps=1e-9):
    """Gini coefficient for a 1D array-like of nonnegative values."""
    a = np.asarray(x, dtype=np.float64).ravel()
    if a.size == 0:
        return np.nan
    # Shift up if any negatives (shouldn't happen for SOG, but safe)
    amin = a.min()
    if amin < 0:
        a = a - amin
    s = a.sum()
    if s <= 0:
        return 0.0  # all zeros -> perfectly equal
    a = np.sort(a)
    n = a.size
    idx = np.arange(1, n + 1, dtype=np.float64)
    return ((2 * idx - n - 1) @ a) / (n * s + eps)

# remove goalies
shooter_roster = rosters[rosters['positionCode'] != 'G']

gini_by_team_game = (
    shooter_roster.groupby(['game_id', 'teamAbbrev'])['sog_count']
      .apply(gini)
      .rename('gini')
      .reset_index()
)

# Average gini by team
gini_by_team = (
    gini_by_team_game.groupby('teamAbbrev')['gini']
    .mean()
    .reset_index()
)

# Correlation with SOGs
# Get the total by team game
sogs_by_team_game = (
    shooter_roster.groupby(['game_id', 'teamAbbrev'])['sog_count']
      .sum()
      .rename('total_sogs')
      .reset_index()
)

gini_by_team_game = (
    pd.merge(gini_by_team_game,
             sogs_by_team_game[['game_id', 'teamAbbrev', 'total_sogs']], 
             on=['game_id', 'teamAbbrev'], 
             how='left')
)

# Correlate
gini_by_team_game['gini'].corr(gini_by_team_game['total_sogs'])

# They seem to be pretty highly correlated such that teams with more shooting
# depth are straight up just taking more shots. 
# I think it will be important when predicting wins with gini here, does it go
# just beyond shot counts. But also, if it doesn't that's okay because this is
# only going to be on element of depth.

# To calc win, 
# create col win.Abbrev
# if awayTeam.score > homeTeam.score then win.Abbrev =  awayTeam.abbrev else homeTeam.abbrev
games['winAbbrev'] = np.where(games['awayTeam.score'] > games['homeTeam.score'], games['awayTeam.abbrev'], games['homeTeam.abbrev'])

# Merge it in
games = games.rename(columns = {'id': 'game_id'})

gini_by_team_game = gini_by_team_game.merge(
    games[["game_id", "winAbbrev"]],
    on="game_id",
    how="left"
)

gini_by_team_game['outcome'] = np.where(gini_by_team_game['teamAbbrev'] == gini_by_team_game['winAbbrev'], 1, 0)

# Given this is quick and dirty let's just look at corr and then regress to control for sogs
gini_by_team_game['gini'].corr(gini_by_team_game['outcome'])
gini_by_team_game['total_sogs'].corr(gini_by_team_game['outcome'])

# The corr is low, but the sogs corr is low too. Teams who take more shots
# win more (r = .0992), teams with more shot depth win more (r = -.063)

# Quick standardized logit regression

# z-score predictors
# Reverse gini to be more intuitive
gini_by_team_game["depth_z"] = -zscore(gini_by_team_game["gini"])
gini_by_team_game["sogs_z"] = zscore(gini_by_team_game["total_sogs"])

model = smf.logit(formula='outcome ~ depth_z * sogs_z', data=gini_by_team_game)
results = model.fit()
results.summary()


##############################################################################
# STRUCTURAL EQUATION MODEL
##############################################################################


    
    
    

    
    