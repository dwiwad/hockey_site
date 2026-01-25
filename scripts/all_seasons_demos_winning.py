import pandas as pd
import numpy as np
from datetime import datetime
import statsmodels.api as sm

# Load data
df = pd.read_csv(
      's3://hockey-decoded/static-ds-analyses/nhl-player-demographics/rosters.csv',
      storage_options={'anon': False}
  )

all_games = pd.read_parquet(
      's3://hockey-decoded/parquet/all_games_clean.parquet',
      storage_options={'anon': False}
  )

# Get common seasons between both datasets
roster_seasons = set(df['season'].unique())
games_seasons = set(all_games['season'].unique())
common_seasons = sorted(roster_seasons & games_seasons)
print(f"Found {len(common_seasons)} seasons with both roster and game data")

# Process all seasons
all_outcomes = []

for season in common_seasons:
      try:
          # Filter to season
          seas_roster = df[df['season'] == season].copy()
          seas_games = all_games[all_games['season'] == season].copy()

          # Skip if no games or rosters
          if len(seas_roster) == 0 or len(seas_games) == 0:
              continue

          # Calculate winner
          seas_games['winner'] = np.where(
              seas_games['homeTeam.score'] > seas_games['awayTeam.score'],
              seas_games['homeTeam.abbrev'],
              seas_games['awayTeam.abbrev']
          )

          # Calculate age (season start = Oct 1 of first year)
          season_year = int(str(season)[:4])
          season_start = datetime(season_year, 10, 1)

          seas_roster['age'] = seas_roster['birth_date'].apply(
              lambda x: (season_start - pd.to_datetime(x)).days // 365 if pd.notna(x) else np.nan
          )

          # Team means
          means_by_team = seas_roster.groupby('team')[['height_in', 'weight_lb', 'age']].mean().reset_index()

          # Build outcomes
          outcomes = seas_games[['homeTeam.abbrev', 'awayTeam.abbrev', 'winner']].copy()
          outcomes['season'] = season

          # Merge home stats
          outcomes = outcomes.merge(
              means_by_team, left_on='homeTeam.abbrev', right_on='team', how='left'
          ).rename(columns={'height_in': 'home_height', 'weight_lb': 'home_weight', 'age': 'home_age'})
          outcomes = outcomes.drop(columns=['team'], errors='ignore')

          # Merge away stats
          outcomes = outcomes.merge(
              means_by_team, left_on='awayTeam.abbrev', right_on='team', how='left'
          ).rename(columns={'height_in': 'away_height', 'weight_lb': 'away_weight', 'age': 'away_age'})
          outcomes = outcomes.drop(columns=['team'], errors='ignore')

          all_outcomes.append(outcomes)
          print(f"✓ {season}: {len(outcomes)} games")

      except Exception as e:
          print(f"✗ {season}: {e}")

# Combine all seasons
outcomes_all = pd.concat(all_outcomes, ignore_index=True)
print(f"\nTotal games: {len(outcomes_all)}")

# Drop rows with missing data
outcomes_clean = outcomes_all.dropna(subset=['home_height', 'away_height', 'home_weight', 'away_weight', 'home_age', 'away_age'])
print(f"Games with complete data: {len(outcomes_clean)}")

# Now analyze across all seasons:

# Calculate advantages
outcomes_clean['home_win'] = (outcomes_clean['winner'] == outcomes_clean['homeTeam.abbrev']).astype(int)
outcomes_clean['height_adv'] = outcomes_clean['home_height'] - outcomes_clean['away_height']
outcomes_clean['weight_adv'] = outcomes_clean['home_weight'] - outcomes_clean['away_weight']
outcomes_clean['age_adv'] = outcomes_clean['home_age'] - outcomes_clean['away_age']

# Overall regression
X = outcomes_clean[['height_adv', 'weight_adv', 'age_adv']]
X = sm.add_constant(X)
y = outcomes_clean['home_win']

model = sm.Logit(y, X).fit()
print(model.summary())
print("\nOdds Ratios:")
print(np.exp(model.params))

# See how effects change over time:

# Run regression per season
season_coefs = []

for season in outcomes_clean['season'].unique():
      seas_data = outcomes_clean[outcomes_clean['season'] == season]
      if len(seas_data) < 50:  # skip small samples
          continue

      X = seas_data[['height_adv', 'weight_adv', 'age_adv']]
      X = sm.add_constant(X)
      y = seas_data['home_win']

      try:
          model = sm.Logit(y, X).fit(disp=0)
          season_coefs.append({
              'season': season,
              'height_coef': model.params['height_adv'],
              'weight_coef': model.params['weight_adv'],
              'age_coef': model.params['age_adv'],
              'n_games': len(seas_data)
          })
      except:
          continue

coefs_df = pd.DataFrame(season_coefs)
coefs_df['year'] = coefs_df['season'].astype(str).str[:4].astype(int)
coefs_df = coefs_df.sort_values('year')

# Visualize trends over time:
import matplotlib.pyplot as plt

fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)

axes[0].plot(coefs_df['year'], coefs_df['height_coef'], 'o-', color='steelblue')
axes[0].axhline(y=0, linestyle='--', color='black', alpha=0.5)
axes[0].set_ylabel('Height Coefficient')
axes[0].set_title('Does Being Taller Help Win? (Over Time)')

axes[1].plot(coefs_df['year'], coefs_df['weight_coef'], 'o-', color='orange')
axes[1].axhline(y=0, linestyle='--', color='black', alpha=0.5)
axes[1].set_ylabel('Weight Coefficient')
axes[1].set_title('Does Being Heavier Help Win?')

axes[2].plot(coefs_df['year'], coefs_df['age_coef'], 'o-', color='purple')
axes[2].axhline(y=0, linestyle='--', color='black', alpha=0.5)
axes[2].set_ylabel('Age Coefficient')
axes[2].set_title('Does Being Older Help Win?')
axes[2].set_xlabel('Season Start Year')

plt.tight_layout()
#plt.savefig('/Users/dwiwad/desktop/size_age_trends.png', dpi=150)
plt.show()

# Define eras
def get_era(season):
      year = int(str(season)[:4])
      if year < 1943:
          return '1. Original Six Era (pre-1943)'
      elif year < 1967:
          return '2. Original Six (1943-1967)'
      elif year < 1980:
          return '3. Expansion Era (1967-1979)'
      elif year < 1995:
          return '4. High Scoring Era (1980-1994)'
      elif year < 2005:
          return '5. Dead Puck Era (1995-2004)'
      elif year < 2013:
          return '6. Post-Lockout (2005-2012)'
      else:
          return '7. Modern Speed Era (2013+)'

outcomes_clean['era'] = outcomes_clean['season'].apply(get_era)

# Regression by era
print("Weight coefficient by era (positive = heavier wins more):\n")

for era in sorted(outcomes_clean['era'].unique()):
      era_data = outcomes_clean[outcomes_clean['era'] == era]

      X = era_data[['height_adv', 'weight_adv', 'age_adv']]
      X = sm.add_constant(X)
      y = era_data['home_win']

      try:
          model = sm.Logit(y, X).fit(disp=0)
          sig = "***" if model.pvalues['weight_adv'] < 0.001 else "**" if model.pvalues['weight_adv'] < 0.01 else "*" if model.pvalues['weight_adv'] < 0.05 else ""
          print(f"{era}")
          print(f"   Weight: {model.params['weight_adv']:+.4f} {sig}  (n={len(era_data):,} games)")
          print(f"   Age:    {model.params['age_adv']:+.4f}")
          print()
      except:
          print(f"{era}: couldn't fit model")

# Visualize the trend:

# Use the per-season coefficients we calculated earlier
fig, ax = plt.subplots(figsize=(14, 6))

ax.scatter(coefs_df['year'], coefs_df['weight_coef'], alpha=0.5, s=30)

# Add smoothed trend line
from scipy.ndimage import uniform_filter1d
coefs_sorted = coefs_df.sort_values('year')
smoothed = uniform_filter1d(coefs_sorted['weight_coef'].values, size=5)
ax.plot(coefs_sorted['year'], smoothed, color='red', linewidth=2, label='5-year moving avg')

ax.axhline(y=0, linestyle='--', color='black', alpha=0.5)
ax.set_xlabel('Season Start Year', fontsize=12)
ax.set_ylabel('Weight Coefficient', fontsize=12)
ax.set_title('Does Being Heavier Help Win?\n(Positive = Yes, Negative = Lighter teams win more)', fontsize=14)
ax.legend()

# Add era annotations
ax.axvline(x=1967, color='gray', linestyle=':', alpha=0.5)
ax.axvline(x=1995, color='gray', linestyle=':', alpha=0.5)
ax.axvline(x=2005, color='gray', linestyle=':', alpha=0.5)
ax.axvline(x=2013, color='gray', linestyle=':', alpha=0.5)

plt.tight_layout()
#plt.savefig('/Users/dwiwad/desktop/weight_trend_by_year.png', dpi=150)
plt.show()

# Quick check - modern era only:

modern = outcomes_clean[outcomes_clean['season'] >= 20132014]

X = modern[['height_adv', 'weight_adv', 'age_adv']]
X = sm.add_constant(X)
y = modern['home_win']

model_modern = sm.Logit(y, X).fit()
print("MODERN ERA (2013+) ONLY:")
print(model_modern.summary())
print("\nOdds Ratios:")
print(np.exp(model_modern.params))



eras = ['Pre-1943', '1943-67', '1967-79', '1980-94', '1995-04', '2005-12', '2013+']
weight_coefs = [0.0077, 0.0046, 0.1170, 0.0706, 0.0217, 0.0019, 0.0104]
age_coefs = [-0.0861, 0.0713, 0.1635, 0.1311, 0.1675, 0.1031, 0.1213]

fig, ax = plt.subplots(figsize=(10, 6))

x = range(len(eras))
width = 0.35

bars1 = ax.bar([i - width/2 for i in x], weight_coefs, width, label='Weight', color='orange')
bars2 = ax.bar([i + width/2 for i in x], age_coefs, width, label='Age', color='purple')

ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
ax.set_xticks(x)
ax.set_xticklabels(eras, rotation=45, ha='right')
ax.set_ylabel('Coefficient (effect on winning)')
ax.set_title('Size vs Experience: What Wins in Each Era?')
ax.legend()

plt.tight_layout()
#plt.savefig('/Users/dwiwad/desktop/era_comparison.png', dpi=150)
plt.show()


# Get all three coefficients by era
print("All coefficients by era:\n")

era_results = []

for era in sorted(outcomes_clean['era'].unique()):
      era_data = outcomes_clean[outcomes_clean['era'] == era]

      X = era_data[['height_adv', 'weight_adv', 'age_adv']]
      X = sm.add_constant(X)
      y = era_data['home_win']

      try:
          model = sm.Logit(y, X).fit(disp=0)
          era_results.append({
              'era': era,
              'height': model.params['height_adv'],
              'weight': model.params['weight_adv'],
              'age': model.params['age_adv'],
              'n': len(era_data)
          })
          print(f"{era}")
          print(f"   Height: {model.params['height_adv']:+.4f} (p={model.pvalues['height_adv']:.3f})")
          print(f"   Weight: {model.params['weight_adv']:+.4f} (p={model.pvalues['weight_adv']:.3f})")
          print(f"   Age:    {model.params['age_adv']:+.4f} (p={model.pvalues['age_adv']:.3f})")
          print()
      except:
          print(f"{era}: couldn't fit model")

era_df = pd.DataFrame(era_results)

# Visualization with all three:

fig, ax = plt.subplots(figsize=(12, 6))

x = range(len(era_df))
width = 0.25

bars1 = ax.bar([i - width for i in x], era_df['height'], width, label='Height', color='steelblue')
bars2 = ax.bar([i for i in x], era_df['weight'], width, label='Weight', color='orange')
bars3 = ax.bar([i + width for i in x], era_df['age'], width, label='Age', color='purple')

ax.axhline(y=0, color='black', linestyle='--', alpha=0.5)
ax.set_xticks(x)
ax.set_xticklabels(['Pre-43', '43-67', '67-79', '80-94', '95-04', '05-12', '2013+'], rotation=45, ha='right')
ax.set_ylabel('Coefficient (effect on winning)')
ax.set_title('Height, Weight & Age: What Wins in Each Era?')
ax.legend()

plt.tight_layout()
#plt.savefig('/Users/dwiwad/desktop/era_all_three.png', dpi=150)
plt.show()

