"""
SEM configuration for Total Depth Index calculation.
Trained on 38,394 team-games from 2010-2025 seasons.

Model fit statistics:
- CFI: 0.987
- TLI: 0.961
- RMSEA: 0.070
- SRMR: 0.022
"""

# Factor score normalization (for final z-scoring)
# Raw factor scores from lavPredict have non-zero mean and SD ≠ 1
FACTOR_SCORE_MEAN = -0.0004392662
FACTOR_SCORE_SD = 0.5871541

# Factor score coefficients from lavPredict (regression method)
# These differ from factor loadings because they account for measurement error
FACTOR_SCORE_COEFFICIENTS = {
    'cf_depth_z': 0.1590167,
    'sog_depth_z': 0.3225073,
    'toi_depth_z': 0.02588038,
    'xgoal_depth_z': 0.1393442
}

# Gini coefficient normalization parameters (from training data)
# DEPTH (1 - Gini) normalization parameters from training data
DEPTH_MEANS = {
    'cf_depth': 0.615088,
    'sog_depth': 0.5370916,
    'toi_depth': 0.8426994,
    'xgoal_depth': 0.4122645
}

DEPTH_SDS = {
    'cf_depth': 0.07212831,
    'sog_depth': 0.08046992,
    'toi_depth': 0.034201,
    'xgoal_depth': 0.07786652
}