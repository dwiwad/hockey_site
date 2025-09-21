import numpy as np
import pandas as pd

# Take coefficients from your fitted interaction model
params = results_ctrl.params
b0 = params['Intercept']
b1 = params['depth_rolling10']
b2 = params['sogs_z']
b3 = params['depth_rolling10:sogs_z']

# Logistic link
def logit(x): return 1 / (1 + np.exp(-x))

# Define a function for marginal effect of depth at a given SOG level
def marginal_effect_depth(depth_val, sog_val):
    # linear predictor
    linpred = b0 + b1*depth_val + b2*sog_val + b3*depth_val*sog_val
    p = logit(linpred)
    # derivative of logit wrt depth = p*(1-p)*(b1 + b3*sog_val)
    return p*(1-p)*(b1 + b3*sog_val)

# Evaluate at mean depth and sog levels (-2,0,2)
depth0 = 0
sog_levels = [-2,0,2]
effects = {s: marginal_effect_depth(depth0, s) for s in sog_levels}

print("Marginal effect of +1 SD Depth on win probability at different SOG levels:")
for s,v in effects.items():
    print(f"SOGs_z={s}: {v:.4f}")

depth_q25, depth_q75 = model_data['depth_rolling10'].quantile([0.25,0.75])
sog_levels = [-2,0,2]
rows = []

for s in sog_levels:
    X_low = pd.DataFrame({'depth_rolling10':[depth_q25], 'sogs_z':[s]})
    X_high = pd.DataFrame({'depth_rolling10':[depth_q75], 'sogs_z':[s]})
    p_low = results_ctrl.predict(X_low)[0]
    p_high = results_ctrl.predict(X_high)[0]
    rows.append({'sogs_z':s, 'prob_low':p_low, 'prob_high':p_high,
                 'delta':p_high - p_low})

pd.DataFrame(rows)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --- compute deltas (p75 - p25) at SOG tiers
q25, q75 = model_data['depth_rolling10'].quantile([0.25, 0.75])
sog_levels = [-2, 0, 2]

rows = []
for s in sog_levels:
    X_low  = pd.DataFrame({'depth_rolling10': [q25], 'sogs_z': [s]})
    X_high = pd.DataFrame({'depth_rolling10': [q75], 'sogs_z': [s]})
    p_low  = results_ctrl.predict(X_low)[0]
    p_high = results_ctrl.predict(X_high)[0]
    rows.append({'SOGs_z': s, 'DeltaWinProb': p_high - p_low})

df = pd.DataFrame(rows)

# --- bar plot
plt.figure(figsize=(7,5))
plt.bar(df['SOGs_z'].astype(str), df['DeltaWinProb'])
plt.xlabel("Shot Level (SOGs_z)")
plt.ylabel("Δ Win Probability (p75 depth – p25 depth)")
plt.title("Depth Converts Shot Volume into Wins More at High Shot Levels")

# annotate bars
for i, v in enumerate(df['DeltaWinProb']):
    plt.text(i, v + 0.002, f"{v:.3f}", ha='center', va='bottom', fontsize=10)

plt.tight_layout()
plt.show()






import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Build a grid of predictor values
xgoal_range = np.linspace(model_data['xgoal'].min(),
                          model_data['xgoal'].max(), 50)
sog_levels = [10, 25, 40]  # low, medium, high shot volumes

grid = pd.DataFrame([
    {'xgoal': x, 'total_sogs': s}
    for x in xgoal_range for s in sog_levels
])

# Predict probabilities from the fitted model
grid['pred_prob'] = results.predict(grid)

# Plot
plt.figure(figsize=(8,6))
for s in sog_levels:
    subset = grid[grid['total_sogs'] == s]
    plt.plot(subset['xgoal'], subset['pred_prob'],
             label=f"SOGs = {s}")

plt.xlabel("Expected Goals (xG)")
plt.ylabel("Predicted Win Probability")
plt.title("Interaction: xG × Shots on Goal")
plt.legend(title="Shot Volume Level")
plt.show()
