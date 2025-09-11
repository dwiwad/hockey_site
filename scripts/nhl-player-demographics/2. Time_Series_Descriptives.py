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
from statsmodels.nonparametric.smoothers_lowess import lowess
from matplotlib.ticker import FuncFormatter
import matplotlib as mpl

# Make sure you're not overwriting later
mpl.rcParams['font.family'] = 'Charter'
print("Using font:", mpl.rcParams['font.family'])  # should say ['Charter']


# Hardcoded project root
PROJECT_ROOT = "/Users/dwiwad/dev/hockey_site"

def save_figure(filename):
    output_dir = os.path.join(
        PROJECT_ROOT,
        "static/images/deep-dives/nhl-player-demographics"
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

roster = pd.read_csv("~/dev/hockey_site/data/nhl-player-demographics/rosters.csv")

# ----------------------------------------------------------------------
#
# ROSTER COUNTS
#
# ----------------------------------------------------------------------

print('Total number of NHL rostered players from 1917 to 2025:', len(roster))
print('Total roster years:', roster['season'].nunique())
print('Total unique rostered players from 1917 to 2025:', roster['id'].nunique())

# ----------------------------------------------------------------------
#
# NATIONALITY PROPORTIONS IN THE 2024-2025 AND OVERALL PLOT
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

# ----------------------------------------------------------------------
# AGGREGATION FOR PLOTTING
# ----------------------------------------------------------------------

# Get the max season
latest_season = country_year_df['season'].max()

# Get the latest group totals
latest_group_totals = (
    country_year_df.query("season == @latest_season")
    .groupby('country_group', as_index=False)['country_prop']
    .sum()
)

latest_order = (
    latest_group_totals
    .sort_values('country_prop', ascending=False)['country_group']
    .tolist()
)

top_groups = latest_group_totals.nlargest(5, 'country_prop')['country_group'].tolist()

# aggregate to group-by-season before plotting 
plot_df = (
    country_year_df[country_year_df['country_group'].isin(top_groups)]
    .groupby(['season', 'country_group'], as_index=False)['country_prop']
    .sum()
)

# Re-add the season label
plot_df['season_label'] = plot_df['season'].apply(split_and_hyphenate)

# Convert to categorical to enforce order
plot_df['country_group'] = pd.Categorical(plot_df['country_group'], categories=top_groups, ordered=True)


# ----------------------------------------------------------------------
# PLOT
# ----------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 7))
sns.lineplot(
    data=plot_df,
    x="season_label",
    y="country_prop",
    hue="country_group",
    palette={
        'Canada': '#D1495B',
        'USA': '#2E4057',
        'Scandinavia': '#008080',
        'Central Europe': '#E0A458',
        'Former USSR': '#6C757D'
    },
    linewidth=3.5,
    ax=ax,
    errorbar=None  
)

# Set a clean aesthetic style
mpl.rcParams['font.family'] = 'Charter'
sns.despine()
ax.grid(False)

# X-tick labels
# Get unique season labels every 15 steps
tick_labels = plot_df['season_label'].unique()[::15]

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
    "while Charternational representation grows modestly.",
    fontsize=14,
    ha='left'
)

fig.text(
    0.9,
    0.01,
    "Data: Raw yearly proportions", 
    fontsize=10, 
    style='italic', 
    ha='right'
)

# Legend
ax.legend(title="", frameon=False, loc='upper right', fontsize=14)
save_figure("nhl_player_nationalities_trend.png")

plt.show()

# ----------------------------------------------------------------------
#
# CLEAN AGE, HEIGHT, AND WEIGHT BY POSITION GROUP
#
# ----------------------------------------------------------------------

# Get roster size by year 
season_roster_size = roster.groupby('season')['id'].nunique()

# Map position to groups
position_map = {'C': 'Forward', 'R': 'Forward', 'L': 'Forward', 'D': 'Defense', 'G': 'Goalie'}
roster['position_group'] = roster['position'].map(position_map)

# Convert height to cm
roster['height_cm'] = roster['height_in'] * 2.54

# Format season label
def split_and_hyphenate(number):
    s_number = str(number)
    return f"{s_number[:4]}-{s_number[4:]}"


# Plotting function
def plot_clean_position_trend(df, value_col, ylabel, title, subtitle, filename, ylims, yticks, color_map):
    sns.set(style="whitegrid")
    mpl.rcParams['font.family'] = 'Charter'
    fig, ax = plt.subplots(figsize=(12, 7))

    for group in df['position_group'].unique():
        group_df = df[df['position_group'] == group]

        # Dots
        ax.scatter(
            group_df['x_pos'],
            group_df[value_col],
            color=color_map[group],
            alpha=0.2,
            s=50
        )

        # Smoothed LOESS line
        smoothed = lowess(
            endog=group_df[value_col],
            exog=group_df['x_pos'],
            frac=0.2,
            return_sorted=True
        )
        ax.plot(
            smoothed[:, 0],
            smoothed[:, 1],
            color=color_map[group],
            linewidth=3.5,
            label=group
        )

    ax.set_ylim(ylims)
    ax.set_yticks(yticks)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(round(x))}"))
    sns.despine()
    ax.grid(False)

    tick_indices = list(range(0, len(season_labels), 15))
    tick_labels = [season_labels[i] for i in tick_indices]
    ax.set_xticks(tick_indices)
    ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)
    ax.tick_params(axis='y', labelsize=14)
    ax.set_ylabel(ylabel, fontsize=18)
    ax.set_xlabel("")

    left_x = ax.get_position().x0
    plt.subplots_adjust(top=0.85)
    fig.suptitle(title, fontsize=20, weight='bold', x=left_x, ha='left', y=0.97)
    fig.text(left_x, 0.87, subtitle, fontsize=14, ha='left')
    clean_label = {"age": "age", "height_cm": "height", "weight_lb": "weight"}.get(value_col, value_col.split("_")[0])
    fig.text(0.9, 0.01, f"Data: Yearly average {clean_label} with LOESS-smoothed trend", 
             fontsize=10, style='italic', ha='right')
    legend_loc = 'upper left' if value_col == 'weight_lb' else 'upper right'
    ax.legend(title='', loc=legend_loc, frameon = False, fontsize = 14)
    save_figure(filename)
    plt.show()

# Loop for each variable
for varname, ylabel, title, subtitle, filename, ylims, yticks in [
    (
        'age',
        'Age (years)',
        'The average NHL player age by position',
        'Forwards, defense, and goalies all follow a similar age curve over time.',
        'nhl_age_by_position.png',
        (22, 30),
        range(22, 31)
    ),
    (
        'height_cm',
        'Height (cm)',
        'The average NHL player height by position',
        'Goalies are slightly taller on average, but the trend is upward for all roles.',
        'nhl_height_by_position.png',
        (170, 200),
        range(170, 201, 5)
    ),
    (
        'weight_lb',
        'Weight (lb)',
        'The average NHL player weight by position',
        'Weights peaked around 2010 and have trended down since.',
        'nhl_weight_by_position.png',
        (150, 220),                # <-- y-axis limits
        range(150, 221, 10)        # <-- y-axis ticks
    )
]:
    temp_df = roster.dropna(subset=['season', 'birth_date', 'position_group']).copy()
    temp_df['birth_date'] = pd.to_datetime(temp_df['birth_date'])
    temp_df['reference_date'] = pd.to_datetime(temp_df['season'].astype(str).str[:4] + '-01-01')

    if varname == 'age':
        temp_df['value'] = (temp_df['reference_date'] - temp_df['birth_date']).dt.days / 365.25
    else:
        temp_df['value'] = temp_df[varname]

    temp_df['season_label'] = temp_df['season'].apply(split_and_hyphenate)

    avg_df = (
        temp_df.groupby(['season_label', 'position_group'])['value']
        .mean()
        .reset_index()
        .rename(columns={'value': varname})
    )

    season_labels = avg_df['season_label'].unique()
    season_to_index = {label: i for i, label in enumerate(season_labels)}
    avg_df['x_pos'] = avg_df['season_label'].map(season_to_index)

    color_map = {
        'Forward': '#264653',
        'Defense': '#2a9d8f',
        'Goalie': '#e9c46a'
    }

    plot_clean_position_trend(
        df=avg_df,
        value_col=varname,
        ylabel=ylabel,
        title=title,
        subtitle=subtitle,
        filename=filename,
        ylims=ylims,
        yticks=yticks,
        color_map=color_map
    )




# ----------------------------------------------------------------------
#
# UNUSED CODE; FIGURES MADE WHILE EXPLORING DATA
#
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
#
# COUNTRY COUNTS BY YEAR
#
# ----------------------------------------------------------------------


# CLEAN
# Global season-to-index map using all years
all_season_labels = sorted(country_year_df['season_label'].unique())
season_to_index = {label: i for i, label in enumerate(all_season_labels)}
filtered_df['x_pos'] = filtered_df['season_label'].map(season_to_index)

# PLOT
sns.set(style="whitegrid")
mpl.rcParams['font.family'] = 'Charter'
fig, ax = plt.subplots(figsize=(12, 7))

# Plot each group
for group in top_groups:
    group_df = filtered_df[filtered_df['country_group'] == group].copy()

    # Dots
    ax.scatter(
        group_df['x_pos'],
        group_df['country_prop'],
        alpha=0.2,
        s=50,
        color=palette[group]
    )

    # LOESS line
    smoothed = lowess(
        endog=group_df['country_prop'],
        exog=group_df['x_pos'],
        frac=0.2,
        return_sorted=True
    )
    ax.plot(
        smoothed[:, 0],
        smoothed[:, 1],
        color=palette[group],
        linewidth=3.5,
        label=group
    )

# Y-axis formatting
ax.set_ylim(0, 1)
ax.set_ylabel("Share of NHL Players", fontsize=18)
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y * 100)}%"))
ax.tick_params(axis='y', labelsize=14)

# X-axis formatting
tick_indices = list(range(0, len(all_season_labels), 15))
tick_labels = [all_season_labels[i] for i in tick_indices]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)
ax.set_xlabel("")

# Aesthetic
sns.despine()
ax.grid(False)

# Titles
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)
fig.suptitle(
    "Canada still leads, but the U.S. is catching up in the NHL",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)
fig.text(
    left_x,
    0.87,
    "Over the past 50 years, American players have surged to near parity with Canadians,\n"
    "while Charternational representation grows modestly.",
    fontsize=14,
    ha='left'
)
fig.text(
    0.9,
    0.01,
    "Data: Share of total NHL players per season by country group (LOESS-smoothed)", 
    fontsize=10, 
    style='italic', 
    ha='right'
)

# Legend + save
ax.legend(title="", frameon=False, loc='upper right', fontsize=14)
save_figure("nhl_player_nationalities_trend_clean.png")
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
    color='#3B4B64',
    edgecolor='none',
    s=12
)

# Line: average height per season
sns.lineplot(
    data=avg_height,
    x="x_pos",
    y="height_cm",
    ax=ax,
    color='#D17A22',
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

# Compute mean height per season
avg_height = (
    height_df.groupby('season_label')['height_cm']
    .mean()
    .reset_index()
)
season_labels = avg_height['season_label'].unique()
season_to_index = {label: i for i, label in enumerate(season_labels)}
avg_height['x_pos'] = avg_height['season_label'].map(season_to_index)

# Apply LOESS smoothing
smoothed = lowess(
    endog=avg_height['height_cm'],
    exog=avg_height['x_pos'],
    frac=0.2,  # controls smoothness: 0.1 = tighter, 0.3 = smoother
    return_sorted=True
)

# PLOT
sns.set(style="whitegrid")
mpl.rcParams['font.family'] = 'Charter'
fig, ax = plt.subplots(figsize=(12, 7))

# Plot faded Oilers blue dots for each yearly average
ax.scatter(
    avg_height['x_pos'],
    avg_height['height_cm'],
    color='#041e42',
    alpha=0.2,
    s=50,
    label='Yearly average'
)

# Plot LOESS smoothed line (non-linear trend)
ax.plot(
    smoothed[:, 0],
    smoothed[:, 1],
    color='#D17A22',
    linewidth=3.5,
    label='LOESS smoothed trend'
)

ax.set_ylim(170, 190)
ax.set_yticks(range(170, 191, 5))
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x)}"))

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

fig.text(
    0.9,
    0.01,
    "Data: Yearly average height with LOESS-smoothed trend", 
    fontsize=10, 
    style='italic', 
    ha='right'
)

# Remove legend if not needed
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
    color='#3B4B64',
    edgecolor='none',
    s=12
)

# Line: average weight per season
sns.lineplot(
    data=avg_weight,
    x="x_pos",
    y="weight_lb",
    ax=ax,
    color='#D17A22',
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


# CLEAN WEIGHT

# Clean and prepare weight data
weight_df = roster[['season', 'weight_lb']].dropna().copy()
weight_df['season_label'] = weight_df['season'].apply(split_and_hyphenate)

# Compute mean weight per season
avg_weight = (
    weight_df.groupby('season_label')['weight_lb']
    .mean()
    .reset_index()
)
season_labels = avg_weight['season_label'].unique()
season_to_index = {label: i for i, label in enumerate(season_labels)}
avg_weight['x_pos'] = avg_weight['season_label'].map(season_to_index)

# Apply LOESS smoothing
smoothed = lowess(
    endog=avg_weight['weight_lb'],
    exog=avg_weight['x_pos'],
    frac=0.2,
    return_sorted=True
)

# PLOT
sns.set(style="whitegrid")
mpl.rcParams['font.family'] = 'Charter'
fig, ax = plt.subplots(figsize=(12, 7))

# Plot faded Oilers blue dots
ax.scatter(
    avg_weight['x_pos'],
    avg_weight['weight_lb'],
    color='#041e42',
    alpha=0.2,
    s=50
)

# Smoothed LOESS line
ax.plot(
    smoothed[:, 0],
    smoothed[:, 1],
    color='#D17A22',
    linewidth=3.5
)

# Axis limits and formatting
ax.set_ylim(160, 220)
ax.set_yticks(range(160, 221, 10))
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x)}"))

# Clean up
sns.despine()
ax.grid(False)

# X-axis ticks and labels
tick_indices = list(range(0, len(season_labels), 15))
tick_labels = [season_labels[i] for i in tick_indices]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)

# Y-axis styling
ax.tick_params(axis='y', labelsize=14)
ax.set_ylabel("Weight (lb)", fontsize=18)
ax.set_xlabel("")

# Titles
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

fig.suptitle(
    "NHL player weights have increased steadily",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)

fig.text(
    left_x,
    0.87,
    "Players now weigh ~12% more than they did a century ago.\nFrom ~175 lb to ~195 lb on average.",
    fontsize=14,
    ha='left'
)

fig.text(
    0.9,
    0.01,
    "Data: Yearly average weight with LOESS-smoothed trend", 
    fontsize=10, 
    style='italic', 
    ha='right'
)

ax.legend().remove()
save_figure("nhl_player_weight_trend_clean.png")
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
mpl.rcParams['font.family'] = 'Charter'
fig, ax = plt.subplots(figsize=(12, 7))

# Jittered scatter points
np.random.seed(42)
x_jitter = age_df['x_pos'] + np.random.uniform(-0.5, 0.5, size=len(age_df))
y_jitter = age_df['age'] + np.random.uniform(-0.3, 0.3, size=len(age_df))

ax.scatter(
    x_jitter,
    y_jitter,
    alpha=0.05,
    color='#3B4B64',
    edgecolor='none',
    s=12
)

# Trend line (average age per season)
sns.lineplot(
    data=avg_age,
    x="x_pos",
    y="age",
    ax=ax,
    color='#D17A22',
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

# CLEAN AGE

# Clean and calculate age
age_df = roster[['season', 'birth_date']].dropna().copy()
age_df['birth_date'] = pd.to_datetime(age_df['birth_date'])
age_df['reference_date'] = pd.to_datetime(age_df['season'].astype(str).str[:4] + '-01-01')
age_df['age'] = (age_df['reference_date'] - age_df['birth_date']).dt.days / 365.25
age_df['season_label'] = age_df['season'].apply(split_and_hyphenate)

# Compute mean age per season
avg_age = (
    age_df.groupby('season_label')['age']
    .mean()
    .reset_index()
)
season_labels = avg_age['season_label'].unique()
season_to_index = {label: i for i, label in enumerate(season_labels)}
avg_age['x_pos'] = avg_age['season_label'].map(season_to_index)

# Apply LOESS smoothing
smoothed = lowess(
    endog=avg_age['age'],
    exog=avg_age['x_pos'],
    frac=0.2,
    return_sorted=True
)

# PLOT
sns.set(style="whitegrid")
mpl.rcParams['font.family'] = 'Charter'
fig, ax = plt.subplots(figsize=(12, 7))

# Plot faded Oilers blue dots
ax.scatter(
    avg_age['x_pos'],
    avg_age['age'],
    color='#041e42',
    alpha=0.2,
    s=50
)

# Smoothed LOESS line
ax.plot(
    smoothed[:, 0],
    smoothed[:, 1],
    color='#D17A22',
    linewidth=3.5
)

# Axis limits and formatting
ax.set_ylim(22, 30)
ax.set_yticks(range(22, 31))
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x)}"))

# Clean up
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
    "The average NHL player age has remained steady",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)

fig.text(
    left_x,
    0.87,
    "Despite changes in size and pace, the average player age has\nstayed between 24 and 28 years since the 1920s.",
    fontsize=14,
    ha='left'
)

fig.text(
    0.9,
    0.01,
    "Data: Yearly average age with LOESS-smoothed trend", 
    fontsize=10, 
    style='italic', 
    ha='right'
)

ax.legend().remove()
save_figure("nhl_player_age_trend_clean.png")
plt.show()

# SCRATCHPAD FOR ROSTER TURNOVER
id_df = roster[['season', 'id']].dropna().copy()
id_df['season_label'] = id_df['season'].apply(split_and_hyphenate)

# Put in the eras
def first_year(number):
    s_number = str(number)
    part1 = s_number[:4]
    return part1

id_df['first_year'] = id_df['season'].apply(first_year)

# make sure first_year is int
id_df['first_year'] = id_df['first_year'].astype(int)

# build a set of (id, first_year) pairs that actually exist
pairs = set(zip(id_df['id'], id_df['first_year']))

# flag if (id, first_year-1) is in the set
id_df['in_prev_season'] = [
    int((i, y-1) in pairs) for i, y in zip(id_df['id'], id_df['first_year'])
]

id_df['in_prev_season'].mean()

# Build eras
id_df = id_df.assign(
    era = np.where(id_df['first_year'] < 1942, 'Early Era (≤1941)',
           np.where(id_df['first_year'] < 1967, 'Original Six (1942–1966)',
           np.where(id_df['first_year'] < 1991, 'Expansion Boom (1967–1990)',
           np.where(id_df['first_year'] < 2017, 'Expansion II (1991–2016)',
                    'Modern Era (2017–present)'))))
)


id_df.groupby('era')['in_prev_season'].count()
id_df.groupby('era')['in_prev_season'].mean()









# 0) Clean, de-dup per player-season
id_df = (
    roster[['season', 'id']]
    .dropna()
    .drop_duplicates()           # ensure one row per id-season
    .copy()
)

def season_start(season):
    s = str(season)
    return int(s[:4])

def season_label(season):
    s = str(season)
    return f"{s[:4]}-{s[4:]}"

id_df['season_start'] = id_df['season'].apply(season_start)
id_df['season_label'] = id_df['season'].apply(season_label)

# 1) Build an ordered list of actual seasons in your data
seasons_sorted = sorted(id_df['season_start'].unique())

# Map each season to the *previous real season* (skip gaps like 2004-05)
prev_map = {s: p for s, p in zip(seasons_sorted[1:], seasons_sorted[:-1])}

# 2) Build a set of (id, season_start) pairs and flag returning players
pairs = set(zip(id_df['id'], id_df['season_start']))

id_df['in_prev_season'] = id_df.apply(
    lambda r: int((r['id'], prev_map.get(r['season_start'], None)) in pairs)
              if prev_map.get(r['season_start'], None) is not None else 0,
    axis=1
)

# 3) Compute per-season turnover = share of newcomers
season_turnover = (
    id_df
      .groupby('season_start', as_index=False)
      .agg(
          players_this_season=('id', 'nunique'),
          returning=('in_prev_season', 'sum')
      )
)
season_turnover['newcomers'] = season_turnover['players_this_season'] - season_turnover['returning']
season_turnover['turnover_rate'] = season_turnover['newcomers'] / season_turnover['players_this_season']

# 4) Add your era buckets (rename Modern end as you like)
def era_of(y):
    if y < 1942: return 'Early Era (≤1941)'
    if y < 1967: return 'Original Six (1942–1966)'
    if y < 1991: return 'Expansion Boom (1967–1990)'
    if y < 2017: return 'Expansion II (1991–2016)'
    return 'Modern Era (2017–present)'

season_turnover['era'] = season_turnover['season_start'].apply(era_of)

# 5) Optional: compare to “expansion pressure”
#    Use total player count (or #teams if you have it) and look at year-over-year change
season_turnover = season_turnover.sort_values('season_start')
season_turnover['delta_players'] = season_turnover['players_this_season'].diff()

# Example summaries:
era_summary = (season_turnover
               .groupby('era', as_index=False)['turnover_rate']
               .mean()
               .rename(columns={'turnover_rate': 'avg_turnover_rate'}))

# Quick check: overall newcomer share (what your mean() was aiming at)
overall_turnover = 1 - id_df['in_prev_season'].mean()


# --- PREPARE TURNOVER DATAFRAME (season_turnover) ---
# season_turnover should already have: season_start, turnover_rate

# Build season labels (e.g., 1917-18, 1918-19, ...)
season_turnover['season_label'] = season_turnover['season_start'].astype(str) + '-' + (season_turnover['season_start']+1).astype(str).str[-2:]

# Map seasons to numeric x positions
season_labels = season_turnover['season_label'].unique()
season_to_index = {label: i for i, label in enumerate(season_labels)}
season_turnover['x_pos'] = season_turnover['season_label'].map(season_to_index)

# --- PLOT ---
fig, ax = plt.subplots(figsize=(12, 7))

# Scatter: faded dots for season-level turnover
ax.scatter(
    season_turnover['x_pos'],
    season_turnover['turnover_rate'],
    alpha=0.15,
    color='#3B4B64',
    edgecolor='none',
    s=25
)

# Line: average turnover per season
sns.lineplot(
    data=season_turnover,
    x="x_pos",
    y="turnover_rate",
    color='#D17A22',
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
ax.set_ylabel("Turnover Rate", fontsize=18)

# Layout and title position
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

# Title
fig.suptitle(
    "NHL roster turnover spikes during expansion periods",
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
    "When the league expands, the proportion of newcomers entering each season increases sharply,\n"
    "reflecting roster turnover driven by new teams and greater player demand.",
    fontsize=14,
    ha='left'
)

plt.show()






























