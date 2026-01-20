#!/usr/bin/env python3
 # -*- coding: utf-8 -*-
"""
Depth vs Goaltending Analysis - Figure Generation
Creates publication-ready figures for blog post
"""

import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib as mpl
from scipy.stats import pearsonr
from statsmodels.nonparametric.smoothers_lowess import lowess
import os

# ==============================================================================
# SETUP
# ==============================================================================

# Brand setup
mpl.rcParams['font.family'] = 'Charter'

PROJECT_ROOT = "/Users/dwiwad/dev/hockey_site"
DATA_PATH = os.path.join(PROJECT_ROOT, "data/total-depth-index/all_seasons")

# Brand colors
col_blue_pale = '#3B4B64'
col_blue_dark = '#041E42'
col_oil_orange = '#FF4C00'
col_gray = '#9AA3AF'
col_white = '#FFFFFF'

def save_figure(filename):
    """Save figure to deep-dives directory"""
    output_dir = os.path.join(PROJECT_ROOT, "static/images/deep-dives/depth-and-goaltending")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    plt.savefig(output_path, dpi=300, bbox_inches='tight', transparent=True)
    print(f"✅ Saved: {output_path}")

# ==============================================================================
# DATA LOADING AND PREPARATION
# ==============================================================================

print("Loading data...")

# Load depth data
data = pd.read_csv(os.path.join(DATA_PATH, "final_data_20102025.csv"))
data['season'] = data['season'].astype(str)
data['game_id'] = data['game_id'].astype(int)

# Load schedule data
schedule = pd.read_csv(os.path.join(DATA_PATH, "all_games_meta_20102025.csv"))
schedule['season'] = schedule['season'].astype(str)
schedule['game_id'] = schedule['id'].astype(int)

# Extract goals from schedule
goals_data = schedule[['game_id', 'season',
                       'homeTeam.abbrev', 'awayTeam.abbrev',
                       'homeTeam.score', 'awayTeam.score']].copy()
goals_data.columns = ['game_id', 'season', 'home_abbrev', 'away_abbrev',
                      'home_goals', 'away_goals']
goals_data['home_abbrev'] = goals_data['home_abbrev'].str.upper()
goals_data['away_abbrev'] = goals_data['away_abbrev'].str.upper()

# Merge home data
home_data = data.merge(
    goals_data[['game_id', 'season', 'home_abbrev', 'home_goals', 'away_goals']],
    on=['game_id', 'season'],
    how='inner'
)
home_data = home_data[home_data['teamAbbrev'] == home_data['home_abbrev']].copy()

# Merge away data
away_data = data.merge(
    goals_data[['game_id', 'season', 'away_abbrev', 'home_goals', 'away_goals']],
    on=['game_id', 'season'],
    how='inner'
)
away_data = away_data[away_data['teamAbbrev'] == away_data['away_abbrev']].copy()

# Create matchup-level data
matchup_data = home_data.merge(
    away_data[['game_id', 'season', 'teamAbbrev', 'tdi_factor', 'xgoal']],
    on=['game_id', 'season'],
    how='inner',
    suffixes=('_home', '_away')
)

# Calculate GSAx (Goals Saved Above Expected)
matchup_data['gsax_home'] = matchup_data['xgoal_away'] - matchup_data['away_goals']
matchup_data['gsax_away'] = matchup_data['xgoal_home'] - matchup_data['home_goals']

# Determine winner
matchup_data['home_win'] = (matchup_data['home_goals'] > matchup_data['away_goals']).astype(int)

# Create winner/loser perspective
matchup_data['winner_depth'] = np.where(
      matchup_data['home_win'] == 1,
      matchup_data['tdi_factor_home'],
      matchup_data['tdi_factor_away']
  )
matchup_data['loser_depth'] = np.where(
      matchup_data['home_win'] == 1,
      matchup_data['tdi_factor_away'],
      matchup_data['tdi_factor_home']
  )
matchup_data['winner_gsax'] = np.where(
      matchup_data['home_win'] == 1,
      matchup_data['gsax_home'],
      matchup_data['gsax_away']
  )
matchup_data['loser_gsax'] = np.where(
      matchup_data['home_win'] == 1,
      matchup_data['gsax_away'],
      matchup_data['gsax_home']
  )

# Calculate differentials
matchup_data['depth_diff'] = matchup_data['winner_depth'] - matchup_data['loser_depth']
matchup_data['gsax_diff'] = matchup_data['winner_gsax'] - matchup_data['loser_gsax']

# Categorize win types
def categorize_depth_win(depth_diff):
      if depth_diff >= 0.05:
          return 'High-depth win'
      elif depth_diff <= -0.05:
          return 'Low-depth win'
      else:
          return 'Equal-depth'

matchup_data['win_type'] = matchup_data['depth_diff'].apply(categorize_depth_win)

# Game type
matchup_data['game_type'] = matchup_data['game_id'].astype(str).str[4:6]
matchup_data['game_type_label'] = matchup_data['game_type'].map({
      '02': 'Regular Season',
      '03': 'Playoffs'
  })

print(f"✅ Loaded {len(matchup_data):,} games")
print(f"   Win types: {matchup_data['win_type'].value_counts().to_dict()}")

# ==============================================================================
# FIGURE 1: WIN TYPE COMPARISON (VIOLIN + BOX)
# ==============================================================================

print("\nGenerating Figure 1: Win Type Comparison...")

# Calculate summary statistics
win_type_summary = matchup_data.groupby('win_type')['gsax_diff'].agg([
      ('mean', 'mean'),
      ('se', lambda x: x.std() / np.sqrt(len(x))),
      ('n', 'count')
  ]).reset_index()

win_type_order = ['Low-depth win', 'Equal-depth', 'High-depth win']
win_type_summary['win_type'] = pd.Categorical(
      win_type_summary['win_type'],
      categories=win_type_order,
      ordered=True
  )
win_type_summary = win_type_summary.sort_values('win_type')

# Create figure
fig, ax = plt.subplots(figsize=(12, 7))

# Colors for win types
colors = {
      'Low-depth win': col_oil_orange,
      'Equal-depth': col_gray,
      'High-depth win': col_blue_dark
  }

plot_data = matchup_data[matchup_data['win_type'].isin(win_type_order)].copy()
plot_data['win_type'] = pd.Categorical(plot_data['win_type'],
                                         categories=win_type_order,
                                         ordered=True)

# Violin plots
for i, wt in enumerate(win_type_order):
      wt_data = plot_data[plot_data['win_type'] == wt]['gsax_diff'].dropna()

      # Create violin WITHOUT the default quartile lines
      parts = ax.violinplot([wt_data], positions=[i], widths=0.6,
                            showmeans=False, showmedians=False, showextrema=False)

      for pc in parts['bodies']:
          pc.set_facecolor(colors[wt])
          pc.set_alpha(0.7)
          pc.set_edgecolor(colors[wt])
          pc.set_linewidth(1.5)

      # Box plot overlay (this provides the quartile info cleanly)
      bp = ax.boxplot([wt_data], positions=[i], widths=0.15,
                      patch_artist=True,
                      boxprops=dict(facecolor=col_white, alpha=0.9, edgecolor=colors[wt], linewidth=1.5),
                      medianprops=dict(color=colors[wt], linewidth=2.5),
                      whiskerprops=dict(color=colors[wt], linewidth=1.5),
                      capprops=dict(color=colors[wt], linewidth=1.5),
                      showfliers=False)

# Reference line
ax.axhline(0, color='black', linestyle='--', linewidth=1, alpha=0.4)

# Styling
sns.despine()
ax.grid(False)
ax.set_xticks([0, 1, 2])
ax.set_xticklabels(win_type_order, fontsize=14)
ax.set_ylabel('GSAx Differential (Winner − Loser)', fontsize=18)
ax.tick_params(axis='y', labelsize=14)

# Title
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

fig.suptitle(
      'Low-Depth Wins Require More Goaltending Performance',
      fontsize=20,
      weight='bold',
      x=left_x,
      ha='left',
      y=0.97
  )

fig.text(
      left_x,
      0.87,
      'Goalie advantage needed is ~0.5 goals higher when winning team lacks depth',
      fontsize=14,
      ha='left'
  )

fig.text(
      0.9,
      0.01,
      'Data: 19,197 NHL games (2010-2025) | Violin width shows distribution density',
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure('figure_1_win_type_comparison.png')
plt.show()

# After Figure 1, add this:
print("\n" + "="*60)
print("SAMPLE SIZES FOR T-TEST")
print("="*60)
print(matchup_data['win_type'].value_counts())

  # Calculate df for high vs low comparison
n_high = len(matchup_data[matchup_data['win_type'] == 'High-depth win'])
n_low = len(matchup_data[matchup_data['win_type'] == 'Low-depth win'])
df_comparison = n_high + n_low - 2
print(f"\nDegrees of freedom (High vs Low): {df_comparison:,}")
print("="*60)

# ==============================================================================
# FIGURE 2: THE QUADRANT PLOT (HERO IMAGE)
# ==============================================================================

print("\nGenerating Figure 2: Quadrant Plot (Hero Image)...")

fig, ax = plt.subplots(figsize=(14, 10))

# Calculate SYMMETRIC limits around 0
x_max = np.percentile(np.abs(matchup_data['depth_diff'].dropna()), 99) * 1.25
y_max = np.percentile(np.abs(matchup_data['gsax_diff'].dropna()), 99) * 1.25

x_lim = [-x_max, x_max]
y_lim = [-y_max, y_max]

# Scatter all games
ax.scatter(matchup_data['depth_diff'], matchup_data['gsax_diff'],
             alpha=0.12, s=18, color=col_blue_pale, edgecolors='none')

# Reference lines
ax.axhline(0, color='black', linestyle='--', linewidth=1.2, alpha=0.5)
ax.axvline(0, color='black', linestyle='--', linewidth=1.2, alpha=0.5)

# LOESS smooth
depth_clean = matchup_data[['depth_diff', 'gsax_diff']].dropna()
smoothed = lowess(depth_clean['gsax_diff'], depth_clean['depth_diff'], frac=0.15)
ax.plot(smoothed[:, 0], smoothed[:, 1], color=col_oil_orange,
          linewidth=4, label='LOESS trend', zorder=10, alpha=0.9)

# Quadrant labels - positioned within the symmetric bounds
label_offset_x = x_max * 0.82
label_offset_y = y_max * 0.82

quadrant_labels = [
      (label_offset_x, label_offset_y,
       "Dominant wins\n(Depth + Goaltending)", col_blue_dark, 'right', 'top'),
      (label_offset_x, -label_offset_y,
       "Depth-driven wins\n(Goalie not needed)", '#2a9d8f', 'right', 'bottom'),
      (-label_offset_x, label_offset_y,
       "Goalie steals\n(Top-heavy wins)", col_oil_orange, 'left', 'top'),
      (-label_offset_x, -label_offset_y,
       "Chaos\n(Both disadvantaged)", col_gray, 'left', 'bottom'),
  ]

for x, y, text, color, ha_val, va_val in quadrant_labels:
      ax.text(x, y, text,
              fontsize=13, weight='bold', style='italic',
              ha=ha_val, va=va_val, color=color, alpha=0.65,
              bbox=dict(boxstyle='round,pad=0.6', facecolor='white',
                       edgecolor=color, linewidth=2.5, alpha=0.9))

# Set symmetric limits
ax.set_xlim(x_lim)
ax.set_ylim(y_lim)

# Styling
sns.despine()
ax.grid(False)
ax.set_xlabel('Depth Advantage (Winner − Loser)', fontsize=16, weight='bold')
ax.set_ylabel('Goalie Advantage (Winner − Loser GSAx)', fontsize=16, weight='bold')
ax.tick_params(axis='both', labelsize=13)
ax.legend(fontsize=12, loc='upper right', frameon=True, fancybox=True)

# Title
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.88)

fig.suptitle(
      'How NHL Games Are Won',
      fontsize=22,
      weight='bold',
      x=left_x,
      ha='left',
      y=0.96
  )

fig.text(
      left_x,
      0.90,
      'Depth and goaltending compensate for each other; teams need at least one advantage',
      fontsize=14,
      ha='left'
  )

fig.text(
      0.9,
      0.01,
      'Data: Each point is one game | Orange line shows LOESS trend (r = −0.19)',
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure('figure_2_quadrant_hero.png')
plt.show()

# After Figure 2, add quadrant analysis
quadrant_counts = pd.DataFrame()

# Define quadrants (adjust thresholds as needed)
depth_threshold = 0.0  # center line
gsax_threshold = 0.0   # center line

quadrants = {
      'Dominant (both)': (matchup_data['depth_diff'] > depth_threshold) & (matchup_data['gsax_diff'] > gsax_threshold),
      'Goalie steals': (matchup_data['depth_diff'] < depth_threshold) & (matchup_data['gsax_diff'] > gsax_threshold),
      'Depth-driven': (matchup_data['depth_diff'] > depth_threshold) & (matchup_data['gsax_diff'] < gsax_threshold),
      'Chaos': (matchup_data['depth_diff'] < depth_threshold) & (matchup_data['gsax_diff'] < gsax_threshold)
  }

for name, mask in quadrants.items():
      count = mask.sum()
      pct = count / len(matchup_data) * 100
      print(f"{name}: {count:,} games ({pct:.1f}%)")

# ==============================================================================
# FIGURE 3: TEAM IDENTITY MAP (2024-25)
# ==============================================================================

print("\nGenerating Figure 3: Team Identity Map (Plotly Style + Fig 2 Design)...")

import requests
from matplotlib.colors import LinearSegmentedColormap

# Filter to current season
current_season = '20242025'
season_data = matchup_data[matchup_data['season'] == current_season].copy()

# Create team-game long format (ALL GAMES, not just wins)
team_games = []
for _, row in season_data.iterrows():
      # Home team
      team_games.append({
          'team': row['teamAbbrev_home'],
          'depth_adv': row['tdi_factor_home'] - row['tdi_factor_away'],
          'gsax_adv': row['gsax_home'] - row['gsax_away'],
          'won': (row['home_goals'] > row['away_goals'])
      })
      # Away team
      team_games.append({
          'team': row['teamAbbrev_away'],
          'depth_adv': row['tdi_factor_away'] - row['tdi_factor_home'],
          'gsax_adv': row['gsax_away'] - row['gsax_home'],
          'won': (row['away_goals'] > row['home_goals'])
      })

team_games_df = pd.DataFrame(team_games)

# Calculate team identity (average across ALL games)
team_identity = team_games_df.groupby('team').agg({
      'depth_adv': 'mean',
      'gsax_adv': 'mean',
      'won': ['sum', 'count']
  }).reset_index()
team_identity.columns = ['team', 'avg_depth_adv', 'avg_gsax_adv', 'wins', 'games']
team_identity['win_pct'] = team_identity['wins'] / team_identity['games']

# Fetch standings from NHL API (use specific date or "now")
standings_date = "2025-04-17"  # End of season (or use "now" for current)
standings_url = f"https://api-web.nhle.com/v1/standings/{standings_date}"
# standings_url = "https://api-web.nhle.com/v1/standings/now"  # Alternative: current

response = requests.get(standings_url)
standings_data = response.json()

# Extract team standings
standings_list = []
for team in standings_data['standings']:
      standings_list.append({
          'team': team['teamAbbrev']['default'],
          'league_rank': team['leagueSequence']
      })

standings_df = pd.DataFrame(standings_list)

# Merge with team identity
team_identity = team_identity.merge(standings_df, on='team', how='left')

# Calculate standing score (1 = best, 0 = worst)
n_teams = team_identity['league_rank'].max()
team_identity['standing_score'] = 1 - (team_identity['league_rank'] - 1) / (n_teams - 1)

# Create custom colormap (Red → White → Green, matching R)
colors_standings = ['#C0392B', 'white', '#1E9E5A']
cmap_standings = LinearSegmentedColormap.from_list('standings', colors_standings, N=256)

# Create figure
fig, ax = plt.subplots(figsize=(14, 10))
  
# Calculate SYMMETRIC limits (Plotly style: max * 1.4)
x_range = team_identity['avg_depth_adv'].abs().max() * 1.4
y_range = team_identity['avg_gsax_adv'].abs().max() * 1.4

# Scatter - FIXED SIZE, colored by standings
scatter = ax.scatter(
      team_identity['avg_depth_adv'],
      team_identity['avg_gsax_adv'],
      s=200,
      c=team_identity['standing_score'],
      cmap='RdYlGn',
      vmin=0, vmax=1,
      alpha=0.85,
      edgecolors='#333333',
      linewidth=1,
      zorder=5
  )

# Add labels CENTERED ABOVE markers (Plotly style)
for _, row in team_identity.iterrows():
      ax.text(
          row['avg_depth_adv'],
          row['avg_gsax_adv'] + (y_range * 0.04),
          row['team'],
          fontsize=11,
          weight='bold',
          color='black',
          ha='center',
          va='bottom',
          zorder=10
      )

# Reference lines
ax.axhline(0, color='black', linestyle='--', linewidth=1.2, alpha=0.5)
ax.axvline(0, color='black', linestyle='--', linewidth=1.2, alpha=0.5)

# Light grid (Plotly style)
ax.grid(True, color='#e0e0e0', linewidth=0.5, alpha=0.7)
ax.set_axisbelow(True)

# Colorbar with label ABOVE (like Fig 2)
cbar = plt.colorbar(scatter, ax=ax, pad=0.02, aspect=25, shrink=0.5)
cbar.ax.tick_params(labelsize=11)
cbar.set_ticks([0, 0.5, 1])
cbar.set_ticklabels(['Worst', 'Middle', 'Best'])

# Add title above colorbar
cbar.ax.text(0.5, 1.08, 'League\nStanding',
               transform=cbar.ax.transAxes,
               fontsize=12, ha='center', va='bottom', weight='bold')

# Set symmetric limits
ax.set_xlim(-x_range, x_range)
ax.set_ylim(-y_range, y_range)

# Quadrant annotations (Fig 2 style: colored borders, larger padding)
label_offset_x = x_range * 0.75
label_offset_y = y_range * 0.75

quadrant_labels = [
      (label_offset_x, label_offset_y,
       "Dominant teams\n(Depth + Goaltending)", col_blue_dark, 'center', 'center'),
      (-label_offset_x, label_offset_y,
       "Goalie-dependent\n(Top-heavy)", col_oil_orange, 'center', 'center'),
      (label_offset_x, -label_offset_y,
       "Depth-driven\n(Balanced roster)", '#2a9d8f', 'center', 'center'),
      (-label_offset_x, -label_offset_y,
       "Struggling\n(Both disadvantages)", col_gray, 'center', 'center'),
  ]

for x, y, text, color, ha_val, va_val in quadrant_labels:
      ax.text(x, y, text,
              fontsize=13, weight='bold', style='italic',
              ha=ha_val, va=va_val, color=color, alpha=0.65,
              bbox=dict(boxstyle='round,pad=0.6', facecolor='white',
                       edgecolor=color, linewidth=2.5, alpha=0.9))

# Styling
sns.despine()
ax.set_xlabel('Average Depth Advantage (Team − Opponent)',
                fontsize=16, weight='bold')
ax.set_ylabel('Average Goalie Advantage (Team − Opponent GSAx)',
                fontsize=16, weight='bold')
ax.tick_params(axis='both', labelsize=13)

# Title (Fig 2 style spacing and sizing)
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.88)

fig.suptitle(
      f'Team Identity: Depth vs Goaltending ({current_season[:4]}-{str(int(current_season[:4])+1)[-2:]} Season)',
      fontsize=22,
      weight='bold',
      x=left_x,
      ha='left',
      y=0.96
  )

fig.text(
      left_x,
      0.90,
      'Point color shows current league standing | Each team\'s average profile across all games',
      fontsize=14,
      ha='left'
  )

# Caption (Fig 2 style)
fig.text(
      0.9,
      0.01,
      'Data: 2024-25 season through January 2025 | Standings from NHL API (current)',
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure('figure_3_team_identity_2425.png')
plt.show()

print("\n" + "="*80)
print("TEAM IDENTITY DATA (2024-25 SEASON)")
print("="*80)

# Sort by league standing (best to worst)
team_data_sorted = team_identity.sort_values('league_rank')

print("\nAll teams (sorted by league standing):")
print(team_data_sorted[['team', 'league_rank', 'avg_depth_adv', 'avg_gsax_adv', 'win_pct']].to_string(index=False))

# Identify quadrants
team_identity['quadrant'] = 'Unknown'
team_identity.loc[
      (team_identity['avg_depth_adv'] > 0) & (team_identity['avg_gsax_adv'] > 0),
      'quadrant'
  ] = 'Dominant'
team_identity.loc[
      (team_identity['avg_depth_adv'] < 0) & (team_identity['avg_gsax_adv'] > 0),
      'quadrant'
  ] = 'Goalie-Dependent'
team_identity.loc[
      (team_identity['avg_depth_adv'] > 0) & (team_identity['avg_gsax_adv'] < 0),
      'quadrant'
  ] = 'Depth-Driven'
team_identity.loc[
      (team_identity['avg_depth_adv'] < 0) & (team_identity['avg_gsax_adv'] < 0),
      'quadrant'
  ] = 'Struggling'

print("\n" + "="*80)
print("QUADRANT BREAKDOWN")
print("="*80)

for quad in ['Dominant', 'Goalie-Dependent', 'Depth-Driven', 'Struggling']:
      quad_teams = team_identity[team_identity['quadrant'] == quad].sort_values('league_rank')
      print(f"\n{quad.upper()} ({len(quad_teams)} teams):")
      print(f"Average league rank: {quad_teams['league_rank'].mean():.1f}")
      print(f"Average win%: {quad_teams['win_pct'].mean():.3f}")
      print("Teams:")
      for _, row in quad_teams.iterrows():
          print(f"  {row['team']:4s} - Rank {row['league_rank']:2.0f} - Depth {row['avg_depth_adv']:+.3f} - GSAx {row['avg_gsax_adv']:+.3f} - Win% {row['win_pct']:.3f}")

# Correlation between standing and position
from scipy.stats import pearsonr

r_depth, p_depth = pearsonr(team_identity['league_rank'], team_identity['avg_depth_adv'])
r_gsax, p_gsax = pearsonr(team_identity['league_rank'], team_identity['avg_gsax_adv'])

print("\n" + "="*80)
print("CORRELATIONS WITH LEAGUE STANDING")
print("="*80)
print(f"Depth advantage vs Standing: r = {r_depth:.3f}, p = {p_depth:.4f}")
print(f"GSAx advantage vs Standing: r = {r_gsax:.3f}, p = {p_gsax:.4f}")
print("(Negative r = better standing correlates with higher advantage)")

print("="*80)
  
# ==============================================================================
# FIGURE 4: STRATEGY SUCCESS RATES
# ==============================================================================

print("\nGenerating Figure 4: Strategy Success Rates...")

# Categorize strategies
team_identity['strategy'] = 'Balanced'
team_identity.loc[
      (team_identity['avg_depth_adv'] > 0.05) & (team_identity['avg_gsax_adv'] > 0.2),
      'strategy'
  ] = 'Elite (Both)'
team_identity.loc[
      (team_identity['avg_depth_adv'] > 0.05) & (team_identity['avg_gsax_adv'] <= 0.2),
      'strategy'
  ] = 'Depth-Driven'
team_identity.loc[
      (team_identity['avg_depth_adv'] <= 0.05) & (team_identity['avg_gsax_adv'] > 0.2),
      'strategy'
  ] = 'Goalie-Dependent'
team_identity.loc[
      (team_identity['avg_depth_adv'] < -0.05) & (team_identity['avg_gsax_adv'] < -0.2),
      'strategy'
  ] = 'Struggling'

# Calculate strategy win rates
strategy_summary = team_identity.groupby('strategy').agg({
      'win_pct': ['mean', 'std', 'count']
  }).reset_index()
strategy_summary.columns = ['strategy', 'mean_win_pct', 'sd_win_pct', 'n_teams']
strategy_summary['se_win_pct'] = strategy_summary['sd_win_pct'] / np.sqrt(strategy_summary['n_teams'])

# Sort by win%
strategy_summary = strategy_summary.sort_values('mean_win_pct', ascending=True)

# Create figure
fig, ax = plt.subplots(figsize=(12, 7))

# Color mapping
strategy_colors_map = {
      'Goalie-Dependent': col_oil_orange,
      'Elite (Both)': col_blue_dark,
      'Depth-Driven': '#2a9d8f',
      'Balanced': col_gray,
      'Struggling': '#9d0208'
  }

colors_list = [strategy_colors_map.get(s, col_gray) for s in strategy_summary['strategy']]

# Horizontal bar chart
bars = ax.barh(range(len(strategy_summary)), strategy_summary['mean_win_pct'],
                 color=colors_list, alpha=0.85, edgecolor=col_blue_dark, linewidth=1.5)

# Error bars
ax.errorbar(strategy_summary['mean_win_pct'], range(len(strategy_summary)),
              xerr=strategy_summary['se_win_pct'],
              fmt='none', color='black', capsize=5, linewidth=2, alpha=0.7)

# Add value labels
for i, (idx, row) in enumerate(strategy_summary.iterrows()):
      ax.text(row['mean_win_pct'] + row['se_win_pct'] + 0.015, i, f"{row['mean_win_pct']:.1%}",
              va='center', ha='left', fontsize=13, weight='bold')

# Reference line at 50%
ax.axvline(0.5, color='black', linestyle='--', linewidth=1, alpha=0.3)

# Styling
sns.despine()
ax.grid(False)
ax.set_yticks(range(len(strategy_summary)))
ax.set_yticklabels(strategy_summary['strategy'], fontsize=13)
ax.set_xlabel('Win Percentage', fontsize=16, weight='bold')
ax.set_xlim(0.3, 0.65)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{int(y*100)}%'))
ax.tick_params(axis='x', labelsize=12)

# Title
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

fig.suptitle(
      'The Surprise: Goalie-Dependent Teams Are Winning More',
      fontsize=20,
      weight='bold',
      x=left_x,
      ha='left',
      y=0.97
  )

fig.text(
      left_x,
      0.87,
      'Average win % by strategic profile—elite goaltending outperforms balanced depth in 2024-25',
      fontsize=14,
      ha='left'
  )

fig.text(
      0.9,
      0.01,
      'Data: 32 NHL teams, 2024-25 season | Error bars show standard error',
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure('figure_4_strategy_success.png')
plt.show()

# ==============================================================================
# FIGURE 4B: STRATEGY SUCCESS RATES (GAME-LEVEL DATA)
# ==============================================================================

print("\nGenerating Figure 4B: Win Rates by Team Identity (Corrected)...")

# Drop 'strategy' column from team_games_df if it exists (from previous run)
if 'strategy' in team_games_df.columns:
      team_games_df = team_games_df.drop(columns=['strategy'])

# Now merge team's overall strategy back to their individual games
team_games_with_identity = team_games_df.merge(
      team_identity[['team', 'strategy']],
      on='team',
      how='left'
  )

# Calculate win rate for each team identity
strategy_game_summary = team_games_with_identity.groupby('strategy').agg({
      'won': ['sum', 'count', 'mean']
  }).reset_index()

strategy_game_summary.columns = ['strategy', 'wins', 'games', 'win_pct']

# Calculate standard error
strategy_game_summary['se_win_pct'] = np.sqrt(
      (strategy_game_summary['win_pct'] * (1 - strategy_game_summary['win_pct'])) /
      strategy_game_summary['games']
  )

# Sort by win%
strategy_game_summary = strategy_game_summary.sort_values('win_pct', ascending=True)

# Create figure
fig, ax = plt.subplots(figsize=(12, 7))

# Color mapping
strategy_colors_map = {
      'Goalie-Dependent': col_oil_orange,
      'Elite (Both)': col_blue_dark,
      'Depth-Driven': '#2a9d8f',
      'Balanced': col_gray,
      'Struggling (Both)': '#9d0208'
  }

colors_list = [strategy_colors_map.get(s, col_gray) for s in strategy_game_summary['strategy']]

# Horizontal bar chart
bars = ax.barh(range(len(strategy_game_summary)), strategy_game_summary['win_pct'],
                 color=colors_list, alpha=0.85, edgecolor=col_blue_dark, linewidth=1.5)

# Error bars
ax.errorbar(strategy_game_summary['win_pct'], range(len(strategy_game_summary)),
              xerr=strategy_game_summary['se_win_pct'],
              fmt='none', color='black', capsize=5, linewidth=2, alpha=0.7)

# Add value labels - positioned after error bars
for i, (idx, row) in enumerate(strategy_game_summary.iterrows()):
      # Add win% label
      ax.text(row['win_pct'] + row['se_win_pct'] + 0.015, i,
              f"{row['win_pct']:.1%}",
              va='center', ha='left', fontsize=13, weight='bold')

# Reference line at 50%
ax.axvline(0.5, color='black', linestyle='--', linewidth=1, alpha=0.3)

# Styling
sns.despine()
ax.grid(False)
ax.set_yticks(range(len(strategy_game_summary)))
ax.set_yticklabels(strategy_game_summary['strategy'], fontsize=13)
ax.set_xlabel('Win Percentage', fontsize=16, weight='bold')
ax.set_xlim(0.3, 0.7)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{int(y*100)}%'))
ax.tick_params(axis='x', labelsize=12)

# Title
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

fig.suptitle(
      'Game-Level Win Rates by Strategic Profile',
      fontsize=20,
      weight='bold',
      x=left_x,
      ha='left',
      y=0.97
  )

fig.text(
      left_x,
      0.87,
      'Win % for each advantage profile',
      fontsize=14,
      ha='left'
  )

fig.text(
      0.9,
      0.01,
      f'Data: {len(team_games_df):,} team-games from 2024-25 season | Error bars show standard error',
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure('figure_4b_strategy_success_game_level.png')
plt.show()

# Print comparison
print("\n" + "="*80)
print("COMPARISON: TEAM-LEVEL vs GAME-LEVEL WIN RATES")
print("="*80)
print("\nGame-Level (each game counted individually):")
print(strategy_game_summary[['strategy', 'win_pct', 'games']].to_string(index=False))

# ==============================================================================
# FIGURE 4C: STRATEGY SUCCESS RATES (ALL SEASONS 2010-2025)
# ==============================================================================

print("\nGenerating Figure 4: Strategy Success Rates (All Seasons)...")

# Create team-game long format for ALL SEASONS
team_games_all = []
for _, row in matchup_data.iterrows():
      # Home team
      team_games_all.append({
          'season': row['season'],
          'team': row['teamAbbrev_home'],
          'depth_adv': row['tdi_factor_home'] - row['tdi_factor_away'],
          'gsax_adv': row['gsax_home'] - row['gsax_away'],
          'won': (row['home_goals'] > row['away_goals'])
      })
      # Away team
      team_games_all.append({
          'season': row['season'],
          'team': row['teamAbbrev_away'],
          'depth_adv': row['tdi_factor_away'] - row['tdi_factor_home'],
          'gsax_adv': row['gsax_away'] - row['gsax_home'],
          'won': (row['away_goals'] > row['home_goals'])
      })

team_games_all_df = pd.DataFrame(team_games_all)

# Calculate season-team identity (one row per team per season)
team_season_identity = team_games_all_df.groupby(['season', 'team']).agg({
      'depth_adv': 'mean',
      'gsax_adv': 'mean',
      'won': ['sum', 'count']
  }).reset_index()
team_season_identity.columns = ['season', 'team', 'avg_depth_adv', 'avg_gsax_adv', 'wins', 'games']
team_season_identity['win_pct'] = team_season_identity['wins'] / team_season_identity['games']

# Categorize strategies (same thresholds)
team_season_identity['strategy'] = 'Balanced'
team_season_identity.loc[
      (team_season_identity['avg_depth_adv'] > 0.05) & (team_season_identity['avg_gsax_adv'] > 0.2),
      'strategy'
  ] = 'Elite (Both)'
team_season_identity.loc[
      (team_season_identity['avg_depth_adv'] > 0.05) & (team_season_identity['avg_gsax_adv'] <= 0.2),
      'strategy'
  ] = 'Depth-Driven'
team_season_identity.loc[
      (team_season_identity['avg_depth_adv'] <= 0.05) & (team_season_identity['avg_gsax_adv'] > 0.2),
      'strategy'
  ] = 'Goalie-Dependent'
team_season_identity.loc[
      (team_season_identity['avg_depth_adv'] < -0.05) & (team_season_identity['avg_gsax_adv'] < -0.2),
      'strategy'
  ] = 'Struggling'

# Calculate strategy win rates across all season-teams
strategy_summary = team_season_identity.groupby('strategy').agg({
      'win_pct': ['mean', 'std', 'count']
  }).reset_index()
strategy_summary.columns = ['strategy', 'mean_win_pct', 'sd_win_pct', 'n_season_teams']
strategy_summary['se_win_pct'] = strategy_summary['sd_win_pct'] / np.sqrt(strategy_summary['n_season_teams'])

# Sort by win%
strategy_summary = strategy_summary.sort_values('mean_win_pct', ascending=True)

print(f"\n✅ Analyzed {len(team_season_identity):,} season-team observations")
print(f"   Across {team_season_identity['season'].nunique()} seasons")
print(f"\nStrategy distribution:")
print(team_season_identity['strategy'].value_counts())

# Create figure
fig, ax = plt.subplots(figsize=(12, 7))

# Color mapping
strategy_colors_map = {
      'Goalie-Dependent': col_oil_orange,
      'Elite (Both)': col_blue_dark,
      'Depth-Driven': '#2a9d8f',
      'Balanced': col_gray,
      'Struggling': '#9d0208'
  }

colors_list = [strategy_colors_map.get(s, col_gray) for s in strategy_summary['strategy']]

# Horizontal bar chart
bars = ax.barh(range(len(strategy_summary)), strategy_summary['mean_win_pct'],
                 color=colors_list, alpha=0.85, edgecolor=col_blue_dark, linewidth=1.5)

# Error bars
ax.errorbar(strategy_summary['mean_win_pct'], range(len(strategy_summary)),
              xerr=strategy_summary['se_win_pct'],
              fmt='none', color='black', capsize=5, linewidth=2, alpha=0.7)

# Add value labels - positioned after error bars
for i, (idx, row) in enumerate(strategy_summary.iterrows()):
      # Win% label
      ax.text(row['mean_win_pct'] + row['se_win_pct'] + 0.015, i,
              f"{row['mean_win_pct']:.1%}",
              va='center', ha='left', fontsize=13, weight='bold')

      # N season-teams as smaller text
      ax.text(0.32, i, f"(n={int(row['n_season_teams'])})",
              va='center', ha='left', fontsize=10, style='italic', alpha=0.6, color="white")

# Reference line at 50%
ax.axvline(0.5, color='black', linestyle='--', linewidth=1, alpha=0.3)

# Styling
sns.despine()
ax.grid(False)
ax.set_yticks(range(len(strategy_summary)))
ax.set_yticklabels(strategy_summary['strategy'], fontsize=13)
ax.set_xlabel('Win Percentage', fontsize=16, weight='bold')
ax.set_xlim(0.3, 0.65)
ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{int(y*100)}%'))
ax.tick_params(axis='x', labelsize=12)

# Title
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

fig.suptitle(
      'More Than the Sum: Depth and Goaltending Compound',
      fontsize=20,
      weight='bold',
      x=left_x,
      ha='left',
      y=0.97
  )

fig.text(
      left_x,
      0.87,
      'Average win % by strategic profile across 15 seasons',
      fontsize=14,
      ha='left'
  )

fig.text(
      0.9,
      0.01,
      f'Data: {len(team_season_identity):,} season-team observations (2010-2025) | Error bars show standard error',
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure('figure_4c_strategy_success_all_seasons.png')
plt.show()

# Print summary stats
print("\n" + "="*80)
print("STRATEGY SUCCESS RATES (2010-2025)")
print("="*80)
for _, row in strategy_summary.sort_values('mean_win_pct', ascending=False).iterrows():
      print(f"{row['strategy']:20s}: {row['mean_win_pct']:.1%} ± {row['se_win_pct']:.1%} (n={int(row['n_season_teams'])} season-teams)")

# ==============================================================================
# FIGURE 5: BINNED TRADEOFF CURVE
# ==============================================================================

print("\nGenerating Figure 5: Binned Tradeoff Curve...")

# Create depth bins
matchup_data['depth_bin'] = pd.cut(
      matchup_data['depth_diff'],
      bins=np.arange(-3, 3.25, 0.25)
  )

# Calculate mean GSAx for each bin
binned_stats = matchup_data.groupby('depth_bin', observed=True)['gsax_diff'].agg([
      'mean', 'std', 'count'
  ]).reset_index()
binned_stats['se'] = binned_stats['std'] / np.sqrt(binned_stats['count'])
binned_stats = binned_stats.dropna()

# Create figure
fig, ax = plt.subplots(figsize=(12, 7))

x_pos = np.arange(len(binned_stats))

# Line with error bars
ax.errorbar(x_pos, binned_stats['mean'], yerr=binned_stats['se'],
              fmt='o-', color=col_blue_dark, linewidth=3, markersize=9,
              capsize=5, capthick=2, label='Mean ± SE', alpha=0.9)

# Fill between
ax.fill_between(x_pos,
                  binned_stats['mean'] - binned_stats['se'],
                  binned_stats['mean'] + binned_stats['se'],
                  alpha=0.2, color=col_blue_pale)

# Reference line
ax.axhline(0, color=col_oil_orange, linestyle='--', linewidth=1.5, alpha=0.6)
ax.axvline(12, color=col_oil_orange, linestyle='--', linewidth=1.5, alpha=0.6)

# Styling
sns.despine()
ax.grid(axis='y', alpha=0.3, linestyle=':', linewidth=0.8)
ax.set_xticks(x_pos[::2])  # Show every other label
ax.set_xticklabels([f"{b.left:.2f}" for b in binned_stats['depth_bin'].iloc[::2]],
                     rotation=0, ha='center', fontsize=10)
ax.set_xlabel('Depth Advantage Bin (Winner − Loser)', fontsize=16)
ax.set_ylabel('Mean GSAx Differential Required', fontsize=16)
ax.tick_params(axis='y', labelsize=13)
ax.legend(fontsize=12, loc='upper right', frameon=True)

# Title
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85, bottom=0.15)

fig.suptitle(
      'The Depth-Goaltending Tradeoff Is Linear',
      fontsize=20,
      weight='bold',
      x=left_x,
      ha='left',
      y=0.97
  )

fig.text(
      left_x,
      0.87,
      'For every 1-point depth advantage, teams need ~0.2 fewer goals of goaltending performance',
      fontsize=14,
      ha='left'
  )

fig.text(
      0.9,
      0.01,
      'Data: Mean GSAx by depth quartile (0.25-unit bins) | No evidence of thresholds or non-linearity',
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure('figure_5_binned_tradeoff.png')
plt.show()

# After creating matchup_data, before Figure 5
print("\n" + "="*60)
print("DEPTH DIFFERENTIAL DISTRIBUTION")
print("="*60)
print(f"Min: {matchup_data['depth_diff'].min():.3f}")
print(f"Max: {matchup_data['depth_diff'].max():.3f}")
print(f"1st percentile: {matchup_data['depth_diff'].quantile(0.01):.3f}")
print(f"99th percentile: {matchup_data['depth_diff'].quantile(0.99):.3f}")
print(f"5th percentile: {matchup_data['depth_diff'].quantile(0.05):.3f}")
print(f"95th percentile: {matchup_data['depth_diff'].quantile(0.95):.3f}")

# Count games outside current bins
outside = matchup_data[(matchup_data['depth_diff'] < -1.5) | (matchup_data['depth_diff'] > 1.5)]
print(f"\nGames outside [-1.5, 1.5]: {len(outside):,} ({len(outside)/len(matchup_data)*100:.1f}%)")

# Show distribution in bins
for threshold in [-3, -2, -1.5]:
      below = (matchup_data['depth_diff'] < threshold).sum()
      print(f"Games below {threshold}: {below:,} ({below/len(matchup_data)*100:.1f}%)")
for threshold in [1.5, 2, 3]:
      above = (matchup_data['depth_diff'] > threshold).sum()
      print(f"Games above {threshold}: {above:,} ({above/len(matchup_data)*100:.1f}%)")
print("="*60)

# After creating the binned_stats in Figure 5 section
print("\n" + "="*80)
print("BINNED TRADEOFF DATA")
print("="*80)

# Show the binned statistics
print("\nBin-level statistics (depth bin → mean GSAx required):")
print(binned_stats[['depth_bin', 'mean', 'se', 'count']].to_string(index=False))

# Linear regression to quantify the slope
from scipy.stats import linregress

# Get numeric bin centers for regression
bin_centers = binned_stats['depth_bin'].apply(lambda x: x.mid)
slope, intercept, r_value, p_value, std_err = linregress(bin_centers, binned_stats['mean'])

print("\n" + "="*80)
print("LINEAR REGRESSION STATISTICS")
print("="*80)
print(f"Slope: {slope:.4f}")
print(f"  (Interpretation: For every 1-point depth advantage, GSAx required changes by {slope:.3f} goals)")
print(f"Intercept: {intercept:.4f}")
print(f"R-squared: {r_value**2:.4f}")
print(f"P-value: {p_value:.6f}")
print(f"Standard error of slope: {std_err:.4f}")

# Check for non-linearity by comparing first/last third slopes
n_bins = len(binned_stats)
third = n_bins // 3

# First third
early_centers = bin_centers[:third]
early_means = binned_stats['mean'][:third]
slope_early, _, r_early, _, _ = linregress(early_centers, early_means)

# Last third
late_centers = bin_centers[-third:]
late_means = binned_stats['mean'][-third:]
slope_late, _, r_late, _, _ = linregress(late_centers, late_means)

print("\n" + "="*80)
print("CHECKING FOR NON-LINEARITY")
print("="*80)
print(f"Slope in first third of range: {slope_early:.4f} (R² = {r_early**2:.4f})")
print(f"Slope in last third of range: {slope_late:.4f} (R² = {r_late**2:.4f})")
print(f"Difference: {abs(slope_early - slope_late):.4f}")
if abs(slope_early - slope_late) < 0.05:
      print("  → Slopes are similar. No evidence of non-linearity.")
else:
      print("  → Slopes differ. Some evidence of non-linearity or thresholds.")

print("="*80)
  
# ==============================================================================
# SUMMARY STATISTICS
# ==============================================================================

print("\n" + "="*80)
print("ANALYSIS COMPLETE - SUMMARY STATISTICS")
print("="*80)

# Overall correlation
r, p = pearsonr(matchup_data['depth_diff'].dropna(),
                  matchup_data['gsax_diff'].dropna())
print(f"\nDepth-GSAx Correlation: r = {r:.4f}, p < 0.001")

# Win type differences
for wt in win_type_order:
      subset = matchup_data[matchup_data['win_type'] == wt]['gsax_diff']
      print(f"{wt}: Mean = {subset.mean():.3f}, SD = {subset.std():.3f}, N = {len(subset):,}")

# Strategy success
print("\nStrategy Win Rates (2024-25):")
for _, row in strategy_summary.sort_values('mean_win_pct', ascending=False).iterrows():
      print(f"  {row['strategy']}: {row['mean_win_pct']:.1%} ({int(row['n_teams'])} teams)")

print("\n✅ All figures generated successfully!")
print(f"   Saved to: {os.path.join(PROJECT_ROOT, 'static/images/deep-dives/depth-and-goaltending/')}")