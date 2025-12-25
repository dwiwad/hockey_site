import pandas as pd
import statsmodels.formula.api as smf
from sklearn.linear_model import LinearRegression 
from scipy.stats import zscore
import graphviz
import semopy as sp
import s3fs
from app.core.config import S3_BUCKET


PREFIX = "static-ds-analyses/total-depth-index/all-seasons"
OBJECT = "final_game_data_20102025.csv"

fs = s3fs.S3FileSystem(anon=False)
path = f"s3://{S3_BUCKET}/{PREFIX}/{OBJECT}"

print(f"Loading {path}")
game_data = pd.read_csv(path, storage_options={"anon": False}, low_memory=False)

# Append season like "20102011" based on first 4 digits of game_id
yr = game_data["game_id"].astype(str).str[:4].astype(int)
game_data["season"] = yr.astype(str) + (yr + 1).astype(str)

print(game_data[["game_id", "season"]].head())

# Keep games where positions 5–6 of game_id are "02" or "03"
mid = game_data["game_id"].astype(str).str[4:6]
mask = mid.isin(["02", "03"])
game_data_regular = game_data.loc[mask].copy()

print(f"Rows kept (02 or 03): {len(game_data_regular)} / {len(game_data)}")
print(game_data_regular["game_id"].head())



##############################################################################
#
# READ BACK IN THE GAME DATA
#
##############################################################################

#data = pd.read_csv('~/dev/hockey_site/data/total-depth-index/final_data_20242025.csv')

# I think I need to remove pre-season games, there are data inconsistencies
#data = data[~data['game_id'].astype(str).str.startswith("202401")]


##############################################################################
#
# STRUCTURAL EQUATION MODEL
#
##############################################################################

game_data_regular["sog_depth_z"] = -zscore(game_data_regular["sog_gini"])
game_data_regular['xgoal_depth_z'] = -zscore(game_data_regular['xgoal_gini'])
game_data_regular["assist_depth_z"] = -zscore(game_data_regular["assist_gini"])
game_data_regular["toi_depth_z"] = -zscore(game_data_regular["toi_gini"])
game_data_regular["corsi_for_z"] = zscore(game_data_regular["corsi_for"])
game_data_regular["cf_depth_z"] = -zscore(game_data_regular["cf_gini"])
game_data_regular['sogs_z'] = zscore(game_data_regular['total_sogs'])
game_data_regular['xgoal_z'] = zscore(game_data_regular['xgoal'])

game_data_regular.to_csv('~/dev/hockey_site/data/total-depth-index/final_data_20102025.csv', index=False)

model_desc = """
    # Simple model
    depth =~ 1*cf_depth_z + sog_depth_z + xgoal_depth_z + assist_depth_z + toi_depth_z

    """

model = sp.Model(model_desc)

res = model.fit(game_data_regular)
print(res)

ins = model.inspect()
print(ins)

stats = sp.calc_stats(model)
print(stats)

#sp.report(model, "sem_report.html")

#sp.semplot(model, "depth_model.svg", plot_ests=True, std_ests=True) 

# RMSEA = .06
# CFI = .94

"""
Interpret depth as: “More Corsi and shot balance, 
but teams with depth also tend to have a bit more concentrated TOI distribution.”

This might actually reflect reality (coaches lean on 
                                     stars in minutes but still spread shots/production).
"""


"""
This paints a very hockey-plausible story:

Teams with more “depth” produce offense across the lineup (shots are balanced, 
    Corsi is strong) but they still lean on stars for ice time — meaning depth doesn’t 
necessarily mean equal minutes, it means effective contributions outside the top line.

That interpretation makes sense: “depth” here isn’t democratic playing time — 
it’s distributed shot production, even if stars eat the minutes.
"""

model_desc = """
    # Simple model
    depth =~ 1*cf_depth_z + sog_depth_z + toi_depth_z + xgoal_depth_z
    """

model = sp.Model(model_desc)

res = model.fit(game_data_regular)
print(res)

ins = model.inspect()
print(ins)

stats = sp.calc_stats(model)
print(stats)



# A little predictive validity test
factor_scores = model.predict_factors(game_data_regular)
game_data_regular['tdi_factor'] = zscore(factor_scores['depth'])

game_data_regular = game_data_regular.sort_values(['teamAbbrev', 'game_id'])

# Rolling 10-game mean of depth
game_data_regular['depth_rolling10'] = (
    game_data_regular.groupby('teamAbbrev')['tdi_factor']
    .transform(lambda x: x.rolling(window=10, min_periods=5).mean())
)


game_data_regular['depth_rolling10'] = (
    game_data_regular.groupby('teamAbbrev')['tdi_factor']
        .transform(lambda s: s.shift(1).rolling(window=10, min_periods=5).mean())
)

# Subset to rows where we have rolling depth values
model_data = game_data_regular.dropna(subset=['depth_rolling10'])

import statsmodels.formula.api as smf

# Simple model with just depth
logit_model = smf.logit("outcome ~ depth_rolling10", data=model_data)
results = logit_model.fit()
print(results.summary())

# Simple model with just depth
logit_model = smf.logit("outcome ~ tdi_factor", data=game_data_regular)
results = logit_model.fit()
print(results.summary())

logit_model = smf.ols("total_sogs ~ tdi_factor", data=game_data_regular)
results = logit_model.fit()
print(results.summary())

logit_model = smf.ols("xgoal ~ tdi_factor", data=game_data_regular)
results = logit_model.fit()
print(results.summary())

# Simple model with just depth
logit_model = smf.logit("outcome ~ xgoal * total_sogs", data=game_data_regular)
results = logit_model.fit()
print(results.summary())

# Simple model with just depth
logit_model = smf.logit("outcome ~ xgoal * tdi_factor", data=game_data_regular)
results = logit_model.fit()
print(results.summary())