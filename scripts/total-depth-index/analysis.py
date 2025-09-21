"""
Created on Fri Sep 19 12:07:21 2025

@author: dwiwad
"""

"""
Created on Tue Sep 16 07:45:52 2025

@author: dwiwad
"""
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.linear_model import LinearRegression 
from scipy.stats import zscore
import graphviz
import semopy as sp

##############################################################################
#
# READ BACK IN THE GAME DATA
#
##############################################################################

data = pd.read_csv('~/dev/hockey_site/data/total-depth-index/final_data_20242025.csv')

# I think I need to remove pre-season games, there are data inconsistencies
data = data[~data['game_id'].astype(str).str.startswith("202401")]


##############################################################################
#
# STRUCTURAL EQUATION MODEL
#
##############################################################################

data["sog_depth_z"] = -zscore(data["sog_gini"])
data['xgoal_depth_z'] = -zscore(data['xgoal_gini'])
data["assist_depth_z"] = -zscore(data["assist_gini"])
data["toi_depth_z"] = -zscore(data["toi_gini"])
data["corsi_for_z"] = zscore(data["corsi_for"])
data["cf_depth_z"] = -zscore(data["cf_gini"])
data['sogs_z'] = zscore(data['total_sogs'])
data['xgoal_z'] = zscore(data['xgoal'])

model_desc = """
    # Simple model
    depth =~ 1*cf_depth_z + sog_depth_z + xgoal_depth_z + assist_depth_z + toi_depth_z

    """

model = sp.Model(model_desc)

res = model.fit(data)
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

res = model.fit(data)
print(res)

ins = model.inspect()
print(ins)

stats = sp.calc_stats(model)
print(stats)




# A little predictive validity test
factor_scores = model.predict_factors(data)
data['tdi_factor'] = zscore(factor_scores['depth'])

data = data.sort_values(['teamAbbrev', 'game_id'])

# Rolling 10-game mean of depth
data['depth_rolling10'] = (
    data.groupby('teamAbbrev')['tdi_factor']
    .transform(lambda x: x.rolling(window=10, min_periods=5).mean())
)


data['depth_rolling10'] = (
    data.groupby('teamAbbrev')['tdi_factor']
        .transform(lambda s: s.shift(1).rolling(window=10, min_periods=5).mean())
)

# Subset to rows where we have rolling depth values
model_data = data.dropna(subset=['depth_rolling10'])

import statsmodels.formula.api as smf

# Simple model with just depth
logit_model = smf.logit("outcome ~ depth_rolling10", data=model_data)
results = logit_model.fit()
print(results.summary())

# Simple model with just depth
logit_model = smf.logit("outcome ~ tdi_factor", data=data)
results = logit_model.fit()
print(results.summary())

logit_model = smf.ols("total_sogs ~ tdi_factor", data=data)
results = logit_model.fit()
print(results.summary())

logit_model = smf.ols("xgoal ~ tdi_factor", data=data)
results = logit_model.fit()
print(results.summary())

# Simple model with just depth
logit_model = smf.logit("outcome ~ xgoal * total_sogs", data=data)
results = logit_model.fit()
print(results.summary())

# Simple model with just depth
logit_model = smf.logit("outcome ~ xgoal * tdi_factor", data=data)
results = logit_model.fit()
print(results.summary())

# Add controls (shots, xG, etc.)
logit_model_ctrl = smf.logit(
    "outcome ~ depth_rolling10 * sogs_z",
    data=model_data
)
results_ctrl = logit_model_ctrl.fit()
print(results_ctrl.summary())


import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Make grid of predictor values
depth_range = np.linspace(model_data['depth_rolling10'].min(),
                          model_data['depth_rolling10'].max(), 50)
sog_range = [-2, 0, 2]  # low, average, high standardized shots

grid = pd.DataFrame([
    {'depth_rolling10': d, 'sogs_z': s}
    for d in depth_range for s in sog_range
])

# Predict probabilities
grid['pred_prob'] = results_ctrl.predict(grid)

# Plot
plt.figure(figsize=(8,6))
for s in sog_range:
    subset = grid[grid['sogs_z'] == s]
    plt.plot(subset['depth_rolling10'], subset['pred_prob'], label=f"SOGs_z={s}")

plt.xlabel("Rolling 10-game Depth")
plt.ylabel("Predicted Win Probability")
plt.title("Interaction: Depth × Shots on Goal")
plt.legend(title="Shot Level")
plt.show()


from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, brier_score_loss

# Sort by date
model_data = model_data.sort_values("game_id")

# Index to split (e.g., 70% point)
split_idx = int(0.7 * len(model_data))

train = model_data.iloc[:split_idx]
test  = model_data.iloc[split_idx:]

# Fit
model = smf.logit("outcome ~ total_sogs + xgoal + depth_rolling10", data=train).fit()

# Predict
test['pred_prob'] = model.predict(test)

auc = roc_auc_score(test['outcome'], test['pred_prob'])
brier = brier_score_loss(test['outcome'], test['pred_prob'])
print("AUC:", auc, "Brier:", brier)


# So depth as a construct works. Predicting next win a bit above chance, 56%
# But need to re-do this so I'm predicting the matchup, not for each team. 
# So a differential score.
# Try a version with corsi depth (cf/60 inverse gini)

# Mediation model - semopy can't do this so I need to do it in R


##############################################################################
#
# GRAVEYARD
#
##############################################################################

model = smf.logit(formula='outcome ~ sogs_z * tdi_factor', data=data)
results = model.fit()
results.summary()



model = smf.logit(formula='outcome ~ sogs_z + corsi_for_z + sog_depth_z + toi_depth_z + xgoal_depth_z', data=data)
results = model.fit()
results.summary()


formula = """
outcome ~ sogs_z
          + corsi_for_z + sog_depth_z + toi_depth_z + xgoal_depth_z
          + sogs_z:corsi_for_z
          + sogs_z:sog_depth_z
          + sogs_z:toi_depth_z
          + sogs_z:xgoal_depth_z
"""

model = smf.logit(formula=formula, data=data)
results = model.fit()
print(results.summary())











# unit weighted model
data['tdi'] = data['corsi_for_z'] + (data['sog_depth_z']) + (data['toi_depth_z']) + (data['xgoal_depth_z'])
data['tdi_z'] = zscore(data['tdi'])


model = smf.logit(formula='outcome ~ sogs_z*tdi_z', data=data)
results = model.fit()
results.summary()

"""
Whoa. So SOGs only matter if you have depth. Taking a lot of shots predicts winning
fairly strongly (beta = .169). And depth on it's own doesn't really predict winning
(beta = .028). BUT there is a significant interaction and it is the most beautiful 
spreading interaction (beta = .081).

What it shows is that at low depth, it does not matter how many shots you take.
Your chance of winning hovers around 47%. And the more sogs - better win chance
relationship depends on depth. If you have low sogs and high depth, 40% chance of
winning. Average sogs and high depth, you're approaching 50%. High sogs and high
depth, 60% chance of winning.

Further, there is theoretical justification for depth as a metric comprised of
corsi, shot depth, and toi depth. I want to add xG so I can get model fit stats
and perhaps a slightly stronger model, and then rebuild on all 15 seasons.
"""





























data['tdi'] = (data['corsi_for'] * (.38*data['sog_gini']) * (-.10*data['toi_gini']))/3
data['tdi_z'] = zscore(data['tdi'])


model = smf.logit(formula='outcome ~ sogs_z*tdi_z', data=data)
results = model.fit()
results.summary()


data['tdi'] = (
    1.0*data['corsi_for_z'] +
    0.382*data['sog_depth_z'] +
   -0.097*data['toi_depth_z']
)/3

data['tdi_z'] = zscore(data['tdi'])


model = smf.logit(formula='outcome ~ sogs_z*tdi_z', data=data)
results = model.fit()
results.summary()



model = smf.logit(formula='outcome ~ sogs_z + sog_depth_z + toi_depth_z + corsi_for_z', data=data)
results = model.fit()
results.summary()


data['tdi'] = data['corsi_for_z'] * data['sog_depth_z'] * data['toi_depth_z']
data['tdi_z'] = zscore(data['tdi'])


model = smf.logit(formula='outcome ~ sogs_z*tdi_z', data=data)
results = model.fit()
results.summary()




# Two factor solution; this is sort of fascinating.
# Implies that toi inequality actually improves depth in scoring
# chances by driving higher corsi and sogs
model_desc = """
    # Simple model
    prod_depth =~ 1*corsi_for_z + sog_depth_z
    deploy_depth =~ toi_depth_z
    
    prod_depth ~~ deploy_depth

    """

model = sp.Model(model_desc)

res = model.fit(data)
print(res)

ins = model.inspect()
print(ins)

stats = sp.calc_stats(model)
print(stats)

data['tdi'] = data['corsi_for_z'] + (.382194*data['sog_depth_z'])
data['tdi_z'] = zscore(data['tdi'])


model = smf.logit(formula='outcome ~ sogs_z*tdi_z*toi_gini_z', data=data)
results = model.fit()
results.summary()




# So maybe a one factor sol'n with inequality not depth.
data['toi_gini_z'] = zscore(data['toi_gini'])

model_desc = """
    # Simple model
    depth =~ 1*corsi_for_z + sog_depth_z + toi_gini_z
    """

model = sp.Model(model_desc)

res = model.fit(data)
print(res)

ins = model.inspect()
print(ins)

stats = sp.calc_stats(model)
print(stats)

data['tdi'] = data['corsi_for_z'] + (.382194*data['sog_depth_z']) + (.096551*data['toi_gini_z'])
data['tdi_z'] = zscore(data['tdi'])


model = smf.logit(formula='outcome ~ sogs_z*tdi_z', data=data)
results = model.fit()
results.summary()












