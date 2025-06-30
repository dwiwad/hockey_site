#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 30 11:57:35 2025

# CODE TO START BUILDING SOME TIME SERIES DESCRIPTIVES

@author: dylanwiwad
"""
# ----------------------------------------------------------------------
#
# LIBRARIES
#
# ----------------------------------------------------------------------

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import os

# Hardcoded project root (adjust if you move the repo)
PROJECT_ROOT = "/Users/dylanwiwad/hockey_site"

def save_figure(filename):
    output_dir = os.path.join(
        PROJECT_ROOT,
        "static/images/blog/historical_player_analysis_072025"
    )
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    # Full path to save the image
    output_path = os.path.join(output_dir, filename)
    # Save the figure
    plt.savefig(output_path, dpi=300, transparent=True)
    print(f"✅ Saved: {output_path}")

# ----------------------------------------------------------------------
#
# READ IN THE DATA
#
# ----------------------------------------------------------------------

roster = pd.read_csv("~/hockey_site/templates/blog/historical_player_analysis_072025/rosters.csv")

# ----------------------------------------------------------------------
#
# COUNTRY COUNTS BY YEAR
#
# ----------------------------------------------------------------------

# Get the simple counts of country by season
country_year_df = roster.groupby(['season', 'birth_country']).size().reset_index(name='count')

# Add in total players per season
country_year_df['total_players'] = country_year_df.groupby('season')['count'].transform('sum')

# Add in proportions
country_year_df['country_prop'] = (country_year_df['count'] / country_year_df['total_players'])

# Split season into a nice labelled variable
def split_and_hyphenate(number):
    s_number = str(number)
    # Example: Split into first 3 and remaining digits
    part1 = s_number[:4]
    part2 = s_number[4:]
    return f"{part1}-{part2}"

# Apply the function to create a new column
country_year_df['season_label'] = country_year_df['season'].apply(split_and_hyphenate)

# Clean up the countries into groupings
def map_country_group(country):
    if country == 'CAN':
        return 'Canada'
    elif country == 'USA':
        return 'USA'
    elif country in ['SWE', 'FIN', 'NOR', 'DNK']:
        return 'Scandinavia'
    elif country in ['CZE', 'SVK']:
        return 'Central Europe'
    elif country in ['RUS', 'BLR', 'UKR', 'KAZ']:
        return 'Former USSR'
    elif country in ['DEU', 'AUT', 'SUI']:  # Germany, Austria, Switzerland
        return 'Western Europe'
    elif country in ['FRA', 'GBR', 'IRL', 'NLD', 'BEL']:
        return 'Other Europe'
    else:
        return 'Other'

# Apply dataframe dataframe
country_year_df['country_group'] = country_year_df['birth_country'].apply(map_country_group)

palette = {
    'Canada': '#FF0000',
    'USA': '#0A3161',
    'Scandinavia': 'goldenrod',
    'Central Europe': 'darkgreen',
    'Former USSR': 'purple',
    'Western Europe': 'orange',
    'Other Europe': 'gray',
    'Other': 'lightgray'
}

# Get the max season
latest_season = country_year_df['season'].max()

# Compute total proportion for each group in the latest season
latest_order = (
    country_year_df[country_year_df['season'] == latest_season]
    .groupby('country_group')['country_prop']
    .sum()
    .sort_values(ascending=False)
    .index
    .tolist()
)

# Convert to categorical to enforce order
country_year_df['country_group'] = pd.Categorical(
    country_year_df['country_group'],
    categories=latest_order,
    ordered=True
)

# TRY TO MAKE A FIVETHIRTYEIGHT OR OTHERWISE NARRATIVE STYLED PLOT
# Set a clean aesthetic style
sns.set(style="whitegrid")

# Restrict to only top 5 country groups in 2024–2025
latest_season = country_year_df['season'].max()
top_groups = (
    country_year_df[country_year_df['season'] == latest_season]
    .groupby('country_group')['country_prop']
    .sum()
    .sort_values(ascending=False)
    .head(5)
    .index
    .tolist()
)

# Filter data to only include these groups
filtered_df = country_year_df[country_year_df['country_group'].isin(top_groups)].copy()

# Set order explicitly
filtered_df['country_group'] = pd.Categorical(
    filtered_df['country_group'],
    categories=top_groups,
    ordered=True
)

# Define a clean, journalistic color palette
palette = {
    'Canada': '#FF0000',       # red
    'USA': '#0A3161',          # blue
    'Scandinavia': '#2a9d8f',  # teal
    'Former USSR': '#8d99ae',  # grayish blue
    'Central Europe': '#f4a261' # warm orange
}

# PLOT
fig, ax = plt.subplots(figsize=(12, 7))

# Plot
sns.lineplot(
    data=filtered_df,
    x="season_label",
    y="country_prop",
    hue="country_group",
    palette=palette,
    linewidth=3.5,
    ax=ax,
    ci=None
)

# Style
sns.despine()
ax.grid(False)

# X-tick labels
# Get unique season labels every 15 steps
tick_labels = filtered_df['season_label'].unique()[::15]

# Set ticks and labels using actual string values
ax.set_xticks(tick_labels)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)
ax.tick_params(axis='y', labelsize=14)

# Axis labels
ax.set_xlabel("")
ax.set_ylabel("Share of NHL Players", fontsize=18)

# Calculate left margin in figure coords
left_x = ax.get_position().x0

# Reserve more space at the top for the titles
plt.subplots_adjust(top=0.85)  # moves the plot down, freeing top 15% of figure height

# Title (main)
fig.suptitle(
    "Canada still leads, but the U.S. is catching up in the NHL",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=.97  # Top of reserved space
)

# Subtitle
fig.text(
    left_x,
    0.87,  # Slightly below the main title
    "Over the past 50 years, American players have surged to near parity with Canadians,\n"
    "while international representation grows modestly.",
    fontsize=14,
    ha='left'
)

# Legend
ax.legend(title="", frameon=False, loc='upper right', fontsize=14)
save_figure("nhl_player_nationalities_trend.png")
plt.show()

# ----------------------------------------------------------------------
#
# WITHIN CANADA, PROVINCE HEATMAPS
#
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
#
# HEAT MAP OF BIRTH CITIES GLOBALLY
#
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
#
# HEIGHT BY YEAR
#
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
#
# WEIGHT BY YEAR
#
# ----------------------------------------------------------------------

# ----------------------------------------------------------------------
#
# AGE BY YEAR
#
# ----------------------------------------------------------------------

