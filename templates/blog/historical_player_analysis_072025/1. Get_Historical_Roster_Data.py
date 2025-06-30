#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Jun 29 15:00:18 2025

# CODE TO USE THE NHL API TO GET ALL HISTORICAL ROSTER DATA

@author: dylanwiwad
"""

# Import the libraries needed
import requests
import pandas as pd
import time
import os

# ----------------------------------------------------------------------
#
# PULL ALL THE TEAM ABBREVIATIONS FOR ALL TIME
#
# ----------------------------------------------------------------------

# Create a list of all active and defunct NHL teams
endpoint = "https://api.nhle.com/stats/rest/en/team"

# Make a get request to the API endpoint
response = requests.get(endpoint)

# Pull the data
data = response.json()

# Flatten 'data' key into a DataFrame
df_teams = pd.json_normalize(data['data'])

# Pull all the tricodes into a list

team_abbreviations = df_teams['triCode'].to_list()


# ----------------------------------------------------------------------
#
# PULL ALL THE TEAM ROSTERS FOR EVERY YEAR SINCE 1917
#
# ----------------------------------------------------------------------

# Test this out by pulling all rosters in 2025
all_rosters = []

# List of all seasons
seasons = [int(f"{year}{year+1}") for year in range(1917, 2025)]

for season in seasons:
    
    # Print a progress message
    print(f"Working on {season}")
    
    # For loop that goes over teams and pulls the rosters taht year,
    # renames variables, adds a season variable, flattens, and appends.
    for abbr in team_abbreviations:
        # Set the URL
        url = f'https://api-web.nhle.com/v1/roster/{abbr}/{season}'
        
        try:
            response = requests.get(url)
            time.sleep(0.5) # Just a slight slowdown to not be rude
            response.raise_for_status()
            data = response.json()
    
            for player in data.get('forwards', []) + data.get('defensemen', []) + data.get('goalies', []):
                player_flat = {
                    'team': abbr,
                    'id': player.get('id'),
                    'first_name': player.get('firstName', {}).get('default'),
                    'last_name': player.get('lastName', {}).get('default'),
                    'position': player.get('positionCode'),
                    'sweater': player.get('sweaterNumber'),
                    'shoots': player.get('shootsCatches'),
                    'birth_date': player.get('birthDate'),
                    'birth_city': player.get('birthCity', {}).get('default'),
                    'birth_province': player.get('birthStateProvince', {}).get('default') if 'birthStateProvince' in player else None,
                    'birth_country': player.get('birthCountry'),
                    'height_in': player.get('heightInInches'),
                    'weight_lb': player.get('weightInPounds'),
                    'headshot': player.get('headshot'),
                    'season': season
                }
                all_rosters.append(player_flat)
                
            # ✅ Success message
            print(f"  ✅ Loaded {abbr} roster for {season}")
        
        except:
            pass
        #except Exception as e:
        #    print(f"Failed to retrieve roster for {abbr}: {e}")

# Convert to DataFrame
rosters_df = pd.DataFrame(all_rosters)

# Preview
print(rosters_df.head())

# Save the data as a CSV for actual analysis
# Get the current working directory
script_dir = os.getcwd()

# Save the DataFrame as a CSV there
csv_path = os.path.join(script_dir, 'rosters.csv')
rosters_df.to_csv(csv_path, index=False)

# ----------------------------------------------------------------------
#
# A FEW QUICK EXPLORATORY LOGIC CHECKS
#
# ----------------------------------------------------------------------

# Number of people per team
rosters_df.groupby('team').size()

# Team count per season
team_season_counts = rosters_df.groupby(['team', "season"]).size()

# Total number of unique players
rosters_df['id'].nunique()

# Missing data on height, weight, country, season. Very complete data
rosters_df['height_in'].isnull().sum()
rosters_df['weight_lb'].isnull().sum()
rosters_df['birth_country'].isnull().sum()
rosters_df['season'].isnull().sum()

# Average height, weight
rosters_df['height_in'].mean()
rosters_df['weight_lb'].mean()

# Country counts
rosters_df.groupby('birth_country').size()















