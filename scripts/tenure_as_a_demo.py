import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt

  # =============================================================================
  # LOAD DATA
  # =============================================================================
games_meta = pd.read_csv(
      's3://hockey-decoded/static-ds-analyses/total-depth-index/all-seasons/all_games_meta_20102025.csv',
      storage_options={'anon': False},
      low_memory=False
  )

game_rosters = pd.read_csv(
      's3://hockey-decoded/static-ds-analyses/total-depth-index/all-seasons/all_rosters_20102025.csv',
      storage_options={'anon': False},
      low_memory=False
  )

player_demos = pd.read_csv(
      's3://hockey-decoded/static-ds-analyses/nhl-player-demographics/rosters.csv',
      storage_options={'anon': False}
  )

print(f"Games: {len(games_meta)}")
print(f"Game rosters: {len(game_rosters)}")
print(f"Player demographics: {len(player_demos)}")

# =============================================================================
# FILTER TO REGULAR SEASON ONLY
# =============================================================================
game_rosters['game_type'] = game_rosters['game_id'].astype(str).str[4:6]
print(f"\nGame types: {game_rosters['game_type'].value_counts().to_dict()}")

game_rosters = game_rosters[game_rosters['game_type'] == '02'].copy()
print(f"After filtering to regular season: {len(game_rosters)}")

# =============================================================================
# GET PLAYER DEMOGRAPHICS (height, weight, birthdate)
# =============================================================================
player_info = player_demos.sort_values('season').groupby('id').agg({
      'height_in': 'last',
      'weight_lb': 'last',
      'birth_date': 'first'
  }).reset_index()
player_info = player_info.rename(columns={'id': 'playerId'})

print(f"Unique players with demographics: {len(player_info)}")

# =============================================================================
# CALCULATE TENURE (years in NHL)
# =============================================================================
player_first_season = player_demos.groupby('id')['season'].min().reset_index()
player_first_season.columns = ['playerId', 'first_season']
player_first_season['first_year'] = player_first_season['first_season'].astype(str).str[:4].astype(int)

# Merge player info + first season into game rosters
game_rosters = game_rosters.merge(player_info, on='playerId', how='left')
game_rosters = game_rosters.merge(player_first_season[['playerId', 'first_year']], on='playerId', how='left')

# Calculate tenure
game_rosters['game_year'] = game_rosters['game_id'].astype(str).str[:4].astype(int)
game_rosters['nhl_tenure'] = game_rosters['game_year'] - game_rosters['first_year']

print(f"\nTenure range (before cleaning): {game_rosters['nhl_tenure'].min():.0f} to {game_rosters['nhl_tenure'].max():.0f}")
print(f"Negative tenure rows: {(game_rosters['nhl_tenure'] < 0).sum()}")

# Floor tenure at 0 (treat edge cases as rookies)
game_rosters['nhl_tenure'] = game_rosters['nhl_tenure'].clip(lower=0)
print(f"Tenure range (after cleaning): {game_rosters['nhl_tenure'].min():.0f} to {game_rosters['nhl_tenure'].max():.0f}")

# =============================================================================
# CALCULATE AGE AT GAME TIME
# =============================================================================
games_meta['game_date'] = pd.to_datetime(games_meta['startTimeUTC']).dt.date
game_rosters = game_rosters.merge(
      games_meta[['id', 'game_date']].rename(columns={'id': 'game_id'}),
      on='game_id',
      how='left'
  )

game_rosters['birth_date'] = pd.to_datetime(game_rosters['birth_date'])
game_rosters['game_date'] = pd.to_datetime(game_rosters['game_date'])
game_rosters['age'] = (game_rosters['game_date'] - game_rosters['birth_date']).dt.days / 365.25

# =============================================================================
# AGGREGATE TO TEAM-GAME LEVEL
# =============================================================================
team_game_stats = game_rosters.groupby(['game_id', 'teamAbbrev']).agg({
      'height_in': 'mean',
      'weight_lb': 'mean',
      'age': 'mean',
      'nhl_tenure': 'mean'
}).reset_index()

team_game_stats.columns = ['game_id', 'teamAbbrev', 'height', 'weight', 'age', 'tenure']
print(f"\nTeam-game combinations: {len(team_game_stats)}")

# =============================================================================
# BUILD OUTCOMES DATASET
# =============================================================================
outcomes = games_meta[['id', 'season', 'homeTeam.abbrev', 'awayTeam.abbrev',
                          'homeTeam.score', 'awayTeam.score']].copy()
outcomes = outcomes.rename(columns={'id': 'game_id'})

# Filter to regular season
outcomes = outcomes[outcomes['game_id'].astype(str).str[4:6] == '02']
print(f"Regular season games: {len(outcomes)}")

# Determine winner
outcomes['winner'] = np.where(
      outcomes['homeTeam.score'] > outcomes['awayTeam.score'],
      outcomes['homeTeam.abbrev'],
      outcomes['awayTeam.abbrev']
  )
outcomes['home_win'] = (outcomes['winner'] == outcomes['homeTeam.abbrev']).astype(int)

# Merge home team stats
outcomes = outcomes.merge(
      team_game_stats,
      left_on=['game_id', 'homeTeam.abbrev'],
      right_on=['game_id', 'teamAbbrev'],
      how='left'
  ).rename(columns={
      'height': 'home_height',
      'weight': 'home_weight',
      'age': 'home_age',
      'tenure': 'home_tenure'
  }).drop(columns=['teamAbbrev'])

# Merge away team stats
outcomes = outcomes.merge(
      team_game_stats,
      left_on=['game_id', 'awayTeam.abbrev'],
      right_on=['game_id', 'teamAbbrev'],
      how='left'
  ).rename(columns={
      'height': 'away_height',
      'weight': 'away_weight',
      'age': 'away_age',
      'tenure': 'away_tenure'
  }).drop(columns=['teamAbbrev'])

# Calculate advantages
outcomes['height_adv'] = outcomes['home_height'] - outcomes['away_height']
outcomes['weight_adv'] = outcomes['home_weight'] - outcomes['away_weight']
outcomes['age_adv'] = outcomes['home_age'] - outcomes['away_age']
outcomes['tenure_adv'] = outcomes['home_tenure'] - outcomes['away_tenure']

# Clean
outcomes_clean = outcomes.dropna(subset=['height_adv', 'weight_adv', 'age_adv', 'tenure_adv'])
print(f"Games with complete data: {len(outcomes_clean)}")

# =============================================================================
# REGRESSION: AGE + TENURE
# =============================================================================
X = outcomes_clean[['height_adv', 'weight_adv', 'age_adv', 'tenure_adv']]
X = sm.add_constant(X)
y = outcomes_clean['home_win']

model = sm.Logit(y, X).fit()
print("\n" + "="*60)
print("REGRESSION: Height, Weight, Age, Tenure")
print("="*60)
print(model.summary())

print("\nOdds Ratios:")
print(np.exp(model.params))

import matplotlib.pyplot as plt
import matplotlib as mpl
import matplotlib.patches as mpatches
import seaborn as sns

  # ---- Brand setup ----
mpl.rcParams['font.family'] = 'Charter'

  # Brand colors
col_blue_pale = '#3B4B64'
col_blue_dark = '#041E42'
col_oil_orange = '#FF4C00'
col_gray = '#9AA3AF'
col_white = '#FFFFFF'

  # Green for significant (you can keep this or use col_oil_orange)
col_significant = '#2ECC71'

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

  # =============================================================================
  # Panel 1: The coefficient bars (top left)
  # =============================================================================
ax1 = axes[0, 0]

categories = ['Height', 'Weight', 'Age', 'Experience']
coefficients = [0.0585, 0.0026, -0.0097, 0.0973]
colors = [col_gray, col_gray, col_gray, col_oil_orange]
significance = ['', '', '', '***']

bars = ax1.barh(categories, coefficients, color=colors, edgecolor=col_blue_dark, height=0.6, linewidth=1.2)
ax1.axvline(x=0, color='black', linestyle='--', linewidth=1, alpha=0.5)

for i, (bar, sig) in enumerate(zip(bars, significance)):
      width = bar.get_width()
      ax1.text(width + 0.01, bar.get_y() + bar.get_height()/2,
               sig, ha='left', va='center', fontsize=14, fontweight='bold', color=col_oil_orange)

ax1.set_xlabel('Effect on Winning (log odds)', fontsize=14)
ax1.set_xlim(-0.05, 0.15)
ax1.tick_params(axis='both', labelsize=12)
sns.despine(ax=ax1)
ax1.grid(False)

  # =============================================================================
  # Panel 2: Win rate by tenure advantage (top right)
  # =============================================================================
ax2 = axes[0, 1]

outcomes_clean['tenure_bin'] = pd.cut(outcomes_clean['tenure_adv'],
                                         bins=[-10, -2, -1, 0, 1, 2, 10],
                                         labels=['Much Less\nExp', 'Less\nExp', 'Equal',
                                                'More\nExp', 'Much More\nExp', 'Way More\nExp'])

win_by_tenure = outcomes_clean.groupby('tenure_bin', observed=True)['home_win'].agg(['mean', 'count'])
win_by_tenure = win_by_tenure[win_by_tenure['count'] > 100]

  # Use brand colors - gradient from orange (bad) to blue (good)
colors_tenure = [col_oil_orange, col_oil_orange, col_gray, col_blue_pale, col_blue_pale, col_blue_dark]
bars2 = ax2.bar(range(len(win_by_tenure)), win_by_tenure['mean'],
                  color=colors_tenure[:len(win_by_tenure)], edgecolor=col_blue_dark, linewidth=1.2)

ax2.axhline(y=0.5, color='black', linestyle='--', linewidth=1, alpha=0.5)
ax2.set_xticks(range(len(win_by_tenure)))
ax2.set_xticklabels(win_by_tenure.index, fontsize=10)
ax2.set_ylabel('Win Rate', fontsize=14)
ax2.set_ylim(0.4, 0.65)
ax2.tick_params(axis='both', labelsize=12)
sns.despine(ax=ax2)
ax2.grid(False)

  # Add percentage labels on bars
for i, (bar, rate) in enumerate(zip(bars2, win_by_tenure['mean'])):
      ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
               f'{rate:.1%}', ha='center', va='bottom', fontsize=10, fontweight='bold')

  # =============================================================================
  # Panel 3: Size scatter (bottom left)
  # =============================================================================
ax3 = axes[1, 0]

sample = outcomes_clean.sample(min(3000, len(outcomes_clean)), random_state=42)
winners = sample[sample['home_win'] == 1]
losers = sample[sample['home_win'] == 0]

ax3.scatter(losers['home_weight'], losers['home_height'],
              alpha=0.3, c=col_oil_orange, s=20, label='Lost')
ax3.scatter(winners['home_weight'], winners['home_height'],
              alpha=0.3, c=col_blue_pale, s=20, label='Won')

ax3.set_xlabel('Team Avg Weight (lbs)', fontsize=14)
ax3.set_ylabel('Team Avg Height (in)', fontsize=14)
ax3.tick_params(axis='both', labelsize=12)
ax3.legend(loc='lower right', frameon=True, fontsize=11)
sns.despine(ax=ax3)
ax3.grid(False)

  # =============================================================================
  # Panel 4: Key takeaway (bottom right)
  # =============================================================================
ax4 = axes[1, 1]
ax4.axis('off')

takeaway_text = """KEY FINDINGS (17,840 games)

  ❌ Being TALLER doesn't help
     (coef = 0.06, p = 0.07)

  ❌ Being HEAVIER doesn't help  
     (coef = 0.00, p = 0.50)

  ❌ Being OLDER doesn't help
     (coef = -0.01, p = 0.71)

  ✅ More NHL EXPERIENCE wins
     (coef = 0.10, p < 0.001)
     
  Each extra year of team avg
  tenure → +10% higher odds of winning"""

ax4.text(0.05, 0.95, takeaway_text, transform=ax4.transAxes, fontsize=13,
           verticalalignment='top', fontfamily='monospace',
           bbox=dict(boxstyle='round,pad=0.8', facecolor='#f8f8f8',
                     edgecolor=col_blue_dark, linewidth=2))

  # =============================================================================
  # Titles (deep dive style - left aligned)
  # =============================================================================
plt.subplots_adjust(top=0.88, hspace=0.35, wspace=0.25)

left_x = axes[0, 0].get_position().x0

fig.suptitle(
      "What Actually Wins in Modern Hockey?",
      fontsize=22,
      weight='bold',
      x=left_x,
      ha='left',
      y=0.96
  )

fig.text(
      left_x,
      0.90,
      "Experience matters more than size—NHL tenure predicts winning, physical attributes don't",
      fontsize=14,
      ha='left'
  )

fig.text(
      0.9,
      0.01,
      "Data: 17,840 NHL games (2010-2025) | Logistic regression controlling for home advantage",
      fontsize=10,
      style='italic',
      ha='right'
  )

plt.savefig('/Users/dwiwad/desktop/experience_wins.png', dpi=300, facecolor='white', bbox_inches='tight')
plt.show()



# Find players with negative tenure
negative_tenure = game_rosters[game_rosters['nhl_tenure'] < 0].copy()

print(f"Rows with negative tenure: {len(negative_tenure)}")
print(f"Unique players with negative tenure: {negative_tenure['playerId'].nunique()}")

  # Look at examples
examples = negative_tenure.groupby('playerId').agg({
      'game_id': 'count',
      'game_year': 'min',
      'first_year': 'first',
      'nhl_tenure': 'first',
      'teamAbbrev': 'first'
  }).reset_index()
examples.columns = ['playerId', 'games_played', 'first_game_year', 'first_roster_year', 'tenure', 'team']
examples = examples.sort_values('tenure')

print("\nWorst cases (most negative tenure):")
print(examples.head(20))

  # Check if these are mostly fringe players (few games)
print(f"\nGames played by negative-tenure players:")
print(examples['games_played'].describe())

# Cross-reference with player_demos to see who these players are
negative_players = negative_tenure['playerId'].unique()

player_check = player_demos[player_demos['id'].isin(negative_players)][
      ['id', 'first_name', 'last_name', 'season', 'team']
  ].sort_values(['id', 'season'])

print("\nSample negative-tenure players in demographics data:")
print(player_check.groupby('id').agg({
      'first_name': 'first',
      'last_name': 'first',
      'season': ['min', 'max', 'count']
  }).head(10))

  # Are these mostly AHL call-ups / fringe players?
  # Compare games played: negative tenure vs positive tenure
print("\nGames per player comparison:")
print("Negative tenure players avg games:",
        game_rosters[game_rosters['nhl_tenure'] < 0].groupby('playerId').size().mean())
print("Positive tenure players avg games:",
        game_rosters[game_rosters['nhl_tenure'] >= 0].groupby('playerId').size().mean())






# What position info is in the player demographics?
print(player_demos.columns.tolist())

  # Check for position column
if 'position' in player_demos.columns:
      print(player_demos['position'].value_counts())
elif 'primaryPosition' in player_demos.columns:
      print(player_demos['primaryPosition'].value_counts())

# Then check if position made it into your game_rosters:

print(game_rosters.columns.tolist())

# If position exists
if 'position' in game_rosters.columns:
      print(game_rosters['position'].value_counts())

#If position is there, here's the analysis path:

# Calculate position-specific team averages per game
position_stats = game_rosters.groupby(['game_id', 'teamId', 'positionCode']).agg({
      'height_in': 'mean',
      'weight_lb': 'mean'
  }).reset_index()

 # Remap position codes: C, L, R -> F (forward), D stays D, G stays G
position_stats['pos_group'] = position_stats['positionCode'].map({
      'C': 'F', 'L': 'F', 'R': 'F', 'D': 'D', 'G': 'G'
  })

  # Now aggregate again at the grouped position level
position_grouped = position_stats.groupby(['game_id', 'teamId', 'pos_group']).agg({
      'height_in': 'mean',
      'weight_lb': 'mean'
  }).reset_index()

print(position_grouped['pos_group'].value_counts())

  # Now pivot
position_wide = position_grouped.pivot_table(
      index=['game_id', 'teamId'],
      columns='pos_group',
      values=['height_in', 'weight_lb']
  ).reset_index()

  # Flatten column names
position_wide.columns = ['_'.join(col).strip('_') if col[1] else col[0] for col in position_wide.columns]
print(position_wide.columns.tolist())
print(position_wide.head())

  # Pivot to get columns like defense_height, forward_height, etc.
position_wide = position_stats.pivot_table(
      index=['game_id', 'teamId'],
      columns='positionCode',
      values=['height_in', 'weight_lb']
  ).reset_index()

  # Flatten column names
position_wide.columns = ['_'.join(col).strip('_') for col in position_wide.columns]
print(position_wide.head())

# =============================================================================
  # PART 1: MERGE POSITION DATA WITH GAME OUTCOMES
  # =============================================================================

  # Get the position-grouped version (F, D, G)
position_stats['pos_group'] = position_stats['positionCode'].map({
      'C': 'F', 'L': 'F', 'R': 'F', 'D': 'D', 'G': 'G'
  })

position_grouped = position_stats.groupby(['game_id', 'teamId', 'pos_group']).agg({
      'height_in': 'mean',
      'weight_lb': 'mean'
  }).reset_index()

position_wide = position_grouped.pivot_table(
      index=['game_id', 'teamId'],
      columns='pos_group',
      values=['height_in', 'weight_lb']
  ).reset_index()

position_wide.columns = ['_'.join(col).strip('_') if col[1] else col[0] for col in position_wide.columns]

  # Rename for clarity
position_wide = position_wide.rename(columns={
      'height_in_D': 'defense_height',
      'height_in_F': 'forward_height',
      'weight_lb_D': 'defense_weight',
      'weight_lb_F': 'forward_weight'
  })

  # Drop goalie columns (not relevant for skater analysis)
position_wide = position_wide.drop(columns=['height_in_G', 'weight_lb_G'], errors='ignore')

print(f"Position data: {len(position_wide)} team-games")
print(position_wide.head())

  # =============================================================================
  # PART 2: BUILD GAME-LEVEL DATASET WITH HOME/AWAY
  # =============================================================================

  # Get unique games with home/away team IDs from game_rosters
  # We need to identify which team is home vs away

  # First, let's get game metadata from all_games if you have it
  # Or we can infer from game_id patterns

  # Merge position data for home and away teams
  # We need the schedule data - let's load it
import pandas as pd

schedule = pd.read_csv('/Users/dwiwad/dev/hockey_site/data/total-depth-index/all_seasons/all_games_meta_20102025.csv')
schedule['game_id'] = schedule['id'].astype(int)

  # Get home and away team IDs
game_teams = schedule[['game_id', 'homeTeam.id', 'awayTeam.id',
                          'homeTeam.score', 'awayTeam.score']].copy()
game_teams.columns = ['game_id', 'home_team_id', 'away_team_id', 'home_goals', 'away_goals']
game_teams['home_win'] = (game_teams['home_goals'] > game_teams['away_goals']).astype(int)

print(f"Games with outcomes: {len(game_teams)}")
print(game_teams.head())

  # =============================================================================
  # PART 3: MERGE HOME AND AWAY POSITION STATS
  # =============================================================================

  # Merge home team position stats
pos_home = position_wide.merge(
      game_teams[['game_id', 'home_team_id', 'home_win']],
      left_on=['game_id', 'teamId'],
      right_on=['game_id', 'home_team_id'],
      how='inner'
  )
pos_home = pos_home.add_prefix('home_')
pos_home = pos_home.rename(columns={'home_game_id': 'game_id', 'home_home_win': 'home_win'})

  # Merge away team position stats
pos_away = position_wide.merge(
      game_teams[['game_id', 'away_team_id']],
      left_on=['game_id', 'teamId'],
      right_on=['game_id', 'away_team_id'],
      how='inner'
  )
pos_away = pos_away.add_prefix('away_')
pos_away = pos_away.rename(columns={'away_game_id': 'game_id'})

  # Combine home and away
pos_matchups = pos_home.merge(pos_away, on='game_id', how='inner')

print(f"Matchups with position data: {len(pos_matchups)}")
print(pos_matchups.columns.tolist())

  # =============================================================================
  # PART 4: CALCULATE POSITION-SPECIFIC ADVANTAGES
  # =============================================================================

  # Defense size advantages (home - away)
pos_matchups['defense_height_adv'] = pos_matchups['home_defense_height'] - pos_matchups['away_defense_height']
pos_matchups['defense_weight_adv'] = pos_matchups['home_defense_weight'] - pos_matchups['away_defense_weight']

  # Forward size advantages
pos_matchups['forward_height_adv'] = pos_matchups['home_forward_height'] - pos_matchups['away_forward_height']
pos_matchups['forward_weight_adv'] = pos_matchups['home_forward_weight'] - pos_matchups['away_forward_weight']

  # Quick look at distributions
print("Position-specific advantages:")
print(pos_matchups[['defense_height_adv', 'defense_weight_adv',
                      'forward_height_adv', 'forward_weight_adv']].describe())

  # =============================================================================
  # PART 5: REGRESSION - DO BIGGER D OR SMALLER F WIN?
  # =============================================================================

import statsmodels.api as sm

  # Model 1: Position-specific size effects
X = pos_matchups[['defense_height_adv', 'defense_weight_adv',
                     'forward_height_adv', 'forward_weight_adv']].dropna()
y = pos_matchups.loc[X.index, 'home_win']

X_const = sm.add_constant(X)
model_pos = sm.Logit(y, X_const).fit()

print("\n" + "="*70)
print("MODEL 1: POSITION-SPECIFIC SIZE EFFECTS")
print("="*70)
print(model_pos.summary2().tables[1])

  # Odds ratios
print("\nOdds Ratios (per 1 unit advantage):")
for var in X.columns:
    coef = model_pos.params[var]
    pval = model_pos.pvalues[var]
    odds = np.exp(coef)
    sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
    print(f"  {var:25s}: OR = {odds:.4f}, p = {pval:.4f} {sig}")

  # =============================================================================
  # PART 6: ADD TENURE BACK IN - FULL MODEL
  # =============================================================================

  # We need to merge tenure data back in
  # Calculate team-level tenure from game_rosters

tenure_by_team = game_rosters.groupby(['game_id', 'teamId']).agg({
      'nhl_tenure': 'mean',
      'age': 'mean'
  }).reset_index()

tenure_by_team = tenure_by_team.rename(columns={
      'nhl_tenure': 'team_tenure',
      'age': 'team_age'
  })

  # Merge tenure for home team
pos_matchups = pos_matchups.merge(
      tenure_by_team.rename(columns={'teamId': 'home_teamId',
                                      'team_tenure': 'home_tenure',
                                      'team_age': 'home_age'}),
      left_on=['game_id', 'home_teamId'],
      right_on=['game_id', 'home_teamId'],
      how='left'
  )

  # Merge tenure for away team
pos_matchups = pos_matchups.merge(
      tenure_by_team.rename(columns={'teamId': 'away_teamId',
                                      'team_tenure': 'away_tenure',
                                      'team_age': 'away_age'}),
      left_on=['game_id', 'away_teamId'],
      right_on=['game_id', 'away_teamId'],
      how='left'
  )

  # Calculate advantages
pos_matchups['tenure_adv'] = pos_matchups['home_tenure'] - pos_matchups['away_tenure']
pos_matchups['age_adv'] = pos_matchups['home_age'] - pos_matchups['away_age']

print(f"Full dataset: {len(pos_matchups)} games")

  # =============================================================================
  # PART 7: FULL MODEL - POSITION SIZE + TENURE + AGE
  # =============================================================================

  # Full model with everything
X_full = pos_matchups[['defense_height_adv', 'defense_weight_adv',
                          'forward_height_adv', 'forward_weight_adv',
                          'tenure_adv', 'age_adv']].dropna()
y_full = pos_matchups.loc[X_full.index, 'home_win']

X_full_const = sm.add_constant(X_full)
model_full = sm.Logit(y_full, X_full_const).fit()

print("\n" + "="*70)
print("MODEL 2: POSITION SIZE + TENURE + AGE")
print("="*70)
print(model_full.summary2().tables[1])

print("\nOdds Ratios:")
for var in X_full.columns:
      coef = model_full.params[var]
      pval = model_full.pvalues[var]
      odds = np.exp(coef)
      sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
      print(f"  {var:25s}: OR = {odds:.4f}, p = {pval:.4f} {sig}")

  # =============================================================================
  # PART 8: VISUALIZATION - COEFFICIENT PLOT
  # =============================================================================

import matplotlib.pyplot as plt
import matplotlib as mpl

mpl.rcParams['font.family'] = 'Charter'

  # Brand colors
col_blue_pale = '#3B4B64'
col_blue_dark = '#041E42'
col_oil_orange = '#FF4C00'
col_gray = '#9AA3AF'

  # Extract coefficients and CIs
vars_to_plot = ['defense_height_adv', 'defense_weight_adv',
                  'forward_height_adv', 'forward_weight_adv',
                  'tenure_adv', 'age_adv']

coefs = model_full.params[vars_to_plot]
conf = model_full.conf_int().loc[vars_to_plot]
pvals = model_full.pvalues[vars_to_plot]

  # Nice labels
labels = ['Defense Height', 'Defense Weight', 'Forward Height', 'Forward Weight',
            'NHL Tenure', 'Age']

  # Colors based on significance
colors = [col_oil_orange if p < 0.05 else col_gray for p in pvals]

fig, ax = plt.subplots(figsize=(10, 6))

y_pos = range(len(vars_to_plot))
ax.barh(y_pos, coefs, xerr=[coefs - conf[0], conf[1] - coefs],
          color=colors, edgecolor=col_blue_dark, linewidth=1.2,
          capsize=5, alpha=0.85)

ax.axvline(x=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
ax.set_yticks(y_pos)
ax.set_yticklabels(labels, fontsize=12)
ax.set_xlabel('Coefficient (log odds)', fontsize=14)

  # Add significance stars
for i, (coef, pval) in enumerate(zip(coefs, pvals)):
      sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
      ax.text(coef + 0.02 if coef > 0 else coef - 0.02, i, sig,
              va='center', ha='left' if coef > 0 else 'right',
              fontsize=14, fontweight='bold', color=col_oil_orange)

import seaborn as sns
sns.despine()
ax.grid(False)

  # Title
left_x = ax.get_position().x0
plt.subplots_adjust(top=0.85)

fig.suptitle("Does Size Matter by Position?", fontsize=20, weight='bold',
               x=left_x, ha='left', y=0.96)
fig.text(left_x, 0.88,
           "Position-specific size advantages and their effect on winning",
           fontsize=14, ha='left')
fig.text(0.9, 0.01,
           f"Data: {len(y_full):,} NHL games (2010-2025) | 95% CI shown",
           fontsize=10, style='italic', ha='right')

plt.savefig('/Users/dwiwad/desktop/position_size_effects.png', dpi=300,
              facecolor='white', bbox_inches='tight')
plt.show()

  # =============================================================================
  # PART 9: EXPLORE BY ERA - HAS POSITION SIZE CHANGED OVER TIME?
  # =============================================================================

  # Add season/era to the data
pos_matchups['season'] = pos_matchups['game_id'].astype(str).str[:4].astype(int)

  # Define eras
def get_era(season):
      if season < 2013:
          return '2010-2012'
      elif season < 2016:
          return '2013-2015'
      elif season < 2019:
          return '2016-2018'
      elif season < 2022:
          return '2019-2021'
      else:
          return '2022-2024'

pos_matchups['era'] = pos_matchups['season'].apply(get_era)

  # Run regression by era
print("\n" + "="*70)
print("DEFENSE WEIGHT EFFECT BY ERA")
print("="*70)

era_results = []
for era in sorted(pos_matchups['era'].unique()):
      era_data = pos_matchups[pos_matchups['era'] == era]
      X_era = era_data[['defense_weight_adv']].dropna()
      y_era = era_data.loc[X_era.index, 'home_win']

      X_era_const = sm.add_constant(X_era)
      model_era = sm.Logit(y_era, X_era_const).fit(disp=0)

      coef = model_era.params['defense_weight_adv']
      pval = model_era.pvalues['defense_weight_adv']
      n = len(y_era)

      era_results.append({'era': era, 'coef': coef, 'pval': pval, 'n': n})
      sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
      print(f"  {era}: coef = {coef:.4f}, p = {pval:.4f} {sig} (n={n:,})")

era_df = pd.DataFrame(era_results)

  # =============================================================================
  # PART 10: SCATTER - DEFENSE SIZE VS FORWARD SIZE (TEAM PROFILES)
  # =============================================================================

  # Calculate team-season averages
team_profiles = pos_matchups.groupby(['season', 'home_teamId']).agg({
      'home_defense_weight': 'mean',
      'home_forward_weight': 'mean',
      'home_win': 'mean'
  }).reset_index()

team_profiles.columns = ['season', 'team_id', 'defense_weight', 'forward_weight', 'win_pct']

fig, ax = plt.subplots(figsize=(10, 8))

scatter = ax.scatter(team_profiles['defense_weight'],
                       team_profiles['forward_weight'],
                       c=team_profiles['win_pct'],
                       cmap='RdYlGn',
                       s=50, alpha=0.6, edgecolors=col_blue_dark, linewidth=0.5)

ax.set_xlabel('Avg Defense Weight (lbs)', fontsize=14)
ax.set_ylabel('Avg Forward Weight (lbs)', fontsize=14)

cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Win %', fontsize=12)

  # Add reference lines at means
ax.axvline(team_profiles['defense_weight'].mean(), color=col_gray, linestyle='--', alpha=0.5)
ax.axhline(team_profiles['forward_weight'].mean(), color=col_gray, linestyle='--', alpha=0.5)

sns.despine()
ax.grid(False)

left_x = ax.get_position().x0
plt.subplots_adjust(top=0.88)

fig.suptitle("Team Size Profiles: Defense vs Forward Weight", fontsize=20, weight='bold',
               x=left_x, ha='left', y=0.96)
fig.text(left_x, 0.90,
           "Each point is a team-season; color shows win percentage",
           fontsize=14, ha='left')

plt.savefig('/Users/dwiwad/desktop/team_size_profiles.png', dpi=300,
              facecolor='white', bbox_inches='tight')
plt.show()

  # Correlation
from scipy.stats import pearsonr
r_def, p_def = pearsonr(team_profiles['defense_weight'], team_profiles['win_pct'])
r_fwd, p_fwd = pearsonr(team_profiles['forward_weight'], team_profiles['win_pct'])
print(f"\nCorrelation with win%:")
print(f"  Defense weight: r = {r_def:.3f}, p = {p_def:.4f}")
print(f"  Forward weight: r = {r_fwd:.3f}, p = {p_fwd:.4f}")










