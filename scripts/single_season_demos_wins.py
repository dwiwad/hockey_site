import pandas as pd
import numpy as np

# Bring in all rosters, at the season level
df = pd.read_csv(
     's3://hockey-decoded/static-ds-analyses/nhl-player-demographics/rosters.csv',
     storage_options={'anon': False}
)

print(df.columns.tolist())
print(f"Total rows: {len(df)}")

# Bring in all games historically
# I have this data from early explorations so let's put it in s3
all_games = pd.read_csv('~/Desktop/NHL Data/all_games_clean.csv')
print(all_games.columns.tolist())

# One off, stick it in S3
#all_games.to_parquet(
#    's3://hockey-decoded/parquet/all_games_clean.parquet',
#    storage_options={'anon': False},
#    index=False
#)

# Let's just, for ease, look at 1917-1918
one_seas_roster = df[df['season'] == 19301931]
one_seas_outcomes = all_games[all_games['season'] == 19301931]

# homeTeam.score and awayTeam.score for the win
one_seas_outcomes['winner'] = np.where(
    one_seas_outcomes['homeTeam.score'] > one_seas_outcomes['awayTeam.score'],
    one_seas_outcomes['homeTeam.abbrev'],
    one_seas_outcomes['awayTeam.abbrev']
)

# Now let's get average height, weight, and age for each teams roster
from datetime import datetime

# Age as of Oct 1 of the season
season_start = datetime(1930, 10, 1)  # adjust per season

one_seas_roster['age'] = one_seas_roster['birth_date'].apply(
    lambda x: (season_start - pd.to_datetime(x)).days // 365
)


means_by_team = one_seas_roster.groupby('team')[['height_in', 'weight_lb', 'age']].mean().reset_index()

# Join into the game outcoms
outcomes = one_seas_outcomes[['homeTeam.abbrev', 'awayTeam.abbrev', 'winner']]

# Merge home team stats
outcomes = outcomes.merge(
    means_by_team,
    left_on='homeTeam.abbrev',
    right_on='team',
    suffixes=('', '_home')
).rename(columns={
    'height_in': 'home_height',
    'weight_lb': 'home_weight',
    'age': 'home_age'
}).drop(columns=['team'])

# Merge away team stats
outcomes = outcomes.merge(
    means_by_team,
    left_on='awayTeam.abbrev',
    right_on='team',
    suffixes=('', '_away')
).rename(columns={
    'height_in': 'away_height',
    'weight_lb': 'away_weight',
    'age': 'away_age'
}).drop(columns=['team'])

outcomes.head()


import matplotlib.pyplot as plt
from scipy import stats

# First, calculate winner vs loser stats
outcomes['winner_is_home'] = outcomes['winner'] == outcomes['homeTeam.abbrev']

# Get winner/loser stats
outcomes['winner_height'] = np.where(outcomes['winner_is_home'], outcomes['home_height'], outcomes['away_height'])
outcomes['loser_height'] = np.where(outcomes['winner_is_home'], outcomes['away_height'], outcomes['home_height'])
outcomes['winner_weight'] = np.where(outcomes['winner_is_home'], outcomes['home_weight'], outcomes['away_weight'])
outcomes['loser_weight'] = np.where(outcomes['winner_is_home'], outcomes['away_weight'], outcomes['home_weight'])
outcomes['winner_age'] = np.where(outcomes['winner_is_home'], outcomes['home_age'], outcomes['away_age'])
outcomes['loser_age'] = np.where(outcomes['winner_is_home'], outcomes['away_age'], outcomes['home_age'])

# Calculate differences
outcomes['height_diff'] = outcomes['winner_height'] - outcomes['loser_height']
outcomes['weight_diff'] = outcomes['winner_weight'] - outcomes['loser_weight']
outcomes['age_diff'] = outcomes['winner_age'] - outcomes['loser_age']

# Quick stats
print("Winner vs Loser Differences (positive = winner is bigger/older)")
print(f"Height: {outcomes['height_diff'].mean():.2f} inches (p={stats.ttest_1samp(outcomes['height_diff'], 0)[1]:.4f})")
print(f"Weight: {outcomes['weight_diff'].mean():.2f} lbs (p={stats.ttest_1samp(outcomes['weight_diff'], 0)[1]:.4f})")
print(f"Age:    {outcomes['age_diff'].mean():.2f} years (p={stats.ttest_1samp(outcomes['age_diff'], 0)[1]:.4f})")



fig, axes = plt.subplots(1, 3, figsize=(14, 5))

# Height diff distribution
axes[0].hist(outcomes['height_diff'], bins=20, edgecolor='black', alpha=0.7)
axes[0].axvline(x=0, color='red', linestyle='--', label='No difference')
axes[0].axvline(x=outcomes['height_diff'].mean(), color='green', linestyle='-', label=f'Mean: {outcomes["height_diff"].mean():.2f}')
axes[0].set_xlabel('Winner - Loser Height (in)')
axes[0].set_title('Height Difference')
axes[0].legend()

# Weight diff distribution
axes[1].hist(outcomes['weight_diff'], bins=20, edgecolor='black', alpha=0.7, color='orange')
axes[1].axvline(x=0, color='red', linestyle='--')
axes[1].axvline(x=outcomes['weight_diff'].mean(), color='green', linestyle='-', label=f'Mean: {outcomes["weight_diff"].mean():.2f}')
axes[1].set_xlabel('Winner - Loser Weight (lbs)')
axes[1].set_title('Weight Difference')
axes[1].legend()

# Age diff distribution
axes[2].hist(outcomes['age_diff'], bins=20, edgecolor='black', alpha=0.7, color='purple')
axes[2].axvline(x=0, color='red', linestyle='--')
axes[2].axvline(x=outcomes['age_diff'].mean(), color='green', linestyle='-', label=f'Mean: {outcomes["age_diff"].mean():.2f}')
axes[2].set_xlabel('Winner - Loser Age (years)')
axes[2].set_title('Age Difference')
axes[2].legend()

plt.tight_layout()
plt.savefig('/Users/dwiwad/desktop/size_age_winning.png', dpi=150)
plt.show()


# Does the bigger team win more often?
outcomes['home_taller'] = outcomes['home_height'] > outcomes['away_height']
outcomes['home_heavier'] = outcomes['home_weight'] > outcomes['away_weight']
outcomes['home_older'] = outcomes['home_age'] > outcomes['away_age']

print("\nWin rate when home team is...")
print(f"Taller:  {outcomes[outcomes['home_taller']]['winner_is_home'].mean():.1%}")
print(f"Shorter: {outcomes[~outcomes['home_taller']]['winner_is_home'].mean():.1%}")
print(f"Heavier: {outcomes[outcomes['home_heavier']]['winner_is_home'].mean():.1%}")
print(f"Lighter: {outcomes[~outcomes['home_heavier']]['winner_is_home'].mean():.1%}")
print(f"Older:   {outcomes[outcomes['home_older']]['winner_is_home'].mean():.1%}")
print(f"Younger: {outcomes[~outcomes['home_older']]['winner_is_home'].mean():.1%}")

import statsmodels.api as sm

# Set up: predict home team win (1) vs away team win (0)
outcomes['home_win'] = (outcomes['winner'] == outcomes['homeTeam.abbrev']).astype(int)

# Differences (home - away)
outcomes['height_adv'] = outcomes['home_height'] - outcomes['away_height']
outcomes['weight_adv'] = outcomes['home_weight'] - outcomes['away_weight']
outcomes['age_adv'] = outcomes['home_age'] - outcomes['away_age']

# Logistic regression
X = outcomes[['height_adv', 'weight_adv', 'age_adv']]
X = sm.add_constant(X)  # Add intercept
y = outcomes['home_win']

model = sm.Logit(y, X).fit()
print(model.summary())

# Odds ratios (more intuitive than coefficients)
print("\nOdds Ratios:")
print(np.exp(model.params))

print("\n95% Confidence Intervals for Odds Ratios:")
print(np.exp(model.conf_int()))


model_ols = sm.OLS(y, X).fit()
print(model_ols.summary())

fig, ax = plt.subplots(figsize=(8, 5))

coefs = model.params[1:]  # exclude constant
errors = model.bse[1:]
names = ['Height Adv\n(per inch)', 'Weight Adv\n(per lb)', 'Age Adv\n(per year)']

ax.barh(names, coefs, xerr=1.96*errors, capsize=5, color=['steelblue', 'orange', 'purple'])
ax.axvline(x=0, color='black', linestyle='--')
ax.set_xlabel('Log Odds Coefficient')
ax.set_title('Effect of Size/Age Advantage on Winning')

plt.tight_layout()
#plt.savefig('/Users/dwiwad/desktop/regression_coefs.png', dpi=150)
plt.show()


# Do teams that are younger and or lighter have higher win percentages? 
# Do teams that are younger and or ligher end up higher in the standings?
# Avg weight and height of teams that make the playoffs compared to those who don't
# Avg weight and height of stanley cup winners vs not each year

# For the years I have game level data, look at it at the game level -
