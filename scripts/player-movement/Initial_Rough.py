#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  2 13:10:59 2025

@author: dylanwiwad
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib as mpl
from matplotlib.ticker import FuncFormatter
from statsmodels.nonparametric.smoothers_lowess import lowess

# ----------------------------------------------------------------------
# STYLE SETUP
# ----------------------------------------------------------------------

mpl.rcParams['font.family'] = 'Charter'
sns.set(style="whitegrid")

color_map = {
    'Forward': '#264653',
    'Defense': '#2A9D8F',
    'Goalie': '#E76F2B'
}

def split_and_hyphenate(year):
    return f"{year}-{str(year + 1)[-2:]}"

def save_figure(filename):
    plt.savefig(filename, dpi=300, bbox_inches='tight', transparent=True)
    print(f"✅ Saved: {filename}")

# ----------------------------------------------------------------------
# PREP
# ----------------------------------------------------------------------

df = roster.copy()
df['season'] = df['season'].astype(str)
df['first_year'] = df.groupby('id')['season'].transform('min').str[:4].astype(int)
df['last_year'] = df.groupby('id')['season'].transform('max').str[:4].astype(int)
latest_year = df['season'].str[:4].astype(int).max()

# Remove active players
df = df[df['last_year'] < latest_year].copy()

# Create position_group if needed
position_map = {'C': 'Forward', 'L': 'Forward', 'R': 'Forward', 'D': 'Defense', 'G': 'Goalie'}
df['position_group'] = df['position'].map(position_map)

# Drop rows without position group
df = df[df['position_group'].notna()].copy()

# ----------------------------------------------------------------------
# METRIC 1: Number of Teams
# ----------------------------------------------------------------------

num_teams_df = (
    df.groupby('id')
    .agg(first_year=('first_year', 'first'),
         position_group=('position_group', 'first'),
         num_teams=('team', pd.Series.nunique))
    .reset_index()
)

# ----------------------------------------------------------------------
# METRIC 2: Avg Duration per Team
# ----------------------------------------------------------------------

career_lengths = df.groupby('id').size().reset_index(name='career_length')
num_teams_df = num_teams_df.merge(career_lengths, on='id')
num_teams_df['avg_duration_per_team'] = num_teams_df['career_length'] / num_teams_df['num_teams']

# ----------------------------------------------------------------------
# METRIC 3: Retained on First Team (≥50%)
# ----------------------------------------------------------------------

first_team_df = (
    df.sort_values(['id', 'season'])
    .groupby('id')
    .agg(first_team=('team', 'first'))
    .reset_index()
)

merged_df = df.merge(first_team_df, on='id')
merged_df['played_for_first_team'] = merged_df['team'] == merged_df['first_team']

retention_df = (
    merged_df.groupby('id')
    .agg(first_year=('first_year', 'first'),
         position_group=('position_group', 'first'),
         total_seasons=('season', 'count'),
         seasons_on_first_team=('played_for_first_team', 'sum'))
    .reset_index()
)
retention_df['retained_on_first_team'] = (retention_df['seasons_on_first_team'] / retention_df['total_seasons']) >= 0.5

# ----------------------------------------------------------------------
# MERGE METRICS AND GROUP BY YEAR + POSITION
# ----------------------------------------------------------------------

summary_df = num_teams_df.merge(retention_df[['id', 'retained_on_first_team']], on='id')

summary_by_year_pos = (
    summary_df.groupby(['first_year', 'position_group'])
    .agg(avg_num_teams=('num_teams', 'mean'),
         avg_duration_per_team=('avg_duration_per_team', 'mean'),
         pct_retained_on_first_team=('retained_on_first_team', 'mean'))
    .reset_index()
)
summary_by_year_pos['x_pos'] = summary_by_year_pos.groupby('position_group').cumcount()

# ----------------------------------------------------------------------
# PLOT 1: Number of Teams
# ----------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 7))
for group in ['Forward', 'Defense', 'Goalie']:
    d = summary_by_year_pos[summary_by_year_pos['position_group'] == group]
    ax.scatter(d['x_pos'], d['avg_num_teams'], color=color_map[group], alpha=0.2, s=50)
    smoothed = lowess(d['avg_num_teams'], d['x_pos'], frac=0.2, return_sorted=True)
    ax.plot(smoothed[:, 0], smoothed[:, 1], color=color_map[group], linewidth=3.5, label=group)

ax.set_ylim(1, 6)
tick_indices = d['x_pos'][::10]
tick_labels = [split_and_hyphenate(y) for y in d['first_year'].iloc[::10]]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, fontsize=14)
ax.set_ylabel("Avg. Number of Teams Played For", fontsize=18)
ax.tick_params(axis='y', labelsize=14)
ax.set_xlabel("")
sns.despine()
ax.grid(False)

left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)
fig.suptitle("Players now play for more teams during their career", fontsize=20, weight='bold', x=left_x, ha='left', y=0.97)
fig.text(left_x, 0.87, "Compared to earlier decades, modern NHL players change teams more frequently over their careers.", fontsize=14, ha='left')
fig.text(0.9, 0.01, "Data: Average number of unique teams per player by debut year and position", fontsize=10, style='italic', ha='right')
ax.legend(title="Position", fontsize=13, title_fontsize=14)
save_figure("nhl_avg_teams_by_position.png")
plt.show()

# ----------------------------------------------------------------------
# PLOT 2: Avg Duration per Team
# ----------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 7))
for group in ['Forward', 'Defense', 'Goalie']:
    d = summary_by_year_pos[summary_by_year_pos['position_group'] == group]
    ax.scatter(d['x_pos'], d['avg_duration_per_team'], color=color_map[group], alpha=0.2, s=50)
    smoothed = lowess(d['avg_duration_per_team'], d['x_pos'], frac=0.2, return_sorted=True)
    ax.plot(smoothed[:, 0], smoothed[:, 1], color=color_map[group], linewidth=3.5, label=group)

ax.set_ylim(1, 10)
tick_indices = d['x_pos'][::10]
tick_labels = [split_and_hyphenate(y) for y in d['first_year'].iloc[::10]]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, fontsize=14)
ax.set_ylabel("Avg. Seasons per Team", fontsize=18)
ax.tick_params(axis='y', labelsize=14)
ax.set_xlabel("")
sns.despine()
ax.grid(False)

left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)
fig.suptitle("Tenure on individual teams has declined over time", fontsize=20, weight='bold', x=left_x, ha='left', y=0.97)
fig.text(left_x, 0.87, "Players used to spend 5–7 years on average with a single team. That number has dropped in modern eras.", fontsize=14, ha='left')
fig.text(0.9, 0.01, "Data: Average number of seasons per team by debut year and position", fontsize=10, style='italic', ha='right')
ax.legend(title="Position", fontsize=13, title_fontsize=14)
save_figure("nhl_avg_duration_per_team_by_position.png")
plt.show()

# ----------------------------------------------------------------------
# PLOT 3: Retained on First Team
# ----------------------------------------------------------------------

fig, ax = plt.subplots(figsize=(12, 7))
for group in ['Forward', 'Defense', 'Goalie']:
    d = summary_by_year_pos[summary_by_year_pos['position_group'] == group]
    ax.scatter(d['x_pos'], d['pct_retained_on_first_team'], color=color_map[group], alpha=0.2, s=50)
    smoothed = lowess(d['pct_retained_on_first_team'], d['x_pos'], frac=0.2, return_sorted=True)
    ax.plot(smoothed[:, 0], smoothed[:, 1], color=color_map[group], linewidth=3.5, label=group)

ax.set_ylim(0, 1)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y * 100)}%"))
tick_indices = d['x_pos'][::10]
tick_labels = [split_and_hyphenate(y) for y in d['first_year'].iloc[::10]]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, fontsize=14)
ax.set_ylabel("Share Spending ≥50% Career on Debut Team", fontsize=18)
ax.tick_params(axis='y', labelsize=14)
ax.set_xlabel("")
sns.despine()
ax.grid(False)

left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)
fig.suptitle("Debut team loyalty has dropped sharply in recent eras", fontsize=20, weight='bold', x=left_x, ha='left', y=0.97)
fig.text(left_x, 0.87, "A majority of NHL players used to spend at least half their career on their debut team.\nToday, that's true for fewer than 1 in 3 players.", fontsize=14, ha='left')
fig.text(0.9, 0.01, "Data: Proportion of players spending ≥50% of career with debut team by debut year and position", fontsize=10, style='italic', ha='right')
ax.legend(title="Position", fontsize=13, title_fontsize=14)
save_figure("nhl_debut_team_retention_by_position.png")
plt.show()


# ----------------------------------------------------------------------
#
# CAREER LENGTH
#
# ----------------------------------------------------------------------

# Define the formatter if not done already
def split_and_hyphenate(year):
    return f"{year}-{str(year + 1)[-2:]}"  # e.g., 2000 → 2000–01

# Count how many seasons each player appears = career length
career_df = (
    roster.groupby('id')
    .agg(
        first_season=('season', 'min'),
        career_length=('season', 'count')
    )
    .reset_index()
)

# Get first year as integer (YYYY)
career_df['first_year'] = career_df['first_season'].astype(str).str[:4].astype(int)

# Remove active players: those who played in the latest year
latest_season = roster['season'].max()
latest_year = int(str(latest_season)[:4])
last_season = roster.groupby('id')['season'].max().reset_index(name='last_season')
last_season['last_year'] = last_season['last_season'].astype(str).str[:4].astype(int)
career_df = career_df.merge(last_season[['id', 'last_year']], on='id')
career_df = career_df[career_df['last_year'] < latest_year].copy()

# Compute average career length by debut year (numeric)
avg_career = (
    career_df.groupby('first_year')['career_length']
    .mean()
    .reset_index()
    .rename(columns={'first_year': 'year'})
)

# Add x position (just index)
avg_career['x_pos'] = avg_career.index

# LOESS smoothing
smoothed = lowess(
    endog=avg_career['career_length'],
    exog=avg_career['x_pos'],
    frac=0.2,
    return_sorted=True
)

# PLOT
sns.set(style="whitegrid")
mpl.rcParams['font.family'] = 'Charter'
fig, ax = plt.subplots(figsize=(12, 7))

# Raw dots
ax.scatter(
    avg_career['x_pos'],
    avg_career['career_length'],
    color='#3B4B64',  # Dusty navy
    alpha=0.2,
    s=50
)

# Smoothed line
ax.plot(
    smoothed[:, 0],
    smoothed[:, 1],
    color='#E76F2B',  # Warm orange
    linewidth=3.5
)

# Y-axis
ax.set_ylim(0, 25)
ax.set_yticks(range(0, 26, 5))
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x)}"))

# X-axis: tick every ~10 years
tick_indices = avg_career.index[::10]
tick_labels = [split_and_hyphenate(yr) for yr in avg_career['year'].iloc[::10]]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)

# Other styling
sns.despine()
ax.grid(False)
ax.tick_params(axis='y', labelsize=14)
ax.set_ylabel("Career Length (Years)", fontsize=18)
ax.set_xlabel("")

# Title and subtitle
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)
fig.suptitle(
    "The average NHL career length has subtly declined",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)
fig.text(
    left_x,
    0.87,
    "While some players have long tenures, most careers are short. The average career\nlength has dipped slightly over time — especially for players debuting after 2000.",
    fontsize=14,
    ha='left'
)
fig.text(
    0.9,
    0.01,
    "Data: Career length by debut season with LOESS-smoothed trend",
    fontsize=10,
    style='italic',
    ha='right'
)

ax.legend().remove()
save_figure("nhl_career_length_by_first_year.png")
plt.show()



# ----------------------------------------------------------------------
#
# CAREER LENGTH BY POSITION
#
# ----------------------------------------------------------------------
# Define formatter
def split_and_hyphenate(year):
    return f"{year}-{str(year + 1)[-2:]}"

# Map player positions to general group
position_map = {'C': 'Forward', 'L': 'Forward', 'R': 'Forward', 'D': 'Defense', 'G': 'Goalie'}
roster['position_group'] = roster['position'].map(position_map)

# Compute career stats
career_df = (
    roster.groupby('id')
    .agg(
        first_season=('season', 'min'),
        career_length=('season', 'count'),
        position_group=('position_group', 'first')
    )
    .reset_index()
)

# Get year values
career_df['first_year'] = career_df['first_season'].astype(str).str[:4].astype(int)

# Remove active players
latest_season = roster['season'].max()
latest_year = int(str(latest_season)[:4])
last_season = roster.groupby('id')['season'].max().reset_index(name='last_season')
last_season['last_year'] = last_season['last_season'].astype(str).str[:4].astype(int)
career_df = career_df.merge(last_season[['id', 'last_year']], on='id')
career_df = career_df[career_df['last_year'] < latest_year].copy()

# Remove players without a position group
career_df = career_df[career_df['position_group'].notna()].copy()

# Compute average career length by debut year and position
avg_career = (
    career_df.groupby(['first_year', 'position_group'])['career_length']
    .mean()
    .reset_index()
    .rename(columns={'first_year': 'year'})
)

# Assign x positions per group (clean index per position group)
avg_career['x_pos'] = avg_career.groupby('position_group').cumcount()

# Define color map (Wes-inspired Oilers tones)
color_map = {
    'Forward': '#264653',
    'Defense': '#2A9D8F',
    'Goalie': '#E76F2B'
}

# PLOT
sns.set(style="whitegrid")
mpl.rcParams['font.family'] = 'Charter'
fig, ax = plt.subplots(figsize=(12, 7))

for position in ['Forward', 'Defense', 'Goalie']:
    group_df = avg_career[avg_career['position_group'] == position]

    # Raw dots
    ax.scatter(
        group_df['x_pos'],
        group_df['career_length'],
        color=color_map[position],
        alpha=0.2,
        s=50
    )

    # LOESS smoothed line
    smoothed = lowess(
        endog=group_df['career_length'],
        exog=group_df['x_pos'],
        frac=0.2,
        return_sorted=True
    )
    ax.plot(
        smoothed[:, 0],
        smoothed[:, 1],
        color=color_map[position],
        linewidth=3.5,
        label=position
    )

# Axis formatting
ax.set_ylim(0, 25)
ax.set_yticks(range(0, 26, 5))
ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{int(x)}"))

# X ticks (just show debut years for Forwards, every 10 years)
ref_group = avg_career[avg_career['position_group'] == 'Forward']
tick_indices = ref_group['x_pos'][::10]
tick_labels = [split_and_hyphenate(y) for y in ref_group['year'].iloc[::10]]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)

# Final styling
sns.despine()
ax.grid(False)
ax.tick_params(axis='y', labelsize=14)
ax.set_ylabel("Career Length (Years)", fontsize=18)
ax.set_xlabel("")

# Titles
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)
fig.suptitle(
    "NHL career length varies slightly by position group",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)
fig.text(
    left_x,
    0.87,
    "Goalies tend to have slightly longer careers, while forwards and defensemen show\na similar but declining trend over time.",
    fontsize=14,
    ha='left'
)
fig.text(
    0.9,
    0.01,
    "Data: Career length by debut season, excluding active players; LOESS-smoothed trend",
    fontsize=10,
    style='italic',
    ha='right'
)

ax.legend(title="Position", fontsize=13, title_fontsize=14)
save_figure("nhl_career_length_by_first_year_position.png")
plt.show()

# ----------------------------------------------------------------------
#
# TEAM TENURE
#
# ----------------------------------------------------------------------

# Define formatter
def split_and_hyphenate(year):
    return f"{year}-{str(year + 1)[-2:]}"  # e.g., 2000 → 2000–01

# Copy original data
df = roster.copy()

# Compute debut year
first_year_df = (
    df.sort_values(['id', 'season'])
    .groupby('id')['season']
    .first()
    .reset_index(name='first_season')
)
first_year_df['first_year'] = first_year_df['first_season'].astype(str).str[:4].astype(int)
df = df.merge(first_year_df[['id', 'first_year']], on='id')

# Count how many seasons per team per player
team_counts = df.groupby(['id', 'team']).size().reset_index(name='seasons_with_team')

# Find most-played team for each player
max_team_df = (
    team_counts
    .sort_values(['id', 'seasons_with_team'], ascending=[True, False])
    .drop_duplicates('id')
    .rename(columns={'seasons_with_team': 'max_team_seasons'})
)

# Compute career length
career_lengths = df.groupby('id').size().reset_index(name='career_length')

# Get last year for active check
last_year_df = df.groupby('id')['season'].max().reset_index(name='last_season')
last_year_df['last_year'] = last_year_df['last_season'].astype(str).str[:4].astype(int)
latest_year = int(str(df['season'].max())[:4])

# Merge all into one dataframe
tenure_df = (
    max_team_df
    .merge(career_lengths, on='id')
    .merge(first_year_df[['id', 'first_year']], on='id')
    .merge(last_year_df[['id', 'last_year']], on='id')
)

# Drop active players
tenure_df = tenure_df[tenure_df['last_year'] < latest_year].copy()

# Compute proportion of career on most-played team
tenure_df['max_team_share'] = tenure_df['max_team_seasons'] / tenure_df['career_length']

# Compute average by debut year
avg_tenure = (
    tenure_df.groupby('first_year')['max_team_share']
    .mean()
    .reset_index()
    .rename(columns={'first_year': 'year'})
)
avg_tenure['x_pos'] = avg_tenure.index

# Smooth with LOESS
from statsmodels.nonparametric.smoothers_lowess import lowess
smoothed = lowess(
    endog=avg_tenure['max_team_share'],
    exog=avg_tenure['x_pos'],
    frac=0.2,
    return_sorted=True
)

# Plotting
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
sns.set(style="whitegrid")
mpl.rcParams['font.family'] = 'Charter'
fig, ax = plt.subplots(figsize=(12, 7))

# Raw points
ax.scatter(
    avg_tenure['x_pos'],
    avg_tenure['max_team_share'],
    color='#3B4B64',
    alpha=0.2,
    s=50
)

# Smoothed line
ax.plot(
    smoothed[:, 0],
    smoothed[:, 1],
    color='#E76F2B',
    linewidth=3.5
)

# Y-axis formatting
ax.set_ylim(0, 1)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y * 100)}%"))

# X-axis formatting
tick_indices = avg_tenure.index[::10]
tick_labels = [split_and_hyphenate(yr) for yr in avg_tenure['year'].iloc[::10]]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, fontsize=14)

# Style
sns.despine()
ax.grid(False)
ax.tick_params(axis='y', labelsize=14)
ax.set_ylabel("Share of Career on Primary Team", fontsize=18)
ax.set_xlabel("")

# Titles
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)
fig.suptitle(
    "NHL players spend less of their career on a single team than they used to",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)
fig.text(
    left_x,
    0.87,
    "Earlier eras saw players spending most of their careers on a single team.\nIn modern hockey, movement is the norm.",
    fontsize=14,
    ha='left'
)
fig.text(
    0.9,
    0.01,
    "Data: Proportion of career played on most-played team by debut season (LOESS-smoothed)",
    fontsize=10,
    style='italic',
    ha='right'
)

ax.legend().remove()
save_figure("nhl_primary_team_tenure_trend.png")
plt.show()

# ----------------------------------------------------------------------
#
# TEAM TENURE BY POSITION
#
# ----------------------------------------------------------------------

# Define formatter
def split_and_hyphenate(year):
    return f"{year}-{str(year + 1)[-2:]}"

# Copy original data
df = roster.copy()

# Ensure position group mapping is complete
position_map = {'C': 'Forward', 'L': 'Forward', 'R': 'Forward', 'D': 'Defense', 'G': 'Goalie'}
df['position_group'] = df['position'].map(position_map)

# Compute debut year
first_year_df = (
    df.sort_values(['id', 'season'])
    .groupby('id')['season']
    .first()
    .reset_index(name='first_season')
)
first_year_df['first_year'] = first_year_df['first_season'].astype(str).str[:4].astype(int)
df = df.merge(first_year_df[['id', 'first_year']], on='id')

# Count how many seasons per team per player
team_counts = df.groupby(['id', 'team']).size().reset_index(name='seasons_with_team')

# Most-played team per player
max_team_df = (
    team_counts
    .sort_values(['id', 'seasons_with_team'], ascending=[True, False])
    .drop_duplicates('id')
    .rename(columns={'seasons_with_team': 'max_team_seasons'})
)

# Career length
career_lengths = df.groupby('id').size().reset_index(name='career_length')

# Last year played
last_year_df = df.groupby('id')['season'].max().reset_index(name='last_season')
last_year_df['last_year'] = last_year_df['last_season'].astype(str).str[:4].astype(int)
latest_year = int(str(df['season'].max())[:4])

# Position group
position_df = df.groupby('id')['position_group'].first().reset_index()

# Combine all
tenure_df = (
    max_team_df
    .merge(career_lengths, on='id')
    .merge(first_year_df[['id', 'first_year']], on='id')
    .merge(last_year_df[['id', 'last_year']], on='id')
    .merge(position_df, on='id')
)

# Drop active players + missing position
tenure_df = tenure_df[(tenure_df['last_year'] < latest_year) & tenure_df['position_group'].notna()].copy()

# Compute share of career on most-played team
tenure_df['max_team_share'] = tenure_df['max_team_seasons'] / tenure_df['career_length']

# Average by debut year & position
avg_tenure = (
    tenure_df.groupby(['first_year', 'position_group'])['max_team_share']
    .mean()
    .reset_index()
    .rename(columns={'first_year': 'year'})
)

# Assign x-axis position
avg_tenure['x_pos'] = avg_tenure.groupby('position_group').cumcount()

# Define color map
color_map = {
    'Forward': '#264653',
    'Defense': '#2A9D8F',
    'Goalie': '#E76F2B'
}

# Plot
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.ticker import FuncFormatter
from statsmodels.nonparametric.smoothers_lowess import lowess

sns.set(style="whitegrid")
mpl.rcParams['font.family'] = 'Charter'
fig, ax = plt.subplots(figsize=(12, 7))

# Plot each position group
for group in ['Forward', 'Defense', 'Goalie']:
    group_df = avg_tenure[avg_tenure['position_group'] == group]

    # Raw dots
    ax.scatter(
        group_df['x_pos'],
        group_df['max_team_share'],
        color=color_map[group],
        alpha=0.2,
        s=50
    )

    # LOESS line
    smoothed = lowess(
        endog=group_df['max_team_share'],
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

# Y-axis
ax.set_ylim(0, 1)
ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: f"{int(y * 100)}%"))

# X-axis labels (from forwards group)
ref_group = avg_tenure[avg_tenure['position_group'] == 'Forward']
tick_indices = ref_group['x_pos'][::10]
tick_labels = [split_and_hyphenate(y) for y in ref_group['year'].iloc[::10]]
ax.set_xticks(tick_indices)
ax.set_xticklabels(tick_labels, rotation=0, fontsize=14)

# Style
sns.despine()
ax.grid(False)
ax.tick_params(axis='y', labelsize=14)
ax.set_ylabel("Share of Career on Primary Team", fontsize=18)
ax.set_xlabel("")

# Titles
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)
fig.suptitle(
    "Goalies tend to stay with one team longer than skaters",
    fontsize=20,
    weight='bold',
    x=left_x,
    ha='left',
    y=0.97
)
fig.text(
    left_x,
    0.87,
    "Across eras, goalies have shown more franchise loyalty or stability than forwards and defensemen.\nIn modern years, all roles show more movement.",
    fontsize=14,
    ha='left'
)
fig.text(
    0.9,
    0.01,
    "Data: Proportion of career spent on most-played team by debut year and position group (LOESS-smoothed)",
    fontsize=10,
    style='italic',
    ha='right'
)

ax.legend(title="Position", fontsize=13, title_fontsize=14)
save_figure("nhl_primary_team_tenure_by_position.png")
plt.show()