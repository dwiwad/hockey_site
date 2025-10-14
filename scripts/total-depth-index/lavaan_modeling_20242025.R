# Short script to grab all NHL team logos
library(httr)
library(jsonlite)

# Output directory
out_dir <- "~/dev/hockey_site/static/images/logos/"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

# Get team codes
teams <- fromJSON("https://api.nhle.com/stats/rest/en/team")$data
team_codes <- teams$triCode

# Download each logo
for (code in team_codes) {
  url <- paste0("https://assets.nhle.com/logos/nhl/svg/", code, "_light.svg")
  dest_file <- file.path(out_dir, paste0(code, "_light.svg"))
  
  resp <- GET(url)
  if (status_code(resp) == 200) {
    writeBin(content(resp, "raw"), dest_file)
    message("Saved: ", dest_file)
  } else {
    warning("Failed to fetch logo for ", code)
  }
}

getwd()
setwd("~/dev/hockey_site/data/total-depth-index/")
getwd()

data <- read.csv("final_data_20102025.csv", header = T)

data <- data[which(data$game_id > 2024020000),]

library(lavaan)

data$xgoal_z <- scale(data$xgoal)
data$sog_depth_z <- -scale(data$sog_gini)
data$assist_depth_z <- -scale(data$assist_gini)
data$toi_depth_z <- -scale(data$toi_gini)
data$xgoal_depth_z <- -scale(data$xgoal_gini)
data$cf_depth_z <- -scale(data$cf_gini)
data$sogs_z <- scale(data$total_sogs)
data$xgoal_z <- scale(data$xgoal)
data$corsi_for_z <- scale(data$corsi_for)

model <- ' 
depth =~ 1*cf_depth_z + assist_depth_z + sog_depth_z + toi_depth_z + xgoal_depth_z

         '

fit <- sem(model, data = data)
summary(fit, fit.measures=T)

model <- ' 
depth =~ 1*cf_depth_z + sog_depth_z + toi_depth_z + xgoal_depth_z

         '

fit <- sem(model, data = data)
summary(fit, fit.measures = T)

fit_config <- sem(model, data = data, group = "season")
fit_metric <- sem(model, data = data, group = "season", group.equal = "loadings")
fit_scalar <- sem(model, data = data, group = "season", group.equal = c("loadings", "intercepts"))
fit_strict <- sem(model, data = data, group = "season", group.equal = c("loadings", "intercepts", "residuals"))

anova(fit_config, fit_metric, fit_scalar, fit_strict)
fitMeasures(fit_config, c("cfi","rmsea","srmr"))
fitMeasures(fit_metric, c("cfi","rmsea","srmr"))
fitMeasures(fit_scalar, c("cfi","rmsea","srmr"))
fitMeasures(fit_strict, c("cfi","rmsea","srmr"))

library(semTools)
measurementInvariance(model=model, data = data, group = "season")




library(lavaanPlot)

lavaanPlot(model = fit, 
           node_options = list(shape = "box", fontname = "Helvetica"), 
           edge_options = list(color = "grey"), coefs = TRUE, sig = .05)


data$depth_factor <- lavPredict(fit)[, "depth"]


summary(glm(outcome~depth_factor, data = data, family = "binomial"))

model <- ' 
depth =~ 1*cf_depth_z + sog_depth_z + toi_depth_z + xgoal_depth_z

outcome ~ c*depth
xgoal_z ~ a1*depth
sogs_z ~ a2*depth

outcome ~ b1*xgoal_z
outcome ~ b2*sogs_z

xgoal_ind := a1*a2
sogs_ind := b1*b2

# total effects
total := c + (a1*b1) + (a2*b2)
         '

fit <- sem(model, data = data)
summary(fit, fit.measures = T)
fscores <- lavPredict(fit, method = "regression", fsm = TRUE)
attr(fscores, "fsm")
# Check if there are any intercepts in the model
lavInspect(fit, "est")$alpha
lavInspect(fit, "est")$nu

lavaanPlot(model = fit, 
           node_options = list(shape = "box", fontname = "Helvetica"), 
           edge_options = list(color = "grey"), coefs = TRUE, sig = .05)

summary(lm(outcome~sogs_z + xgoal_z, data = data))

"when you hold xG constant, extra shots tend to be low-quality,
low-conversion attempts (perimeter, blocked lanes, point shots). 
That’s why the conditional effect is negative."

"
4. Hockey interpretation

This story makes a lot of hockey sense:

Depth increases shot pressure (more players shooting).

But if those shots aren’t dangerous, they don’t help much once you account for xG.

Depth’s real value is in helping a team sustain dangerous chance generation across lines.

In other words: quality, not just volume, is what converts depth into wins.

5. How you can write this up

“Depth predicts both shot volume and expected goals. However, once quality (xG) 
is accounted for, additional shot volume is negatively associated with winning, 
consistent with the idea that many depth-driven shots are low quality. The true 
mechanism is that depth boosts a team’s ability to generate dangerous chances 
across the lineup, and it is this increase in xG that drives victories.”

⚖️ So yes, it absolutely makes sense that the SOG effect flips negative once you
condition on xG. It’s a suppression effect that reinforces your mediation claim:
depth matters because it raises the floor of chance quality, not because it floods
the net with undangerous shots.

"
model <- ' 
depth =~ 1*cf_depth_z + sog_depth_z + toi_depth_z + xgoal_depth_z

outcome ~ c*depth
sogs_z ~ a1*depth

outcome ~ a2*sogs_z

sogs_ind := a1*a2

# total effects
total_xgoal := c + (a1*a2)
         '

fit <- sem(model, data = data)
summary(fit, fit.measures = T)

summary(lm(outcome~sogs_z + xgoal_z, data = data))





model <- ' 
depth =~ 1*cf_depth_z + sog_depth_z + toi_depth_z + xgoal_depth_z

outcome ~ depth
xgoal_z ~ a1*depth
sogs_z ~ b1*depth
corsi_for_z ~ c1*depth


outcome ~ a2*xgoal_z
outcome ~ b2*sogs_z
outcome ~ c2*corsi_for_z

xgoal_ind := a1*a2
sogs_ind := b1*b2
corsi_ind := c1*c2

         '

fit <- sem(model, data = data)
fitMeasures(fit, c("rmsea", "cfi"))
summary(fit)

lavaanPlot(model = fit, 
           node_options = list(shape = "box", fontname = "Helvetica"), 
           edge_options = list(color = "grey"), coefs = TRUE, sig = .05)



model <- ' 
depth =~ 1*cf_depth_z + sog_depth_z + toi_depth_z + xgoal_depth_z

outcome ~ depth
sogs_z ~ a1*depth

xgoal_z ~ a2*sogs_z

outcome ~ a3*xgoal_z
outcome ~ sogs_z


xgoal_ind := a1*a2*a3
         '

fit <- sem(model, data = data)
summary(fit)

lavaanPlot(model = fit, 
           node_options = list(shape = "box", fontname = "Helvetica"), 
           edge_options = list(color = "grey"), coefs = TRUE, sig = .05)

# Bottom line: depth creates more high quality shots (xG), which leads to more wins.

# R version
model <- glm(outcome ~ depth_factor, data = data, family = binomial)

# Create quartiles
data$depth_q <- cut(data$depth_factor, breaks = quantile(data$depth_factor, probs=seq(0,1,0.25)), include.lowest=TRUE)

# Predicted probs at Q1 vs Q4
newdat <- data.frame(depth_factor = tapply(data$depth_factor, data$depth_q, mean))
pred <- predict(model, newdat, type="response")
pred

library(margins)
m <- glm(outcome ~ depth_factor, data = data, family = binomial)
summary(margins(m, at=list(depth_factor=c(mean(data$depth_factor)-sd(data$depth_factor),
                                          mean(data$depth_factor),
                                          mean(data$depth_factor)+sd(data$depth_factor)))))

# Refit just to be safe
model <- glm(outcome ~ depth_factor + sogs_z + corsi_for_z + xgoal_z,
             data = data, family = binomial)

# Get the quartile means again
depth_means <- tapply(data$depth_factor, data$depth_q, mean, na.rm = TRUE)

# Function to set depth to a fixed value, predict for every row, then average
avg_pred_at <- function(depth_val) {
  nd <- data
  nd$depth_factor <- depth_val
  mean(predict(model, newdata = nd, type = "response"), na.rm = TRUE)
}

q_probs <- sapply(as.numeric(depth_means), avg_pred_at)
names(q_probs) <- levels(data$depth_q)
q_probs
q_probs[c(1,4)]      # Q1 vs Q4 average win probs
diff_q4_q1 <- q_probs[4] - q_probs[1]
diff_q4_q1

# This is great. In a given game, if in top quartile of depth win 53%, bottom 46.5%
#What about taems
library(dplyr)

team_summary <- reg_seas %>%
  group_by(teamAbbrev) %>%
  summarise(
    avg_depth = mean(depth_factor, na.rm = TRUE),
    win_rate  = mean(outcome, na.rm = TRUE),
    n_games   = n(),
    .groups = "drop"
  )

team_summary

psych::corr.test(team_summary$avg_depth, team_summary$win_rate)

# This is important because game to game is one thing, but over a season depth is
# a team level thing--did the teams with more depth win more? YES.

# --- Scatterplot of avg depth vs win rate ---
ggplot(team_summary, aes(x = avg_depth, y = win_rate, label = teamAbbrev)) +
  geom_point(color = "steelblue", size = 3) +
  ggrepel::geom_text_repel(size = 3) +
  geom_smooth(method = "lm", se = FALSE, linetype = 2, color = "grey40") +
  labs(
    x = "Average Depth (regular season)",
    y = "Win Rate",
    title = "Team Average Depth vs Win Rate"
  ) +
  theme_minimal(base_size = 12)

# --- Win rates by depth quartile ---
team_summary <- team_summary %>%
  mutate(depth_quartile = ntile(avg_depth, 4))

quartile_summary <- team_summary %>%
  group_by(depth_quartile) %>%
  summarise(
    avg_depth   = mean(avg_depth, na.rm = TRUE),
    mean_winrate = mean(win_rate, na.rm = TRUE),
    n_teams     = n(),
    .groups = "drop"
  )

quartile_summary

ggplot(quartile_summary, aes(x = factor(depth_quartile), y = mean_winrate)) +
  geom_col(fill = "steelblue", alpha = 0.7) +
  geom_text(aes(label = scales::percent(mean_winrate, accuracy = 1)),
            vjust = -0.5) +
  labs(
    x = "Depth Quartile (team avg)",
    y = "Average Win Rate",
    title = "Win Rate by Depth Quartile"
  ) +
  scale_y_continuous(labels = scales::percent_format(accuracy = 1),
                     limits = c(0,1)) +
  theme_minimal(base_size = 12)

# Multilevel logistic model: win ~ depth, clustered by team
mlm <- glmer(outcome ~ depth_factor + (1 | teamAbbrev),
             data = reg_seas,
             family = binomial)

summary(mlm)

library(sjPlot)
library(ggeffects)

sjPlot::plot_model(
  mlm,
  type = "pred",        # predicted probabilities
  terms = "depth_factor", 
  transform = "plogis"  # ensure logistic link is shown as probabilities
) +
  labs(
    x = "Depth (factor score)",
    y = "Predicted Win Probability",
    title = "Predicted Probability of Win by Depth (MLM)"
  )

# Does depth predict depth
library(zoo)

rolling_depth <- data %>%
  arrange(teamAbbrev, game_id) %>%  # make sure it's ordered
  group_by(teamAbbrev) %>%
  mutate(
    depth_rolling10 = rollapply(
      depth_factor,
      width = 10,
      FUN = mean,
      align = "right",
      fill = NA
    )
  ) %>%
  ungroup()

head(rolling_depth, 15)

library(dplyr)
library(tidyr)
library(zoo)

# 1) Lagged 10-game rolling depth per team (uses prior 10 games only)
data_roll <- data %>%
  arrange(teamAbbrev, game_id) %>%
  group_by(teamAbbrev) %>%
  mutate(
    depth_roll10 = rollapply(
      lag(depth_factor),      # prior games only
      width = 10,
      FUN = mean,
      align = "right",
      fill = NA_real_
    )
  ) %>%
  ungroup()

# 2) Keep valid games (exactly two teams, one winner/one loser, both depths available)
games_valid <- data_roll %>%
  group_by(game_id) %>%
  filter(
    n_distinct(teamAbbrev) == 2,
    all(c(0, 1) %in% outcome),
    sum(!is.na(depth_roll10)) == 2
  ) %>%
  ungroup()

# 3) Wide game-level table: winner/loser + their lagged 10g depth
matchups <- games_valid %>%
  transmute(
    game_id,
    team = teamAbbrev,
    outcome,
    depth_roll10
  ) %>%
  mutate(role = if_else(outcome == 1, "winning", "losing")) %>%
  pivot_wider(
    id_cols = game_id,
    names_from = role,
    values_from = c(team, depth_roll10),
    names_sep = "_"
  ) %>%
  rename(
    winning_team = team_winning,
    losing_team  = team_losing,
    winning_depth = depth_roll10_winning,
    losing_depth  = depth_roll10_losing
  ) %>%
  mutate(depth_diff = winning_depth - losing_depth)

# Peek
head(matchups)

library(broom)

# Build long form: both teams in each game
model_data <- matchups %>%
  dplyr::select(game_id, winning_team, losing_team,
         winning_depth, losing_depth) %>%
  tidyr::pivot_longer(
    cols = c(winning_team, losing_team,
             winning_depth, losing_depth),
    names_to = c("role", ".value"),
    names_pattern = "(winning|losing)_(.*)"
  ) %>%
  mutate(outcome = if_else(role == "winning", 1, 0))

# Logistic regression: does team depth predict win?
fit <- glm(outcome ~ depth, data = model_data, family = binomial)

summary(fit)
broom::tidy(fit, exponentiate = TRUE, conf.int = TRUE)  # odds ratios


# Does depth predict depth
depth_predict <- data_roll %>%
  arrange(teamAbbrev, game_id) %>%
  group_by(teamAbbrev) %>%
  mutate(next_depth = lead(depth_factor)) %>%
  ungroup() %>%
  filter(!is.na(depth10), !is.na(next_depth))

# Simple regression: does 10g rolling avg predict next game's depth?
fit_depth <- lm(next_depth ~ depth10, data = depth_predict)
summary(fit_depth)

# Optional: add plot
ggplot(depth_predict, aes(x = depth10, y = next_depth)) +
  geom_point(alpha = 0.3) +
  geom_smooth(method = "lm", se = TRUE, color = "steelblue") +
  labs(
    x = "10-game rolling average depth (lagged)",
    y = "Next game depth",
    title = "Does rolling depth predict next game’s depth?"
  ) +
  theme_minimal(base_size = 12)

# Depth differential
# FIX: bring depth_diff from wide table before pivot
matchups2 <- matchups %>%
  mutate(depth_diff = winning_depth - losing_depth)

# Now go long, keeping depth_diff attached
model_data <- matchups2 %>%
  tidyr::pivot_longer(
    cols = c(winning_team, losing_team,
             winning_depth, losing_depth),
    names_to = c("role", ".value"),
    names_pattern = "(winning|losing)_(.*)"
  ) %>%
  mutate(outcome = if_else(role == "winning", 1, 0))

# Logistic regression: does bigger depth_diff make the deeper team more likely to win?
fit <- glm(outcome ~ depth*depth_diff, data = model_data, family = binomial)


fit <- glm(outcome ~ depth_diff, data = model_data, family = binomial)
summary(fit)







library(dplyr)
library(tidyr)
library(zoo)
library(broom)

# 0) Start from your per-team, per-game data with depth_factor
# Build lagged 10-game rolling depth (no leakage)
data_roll <- data %>%
  arrange(teamAbbrev, game_id) %>%
  group_by(teamAbbrev) %>%
  mutate(depth10 = rollapply(lag(depth_factor), 10, mean, align = "right",
                             fill = NA_real_)) %>%
  ungroup()

# 1) Keep only valid 2-team games with both lagged depths present
games2 <- data_roll %>%
  group_by(game_id) %>%
  filter(n() == 2, all(c(0,1) %in% outcome), !any(is.na(depth10))) %>%
  ungroup() %>%
  dplyr::select(game_id, teamAbbrev, outcome, depth10)

# 2) Self-join within game to attach opponent depth
pairs <- games2 %>%
  left_join(
    games2 %>%
      dplyr::select(game_id, opp_team = teamAbbrev, opp_outcome = outcome, opp_depth10 = depth10),
    by = "game_id"
  ) %>%
  filter(teamAbbrev != opp_team) %>%    # drop self-rows
  mutate(edge = depth10 - opp_depth10)  # signed depth advantage from THIS row's perspective

# Sanity check: within each game, the two rows' edges should be negatives of each other
# pairs %>% group_by(game_id) %>% summarise(sum_edge = sum(edge))  # ~0

# 3A) Simple logistic regression: win ~ signed depth edge
fit_glm <- glm(outcome ~ edge, data = pairs, family = binomial)
summary(fit_glm, exponentiate = TRUE, conf.int = TRUE)
broom::tidy(fit_glm, exponentiate = TRUE, conf.int = TRUE)  # odds ratios
# OR for `edge` = change in odds of winning per 1 SD edge in depth (since depth_factor was z-scored)

# 3B) (Recommended) Conditional logit: pairwise comparison within each game
# This controls for any game-specific intercept by stratifying on game_id
# install.packages("survival") if needed
library(survival)
fit_clogit <- clogit(outcome ~ edge + strata(game_id), data = pairs)
summary(fit_clogit)
broom::tidy(fit_clogit, exponentiate = TRUE, conf.int = TRUE) 
# exp(coef) is the odds ratio per 1 SD edge, with pairing fully controlled

# slope from clogit
b1 <- coef(fit_clogit)[["edge"]]

inv_logit <- function(x) 1 / (1 + exp(-x))

# Range of edges, say -2 to +2 SD
newdat <- data.frame(
  edge = seq(-2, 2, by = 0.1)
)

# Predicted win probabilities
newdat$pred <- inv_logit(b1 * newdat$edge)

ggplot(newdat, aes(x = edge, y = pred)) +
  geom_line(size = 1.2, color = "steelblue") +
  geom_hline(yintercept = 0.5, linetype = "dashed", color = "grey50") +
  labs(
    x = "Depth edge (team – opponent, in SDs)",
    y = "Predicted win probability",
    title = "Conditional logit: win probability vs depth edge"
  ) +
  theme_minimal(base_size = 13)
