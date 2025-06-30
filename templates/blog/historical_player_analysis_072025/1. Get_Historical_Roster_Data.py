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

# ----------------------------------------------------------------------
#
# TESTING IT OUT, PULL EDMONTON'S MOST RECENT ROSTER
#
# ----------------------------------------------------------------------

# Set the API endpoint
endpoint = 'https://api-web.nhle.com/v1/roster/EDM/20232024'

# Make a get request to the API endpoint
response = requests.get(endpoint)

# Pull the data
data = response.json()

# Combine all players from forwards, defensemen, goalies nested json structure
players = data['forwards'] + data['defensemen'] + data['goalies']

# Flatten to a df
df_players = pd.json_normalize(players)

# Preview
print(df_players.head())

# ----------------------------------------------------------------------
#
# PULL ALL THE TEAM ROSTERS FOR THIS YEAR
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


# Test this out by pulling all rosters in 2025
all_rosters = []

for abbr in team_abbreviations:
    url = f'https://api-web.nhle.com/v1/roster/{abbr}/20242025'
    try:
        response = requests.get(url)
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
                'headshot': player.get('headshot')
            }
            all_rosters.append(player_flat)

    except Exception as e:
        print(f"Failed to retrieve roster for {abbr}: {e}")

# Convert to DataFrame
rosters_df = pd.DataFrame(all_rosters)

# Preview
print(rosters_df.head())

# Number of people per team
rosters_df.groupby('team').size()


# ----------------------------------------------------------------------
#
# PULL ALL THE TEAM ROSTERS FOR EVERY YEAR SINCE 1917
#
# ----------------------------------------------------------------------

















