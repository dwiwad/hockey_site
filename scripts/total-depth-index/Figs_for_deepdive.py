#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  9 08:05:25 2026

@author: dwiwad
"""

"""
igure 2: Distribution of Depth (TDI) Factor Scores
"""

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib as mpl
import os

# ---- Brand setup ----
mpl.rcParams['font.family'] = 'Charter'

PROJECT_ROOT = "/Users/dwiwad/dev/hockey_site"

def save_figure(filename):
    output_dir = os.path.join(PROJECT_ROOT, "static/images/deep-dives/total-depth-index")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    plt.savefig(output_path, dpi=300, transparent=True)
    print(f"✅ Saved: {output_path}")

# ---- Load data ----
data_path = os.path.join(PROJECT_ROOT, "data/total-depth-index/all_seasons/final_data_20102025.csv")
data = pd.read_csv(data_path)

# ---- Brand colors ----
col_blue_pale = '#3B4B64'
col_blue_dark = '#041E42'
col_oil_orange = '#FF4C00'
col_white = '#FFFFFF'

# ---- Figure 2: Distribution histogram ----
fig, ax = plt.subplots(figsize=(12, 7))

# Histogram with density
ax.hist(
    data['tdi_factor'].dropna(),
    bins=60,
    density=True,
    color=col_blue_pale,
    alpha=0.7,
    edgecolor='white',
    linewidth=0.3
)

# Density curve overlay
data['tdi_factor'].dropna().plot.kde(
    ax=ax,
    color=col_oil_orange,
    linewidth=3.5
)

# Clean aesthetic
sns.despine()
ax.grid(False)

# Axis labels
ax.set_xlabel("Depth (latent factor score)", fontsize=18)
ax.set_ylabel("Density", fontsize=18)
ax.set_xlim(-3.5, 3.5)
ax.tick_params(axis='both', labelsize=14)

# Calculate left margin for title alignment
left_x = ax.get_position().x0

# Reserve space for titles
plt.subplots_adjust(top=0.85)

# Main title
fig.suptitle(
    "Distribution of Depth (TDI) Factor Scores",
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
    "Team–game factor scores across all seasons (2010-2025)",
    fontsize=14,
    ha='left'
)

# Data source note
fig.text(
    0.9,
    0.01,
    "Data: Latent factor scores from confirmatory factor analysis (n=60 bins)",
    fontsize=10,
    style='italic',
    ha='right'
)

save_figure("figure_2_depth_distribution.png")
plt.show()


# ---- Calculate lag-1 autocorrelation by team-season ----
ac1_by_ts = []

for (team, season), group in data.groupby(['teamAbbrev', 'season']):
    group = group.sort_values('game_id').reset_index(drop=True)

    if len(group) >= 2:
        # Calculate correlation between tdi_factor and its lag
        tdi = group['tdi_factor'].values
        tdi_lag = pd.Series(tdi).shift(1).values

        # Compute correlation, ignoring NaN
        mask = ~(pd.isna(tdi) | pd.isna(tdi_lag))
        if mask.sum() >= 2:
            ac1 = pd.Series(tdi[mask]).corr(pd.Series(tdi_lag[mask]))
            ac1_by_ts.append({
                'teamAbbrev': team,
                'season': season,
                'n_games': len(group),
                'ac1': ac1
            })

ac1_df = pd.DataFrame(ac1_by_ts).dropna(subset=['ac1'])

# ---- Filter out ATL and UTA ----
ac1_df = ac1_df[~ac1_df['teamAbbrev'].isin(['ATL', 'UTA'])]

# ---- Order teams by median autocorrelation ----
team_order = (ac1_df.groupby('teamAbbrev')['ac1']
              .median()
              .sort_values()
              .index.tolist())

# ---- Figure 3: Violin plot with boxplot overlay ----
fig, ax = plt.subplots(figsize=(10, 5.5))

# Violin plot
parts = ax.violinplot(
    [ac1_df[ac1_df['teamAbbrev'] == team]['ac1'].values for team in team_order],
    positions=range(len(team_order)),
    widths=0.7,
    showmeans=False,
    showmedians=False,
    showextrema=False
)

# Style violin bodies
for pc in parts['bodies']:
      pc.set_facecolor(col_blue_pale)
      pc.set_alpha(0.85)
      pc.set_edgecolor(col_blue_dark)
      pc.set_linewidth(0.8)
      pc.set_alpha(0.7)

  # Boxplot overlay
bp = ax.boxplot(
      [ac1_df[ac1_df['teamAbbrev'] == team]['ac1'].values for team in team_order],
      positions=range(len(team_order)),
      widths=0.18,
      patch_artist=True,
      showfliers=False,
      medianprops=dict(color=col_blue_dark, linewidth=2),
      boxprops=dict(facecolor=col_white, edgecolor=col_blue_dark, linewidth=1.2),
      whiskerprops=dict(color=col_blue_dark, linewidth=1.2),
      capprops=dict(color=col_blue_dark, linewidth=1.2)
  )

  # Horizontal line at 0
ax.axhline(y=0, color=col_oil_orange, linewidth=1.4, linestyle='--', alpha=0.95)

  # Clean aesthetic
sns.despine()
ax.grid(False)

  # Axis labels and ticks
ax.set_xticks(range(len(team_order)))
ax.set_xticklabels(team_order, rotation=90, fontsize=10, va='top')
ax.set_xlabel("Team", fontsize=18)
ax.set_ylabel("Lag-1 autocorrelation of Depth", fontsize=18)
ax.tick_params(axis='y', labelsize=14)

  # Calculate left margin for title alignment
left_x = ax.get_position().x0

  # Reserve space for titles
plt.subplots_adjust(top=0.85, bottom=0.15)

  # Main title
fig.suptitle(
      "Short-Term Stability of Depth by Team",
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
      "Lag-1 autocorrelation within team-seasons (2010-2025)",
      fontsize=14,
      ha='left'
  )

  # Data source note
fig.text(
      0.9,
      0.01,
      "Data: Correlation between consecutive games, aggregated by team across seasons",
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure("figure_3_ac1_by_team.png")
plt.show()

# ---- MoneyPuck data ----

  # ---- Brand colors ----
col_depth = '#3B4B64'      # Depth model
col_moneypuck = '#6EB4B8'  # MoneyPuck
col_baseline = '#9A9A9A'   # Baseline
col_orange = '#E76F2B'     # Reference lines
  
  # ---- CV results (you'll need to load or create this from your data) ----
  # This is placeholder - replace with actual cv_results_metrics from your analysis
  # ---- CV results (actual data from analysis) ----
cv_results = pd.DataFrame({
      'season': ['20102011', '20112012', '20122013', '20132014', '20142015',
                 '20152016', '20162017', '20172018', '20182019', '20192020',
                 '20202021', '20212022', '20222023', '20232024', '20242025'],
      'accuracy_model': [0.552, 0.563, 0.554, 0.545, 0.545,
                         0.532, 0.569, 0.570, 0.537, 0.543,
                         0.538, 0.594, 0.568, 0.577, 0.588],
      'accuracy_baseline': [0.520, 0.552, 0.581, 0.541, 0.544,
                            0.528, 0.558, 0.558, 0.535, 0.525,
                            0.535, 0.541, 0.520, 0.537, 0.565],
      'logloss': [0.686, 0.683, 0.684, 0.684, 0.687,
                  0.688, 0.681, 0.679, 0.686, 0.689,
                  0.684, 0.669, 0.683, 0.673, 0.675],
      'logloss_baseline': [0.692, 0.688, 0.680, 0.690, 0.689,
                           0.692, 0.686, 0.686, 0.691, 0.692,
                           0.691, 0.690, 0.692, 0.690, 0.685]
  })

  # ---- MoneyPuck data (only 2020-2025) ----
moneypuck = pd.DataFrame({
      'season': ['20202021', '20212022', '20222023', '20232024', '20242025'],
      'acc_mp': [0.601, 0.641, 0.606, 0.611, 0.604],
      'logloss_mp': [0.660, 0.648, 0.656, 0.661, 0.658]
  })

  # ---- Create figure with 2 stacked subplots ----
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9), sharex=True)

  # ==========================================
  # TOP PANEL: ACCURACY
  # ==========================================

  # Depth model
ax1.plot(cv_results['season'], cv_results['accuracy_model'],
         color=col_depth, linewidth=3.5, marker='o', markersize=8,
         label='Depth model (LOSO-CV)')

  # MoneyPuck
ax1.plot(moneypuck['season'], moneypuck['acc_mp'],
         color=col_moneypuck, linewidth=3.5, linestyle='dotted',
         marker='^', markersize=9, label='MoneyPuck pre-game model')

  # Baseline
ax1.plot(cv_results['season'], cv_results['accuracy_baseline'],
         color=col_baseline, linewidth=3, linestyle='--',
         marker='s', markersize=7, label='Baseline (home win rate)')

  # Random 50% reference
ax1.axhline(y=0.5, color=col_orange, linewidth=1.4, linestyle='--', alpha=0.7)
ax1.text(1, 0.503, 'Random baseline (50%)',
         color=col_orange, fontsize=11, style='italic', va='bottom')

  # Styling
sns.despine(ax=ax1)
ax1.grid(False)
ax1.set_ylabel("Accuracy", fontsize=18)
ax1.tick_params(axis='y', labelsize=14)
ax1.set_ylim(0.50, 0.66)

  # Format y-axis as percentages
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{int(y*100)}%'))

  # ==========================================
  # BOTTOM PANEL: LOG LOSS
  # ==========================================

  # Depth model
ax2.plot(cv_results['season'], cv_results['logloss'],
         color=col_depth, linewidth=3.5, marker='o', markersize=8,
           label='Depth model (LOSO-CV)')

  # MoneyPuck
ax2.plot(moneypuck['season'], moneypuck['logloss_mp'],
           color=col_moneypuck, linewidth=3.5, linestyle='dotted',
           marker='^', markersize=9, label='MoneyPuck pre-game model')

  # Baseline
ax2.plot(cv_results['season'], cv_results['logloss_baseline'],
           color=col_baseline, linewidth=3, linestyle='--',
           marker='s', markersize=7, label='Baseline (home win rate)')

  # Random 0.693 reference
ax2.axhline(y=0.693, color=col_orange, linewidth=1.4, linestyle='--', alpha=0.7)
ax2.text(1, 0.6935, 'Random baseline (0.693)',
           color=col_orange, fontsize=11, style='italic', va='bottom')

  # Styling
sns.despine(ax=ax2)
ax2.grid(False)
ax2.set_xlabel("Season", fontsize=18)
ax2.set_ylabel("Log Loss", fontsize=18)
ax2.tick_params(axis='both', labelsize=14)
ax2.set_ylim(0.645, 0.70)

  # X-axis labels rotated
ax2.set_xticks(range(len(cv_results['season'])))
ax2.set_xticklabels(cv_results['season'], rotation=45, ha='right')

  # ==========================================
  # TITLES AND LEGEND
  # ==========================================

  # Calculate left margin for title alignment
left_x = ax1.get_position().x0

  # Reserve space for titles
plt.subplots_adjust(top=0.92, bottom=0.12, hspace=0.15)

  # Main title
fig.suptitle(
      "Predictive Accuracy and Log Loss by Season",
      fontsize=20,
      weight='bold',
      x=left_x,
      ha='left',
      y=0.97
  )

  # Subtitle
fig.text(
      left_x,
      0.92,
      "Depth model vs MoneyPuck vs seasonal baseline (LOSO-CV for depth model)",
      fontsize=14,
      ha='left'
  )

  # Shared legend at bottom
handles, labels = ax1.get_legend_handles_labels()
fig.legend(handles, labels, loc='center', ncol=3,
             frameon=False, fontsize=14, bbox_to_anchor=(0.5, 0.48))

  # Data source note
fig.text(
      0.9,
      0.01,
      "Data: Leave-one-season-out cross-validation (2020-2025 seasons)",
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure("figure_accuracy_logloss.png")
plt.show()



# ---- Figure 4: Rolling 10-game Depth → next-game Depth ----

  # Calculate rolling 10-game average and next game depth
data_roll = data.sort_values(['teamAbbrev', 'game_id']).copy()

  # Group by team and calculate rolling mean (lag it so we don't use current game)
data_roll['depth_roll10'] = (data_roll.groupby('teamAbbrev')['tdi_factor']
                                .transform(lambda x: x.shift(1).rolling(10, min_periods=10).mean()))

  # Next game depth
data_roll['depth_next'] = data_roll.groupby('teamAbbrev')['tdi_factor'].shift(-1)

  # Filter to valid rows
df_model = data_roll.dropna(subset=['depth_roll10', 'depth_next'])

  # ---- Create figure ----
fig, ax = plt.subplots(figsize=(12, 7))

  # Scatter plot (faded dots)
ax.scatter(
      df_model['depth_roll10'],
      df_model['depth_next'],
      alpha=0.18,
      s=30,
      color=col_blue_pale,
      edgecolor='none'
  )

  # Linear regression line with confidence interval
sns.regplot(
      data=df_model,
      x='depth_roll10',
      y='depth_next',
      scatter=False,
      ax=ax,
      color=col_oil_orange,
      line_kws={'linewidth': 3.5},
      ci=95
  )

  # Clean aesthetic
sns.despine()
ax.grid(False)

  # Axis labels
ax.set_xlabel("Depth (10-game rolling mean, t−1)", fontsize=18)
ax.set_ylabel("Depth (t)", fontsize=18)
ax.tick_params(axis='both', labelsize=14)

  # Calculate left margin for title alignment
left_x = ax.get_position().x0

  # Reserve space for titles
plt.subplots_adjust(top=0.85)

  # Main title
fig.suptitle(
      "Rolling Ten-Game Average Depth Predicts Next-Game Depth",
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
      "Recent performance trends are moderately predictive of immediate future depth",
      fontsize=14,
      ha='left'
  )

  # Data source note
fig.text(
      0.9,
      0.01,
      "Data: 10-game rolling average (lagged) vs next-game depth across all team-seasons",
      fontsize=10,
      style='italic',
      ha='right'
  )

save_figure("figure_4_rolling_depth_prediction.png")
plt.show()