# ---- Packages ----
library(dplyr)
library(tidyr)
library(slider)
library(rsample)
library(lavaan)

reg_seas <- data[which(data$game_id > 202403000),]
# ============================================
# 1) Lagged 10-game rolling avgs (no leakage)
# ============================================
# Assumes `data` has: game_id, teamAbbrev, outcome (0/1),
# total_sogs, xgoal, depth_factor, etc.

data_ra <- reg_seas %>%
  arrange(teamAbbrev, game_id) %>%
  group_by(teamAbbrev) %>%
  mutate(
    # rolling means over last 10 INCLUDING current -> then lag() to exclude current
    sog10   = slide_dbl(total_sogs,   mean, .before = 9, .complete = TRUE) %>% dplyr::lag(),
    xg10    = slide_dbl(xgoal,        mean, .before = 9, .complete = TRUE) %>% dplyr::lag(),
    depth10 = slide_dbl(depth_factor, mean, .before = 9, .complete = TRUE) %>% dplyr::lag()
  ) %>%
  ungroup()

# Keep games where both teams exist, have valid outcomes, and both have valid 10g histories
data_ra2 <- data_ra %>%
  group_by(game_id) %>%
  filter(
    n() == 2,
    all(c(0, 1) %in% outcome),
    !is.na(sog10) & !is.na(xg10) & !is.na(depth10)
  ) %>%
  ungroup()

# ===========================================================
# 2) Canonical one-row-per-game matchup table (ref vs opp)
#    - "ref" = lexicographically first teamAbbrev in game
#    - diffs = ref - opp
#    - target = did REF team win?
# ===========================================================
# --- Robust one-row-per-game matchup table ---
matchups <- data_ra2 %>%
  group_by(game_id) %>%
  arrange(teamAbbrev, .by_group = TRUE) %>%
  mutate(
    # tag rows deterministically within game
    rn = dplyr::row_number(),
    slot = dplyr::case_when(
      rn == 1 ~ "ref",
      rn == 2 ~ "opp",
      TRUE    ~ NA_character_
    )
  ) %>%
  # keep only games that truly have two teams
  filter(!is.na(slot)) %>%
  # if any game still has !=2 rows, drop it
  filter(dplyr::n() == 2) %>%
  select(game_id, slot, teamAbbrev, outcome, sog10, xg10, depth10) %>%
  ungroup() %>%
  tidyr::pivot_wider(
    names_from = slot,
    values_from = c(teamAbbrev, outcome, sog10, xg10, depth10),
    names_sep = "_"
  ) %>%
  mutate(
    sog_diff    = sog10_ref   - sog10_opp,
    xg_diff     = xg10_ref    - xg10_opp,
    depth_diff  = depth10_ref - depth10_opp,
    outcome_ref = outcome_ref   # ref team win? (1=yes, 0=no)
  ) %>%
  select(game_id, teamAbbrev_ref, teamAbbrev_opp,
         sog_diff, xg_diff, depth_diff, outcome_ref) %>%
  tidyr::drop_na(sog_diff, xg_diff, depth_diff, outcome_ref)


# ===================================
# 3) Train/test split (chronological)
# ===================================
set.seed(123)
split <- initial_time_split(matchups, prop = 0.7)
train_data <- training(split)
test_data  <- testing(split)

# =============================================
# 4) SEM: depth_diff -> (sog_diff, xg_diff) -> outcome_ref
#     - outcome_ref is binary; use WLSMV with ordered
# =============================================
sem_model <- '
  # mediators
  sog_diff ~ depth_diff
  xg_diff  ~ depth_diff

  # outcome equation
  outcome_ref ~ sog_diff + xg_diff + depth_diff
'

fit <- sem(sem_model,
           data      = train_data,
           ordered   = "outcome_ref",
           estimator = "WLSMV")

# Extract SEM outcome equation coefficients (intercept + paths)
params <- parameterEstimates(fit)

beta_depth <- params$est[params$lhs == "outcome_ref" & params$rhs == "depth_diff" & params$op == "~"]
beta_sog   <- params$est[params$lhs == "outcome_ref" & params$rhs == "sog_diff"   & params$op == "~"]
beta_xg    <- params$est[params$lhs == "outcome_ref" & params$rhs == "xg_diff"    & params$op == "~"]
beta_int   <- params$est[params$lhs == "outcome_ref" & params$op  == "~1"]

# SEM predictions on TEST
test_sem <- test_data %>%
  mutate(
    linpred = beta_int +
      beta_depth * depth_diff +
      beta_sog   * sog_diff +
      beta_xg    * xg_diff,
    prob = 1 / (1 + exp(-linpred)),
    pred = ifelse(prob > 0.5, 1, 0)
  )

acc_sem <- mean(test_sem$pred == test_sem$outcome_ref, na.rm = TRUE)

# ====================================================
# 5) Simple logits for xG-only, Depth-only, SOG-only
#     (trained on train_data, evaluated on test_data)
# ====================================================

# all
fit_all <- glm(outcome_ref ~ xg_diff + sog_diff + depth_diff,
              data = train_data, family = binomial)
pred_all <- predict(fit_all, newdata = test_data, type = "response")
acc_all  <- mean(ifelse(pred_all > 0.5, 1, 0) == test_data$outcome_ref, na.rm = TRUE)

# xG-only
fit_xg <- glm(outcome_ref ~ xg_diff,
              data = train_data, family = binomial)
pred_xg <- predict(fit_xg, newdata = test_data, type = "response")
acc_xg  <- mean(ifelse(pred_xg > 0.5, 1, 0) == test_data$outcome_ref, na.rm = TRUE)

# Depth-only
fit_depth <- glm(outcome_ref ~ depth_diff,
                 data = train_data, family = binomial)
pred_depth <- predict(fit_depth, newdata = test_data, type = "response")
acc_depth  <- mean(ifelse(pred_depth > 0.5, 1, 0) == test_data$outcome_ref, na.rm = TRUE)

# SOG-only
fit_sog <- glm(outcome_ref ~ sog_diff,
               data = train_data, family = binomial)
pred_sog <- predict(fit_sog, newdata = test_data, type = "response")
acc_sog  <- mean(ifelse(pred_sog > 0.5, 1, 0) == test_data$outcome_ref, na.rm = TRUE)

# =========================
# 6) Print the four results
# =========================
cat("\nTest-set accuracies (rolling 10-game, lagged predictors):\n")
cat(sprintf("  SEM (Depth→SOG/xG→Win) : %.3f\n", acc_sem))
cat(sprintf("  All logistic           : %.3f\n", acc_all))
cat(sprintf("  xG-only logistic       : %.3f\n", acc_xg))
cat(sprintf("  Depth-only logistic    : %.3f\n", acc_depth))
cat(sprintf("  SOG-only logistic      : %.3f\n\n", acc_sog))


