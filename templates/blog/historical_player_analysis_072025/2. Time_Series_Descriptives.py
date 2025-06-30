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
import numpy as np
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

# Clean up data and convert height to cm
height_df = roster[['season', 'height_in']].dropna().copy()
height_df['height_cm'] = height_df['height_in'] * 2.54
height_df['season_label'] = height_df['season'].apply(split_and_hyphenate)

# Create jittered data
np.random.seed(42)
jittered_x = np.arange(len(height_df)) + np.random.uniform(-0.5, 0.5, size=len(height_df))
jittered_y = height_df['height_cm'] + np.random.uniform(-0.8, 0.8, size=len(height_df))

# Map seasons to numeric x values
season_labels = height_df['season_label'].unique()
season_to_index = {label: i for i, label in enumerate(season_labels)}
height_df['x_pos'] = height_df['season_label'].map(season_to_index)

# Compute average height by season
avg_height = (
    height_df.groupby('season_label')['height_cm']
    .mean()
    .reset_index()
)
avg_height['x_pos'] = avg_height['season_label'].map(season_to_index)

# PLOT
fig, ax = plt.subplots(figsize=(12, 7))

# Scatter: faded, jittered dots
ax.scatter(
    height_df['x_pos'] + np.random.uniform(-0.5, 0.5, size=len(height_df)),
    height_df['height_cm'] + np.random.uniform(-0.8, 0.8, size=len(height_df)),
    alpha=0.05,
    color='#041e42ff',
    edgecolor='none',
    s=12
)

# Line: average height per season
sns.lineplot(
    data=avg_height,
    x="x_pos",
    y="height_cm",
    ax=ax,
    color='#FF4C00',
    linewidth=3.5,
    zorder=10
)

# Style
sns.despine()
ax.grid(False)

# X-axis ticks and labels
tick_indices = list(range(0, len(season_labels), 15))
tick_labels = [season_labels[i] for i in tick_indices]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)

# Y-axis tick label styling
ax.tick_params(axis='y', labelsize=14)

# Axis labels
ax.set_xlabel("")
ax.set_ylabel("Height (cm)", fontsize=18)

# Layout and title position
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

# Title
fig.suptitle(
    "NHL player heights have risen over time, but plateaued",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)

# Subtitle
fig.text(
    left_x,
    0.87,
    "Over the past 107 years, NHL players have steadily gotten taller,\ngrowing from 176.2cm to 186.8cm (+5.99%).",
    fontsize=14,
    ha='left'
)

# No legend needed
ax.legend().remove()

# Save and show
save_figure("nhl_player_height_trend_raw.png")
plt.show()

# CLEAN HEIGHT

# Clean and prepare height data
height_df = roster[['season', 'height_in']].dropna().copy()
height_df['height_cm'] = height_df['height_in'] * 2.54
height_df['season_label'] = height_df['season'].apply(split_and_hyphenate)

# Map seasons to x-axis position
season_labels = height_df['season_label'].unique()
season_to_index = {label: i for i, label in enumerate(season_labels)}
height_df['x_pos'] = height_df['season_label'].map(season_to_index)

# Compute mean and std deviation per season
grouped = height_df.groupby('season_label')['height_cm']
mean = grouped.mean()
std = grouped.std()
x_vals = [season_to_index[s] for s in mean.index]

# PLOT
sns.set(style="whitegrid")
fig, ax = plt.subplots(figsize=(12, 7))

# Fill between (mean ± std)
ax.fill_between(
    x_vals,
    mean - std,
    mean + std,
    color='#041e42ff',
    alpha=0.15,
    label="± 1 std. dev."
)

# Plot mean line
ax.plot(
    x_vals,
    mean,
    color='#FF4C00',
    linewidth=3.5,
    label="Mean height"
)

# Clean up plot
sns.despine()
ax.grid(False)

# X-axis ticks and labels
tick_indices = list(range(0, len(season_labels), 15))
tick_labels = [season_labels[i] for i in tick_indices]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)

# Y-axis styling
ax.tick_params(axis='y', labelsize=14)
ax.set_ylabel("Height (cm)", fontsize=18)
ax.set_xlabel("")

# Titles
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

fig.suptitle(
    "NHL player heights have risen over time, but plateaued",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)

fig.text(
    left_x,
    0.87,
    "Over the past 107 years, NHL players have steadily gotten taller,\ngrowing from 176.2cm to 186.8cm (+5.99%).",
    fontsize=14,
    ha='left'
)

# Optional: remove legend if not needed
ax.legend().remove()

# Save and show
save_figure("nhl_player_height_trend_clean.png")
plt.show()



# ----------------------------------------------------------------------
#
# WEIGHT BY YEAR
#
# ----------------------------------------------------------------------

# Clean up data 
weight_df = roster[['season', 'weight_lb']].dropna().copy()
weight_df['season_label'] = weight_df['season'].apply(split_and_hyphenate)

# Create jittered data
np.random.seed(42)
jittered_x = np.arange(len(weight_df)) + np.random.uniform(-0.5, 0.5, size=len(weight_df))
jittered_y = weight_df['weight_lb'] + np.random.uniform(-0.8, 0.8, size=len(weight_df))

# Map seasons to numeric x values
season_labels = weight_df['season_label'].unique()
season_to_index = {label: i for i, label in enumerate(season_labels)}
weight_df['x_pos'] = weight_df['season_label'].map(season_to_index)

# Compute average weight by season
avg_weight = (
    weight_df.groupby('season_label')['weight_lb']
    .mean()
    .reset_index()
)
avg_weight['x_pos'] = avg_weight['season_label'].map(season_to_index)

# PLOT
fig, ax = plt.subplots(figsize=(12, 7))

# Scatter: faded, jittered dots
ax.scatter(
    weight_df['x_pos'] + np.random.uniform(-0.5, 0.5, size=len(weight_df)),
    weight_df['weight_lb'] + np.random.uniform(-0.8, 0.8, size=len(weight_df)),
    alpha=0.05,
    color='#041e42ff',
    edgecolor='none',
    s=12
)

# Line: average weight per season
sns.lineplot(
    data=avg_weight,
    x="x_pos",
    y="weight_lb",
    ax=ax,
    color='#FF4C00',
    linewidth=3.5,
    zorder=10
)

# Style
sns.despine()
ax.grid(False)

# X-axis ticks and labels
tick_indices = list(range(0, len(season_labels), 15))
tick_labels = [season_labels[i] for i in tick_indices]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)

# Y-axis tick label styling
ax.tick_params(axis='y', labelsize=14)

# Axis labels
ax.set_xlabel("")
ax.set_ylabel("Weight (lbs)", fontsize=18)

# Layout and title position
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

# Title
fig.suptitle(
    "NHL Player weights rose for a long time, but have begun to decline",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)

# Subtitle
fig.text(
    left_x,
    0.87,
    "Average weight rose from 171.4lbs to a peak of 205.4lbs (+19.8%) in the 2005-2006 season,\nand have since declined 2.2% to 200.7lbs.",
    fontsize=14,
    ha='left'
)

# No legend needed
ax.legend().remove()

# Save and show
save_figure("nhl_player_weight_trend.png")
plt.show()


# ----------------------------------------------------------------------
#
# AGE BY YEAR
#
# ----------------------------------------------------------------------

# Clean and calculate age
age_df = roster[['season', 'birth_date']].dropna().copy()
age_df['birth_date'] = pd.to_datetime(age_df['birth_date'])

# Assume players are measured at January 1st of each season year
age_df['reference_date'] = pd.to_datetime(age_df['season'].astype(str).str[:4] + '-01-01')
age_df['age'] = (age_df['reference_date'] - age_df['birth_date']).dt.days / 365.25

# Format season label and assign x-axis numeric positions
age_df['season_label'] = age_df['season'].apply(split_and_hyphenate)
season_labels = age_df['season_label'].unique()
season_to_index = {label: i for i, label in enumerate(season_labels)}
age_df['x_pos'] = age_df['season_label'].map(season_to_index)

# Compute average age per season
avg_age = (
    age_df.groupby('season_label')['age']
    .mean()
    .reset_index()
)
avg_age['x_pos'] = avg_age['season_label'].map(season_to_index)

# PLOT
sns.set(style="whitegrid")
fig, ax = plt.subplots(figsize=(12, 7))

# Jittered scatter points
np.random.seed(42)
x_jitter = age_df['x_pos'] + np.random.uniform(-0.5, 0.5, size=len(age_df))
y_jitter = age_df['age'] + np.random.uniform(-0.3, 0.3, size=len(age_df))

ax.scatter(
    x_jitter,
    y_jitter,
    alpha=0.05,
    color='#041e42ff',
    edgecolor='none',
    s=12
)

# Trend line (average age per season)
sns.lineplot(
    data=avg_age,
    x="x_pos",
    y="age",
    ax=ax,
    color='#FF4C00',
    linewidth=3.5,
    zorder=10
)

# Style
sns.despine()
ax.grid(False)

# X-axis ticks and labels
tick_indices = list(range(0, len(season_labels), 15))
tick_labels = [season_labels[i] for i in tick_indices]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)

# Y-axis styling
ax.tick_params(axis='y', labelsize=14)
ax.set_ylabel("Age (years)", fontsize=18)
ax.set_xlabel("")

# Titles
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

fig.suptitle(
    "NHL Player Age Has Remained Remarkably Stable",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)

fig.text(
    left_x,
    0.87,
    "Despite changes in training, nutrition, and playing style,\nthe average NHL player age has hovered near 26 for decades.",
    fontsize=14,
    ha='left'
)

# No legend
ax.legend().remove()

# Save and show
save_figure("nhl_player_age_trend.png")
plt.show()

