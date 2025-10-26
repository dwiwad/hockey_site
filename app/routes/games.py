from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.nhl.service import fetch_game_pbp, fetch_game_box, fetch_moneypuck_player_xg_csv
from app.nhl.parsers.sogs import sog_by_team
from app.nhl.parsers.hits import hits_by_team
from app.nhl.parsers.rosters import roster_by_team
from app.nhl.parsers.scoreboard import scoreboard
from app.nhl.parsers.depth import shot_depth_from_pbp, cf_depth_from_pbp, xgoal_depth_from_players, toi_depth_from_boxscore, calculate_tdi
from app.nhl.models.depth_sem_config import FACTOR_SCORE_COEFFICIENTS
from app.config.team_colors import TEAM_COLORS

# Anchor templates to project root so it works no matter where you run uvicorn
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory="templates")

games_router = APIRouter()

@games_router.get("/dashboard/games/{season}/{game_id}", response_class=HTMLResponse)
async def game_dashboard(request: Request, season: int, game_id: int, fresh: bool = False):
    # Service Functions to actually get and store data
    pbp = fetch_game_pbp(game_id, season, ttl_seconds=5)
    box = fetch_game_box(game_id, season, ttl_seconds=5)
    xg = fetch_moneypuck_player_xg_csv(game_id, season, ttl_seconds=5)

    rosters = roster_by_team(pbp)
    shot_depth_payload = shot_depth_from_pbp(pbp, rosters) 
    cf_depth_payload = cf_depth_from_pbp(pbp, rosters)
    toi_depth_payload = toi_depth_from_boxscore(pbp, box, rosters)
    xg_depth_payload = xgoal_depth_from_players(
    pbp=pbp,
    roster_rows=rosters,
    xg_df=xg,
    situation="all",        
    adjusted=False,         
    include_goalies=False,
    )

    # Check if we have enough data to calculate TDI
    has_shot_data = not shot_depth_payload.get('no_shots', True)
    has_cf_data = not cf_depth_payload.get('no_shots', True)
    has_xg_data = not xg_depth_payload.get('no_xg', True)
    has_toi_data = not toi_depth_payload.get('no_toi', True)

    if has_shot_data and has_cf_data and has_xg_data and has_toi_data:
        # Extract live Gini coefficients from game
        home_sog_gini = shot_depth_payload['home']['ineq']
        away_sog_gini = shot_depth_payload['away']['ineq']

        home_cf_gini = cf_depth_payload['cf_home']['ineq']
        away_cf_gini = cf_depth_payload['cf_away']['ineq']

        home_xg_gini = xg_depth_payload['xg_home']['ineq']
        away_xg_gini = xg_depth_payload['xg_away']['ineq']

        home_toi_gini = toi_depth_payload['toi_home']['ineq']
        away_toi_gini = toi_depth_payload['toi_away']['ineq']

        # BAYESIAN BLENDING: Check if we should blend with priors
        boxscore = scoreboard(pbp)
        clock_data = box.get("clock", {}) or {}

        # Calculate time elapsed (in minutes)
        if boxscore.get('gameState') not in ('FINAL', 'OFF', 'FUT', 'PRE'):
            # Game is live - consider blending
            period = boxscore.get('period', 1)
            time_remaining = clock_data.get('timeRemaining', '20:00')

            # Parse time remaining (format: "MM:SS")
            try:
                mins, secs = time_remaining.split(':')
                time_remaining_mins = int(mins) + int(secs) / 60
            except:
                time_remaining_mins = 20.0

            # Calculate elapsed time
            if period == 1:
                time_elapsed = 20 - time_remaining_mins
            elif period == 2:
                time_elapsed = 20 + (20 - time_remaining_mins)
            elif period == 3:
                time_elapsed = 40 + (20 - time_remaining_mins)
            else:  # OT or later
                time_elapsed = 60

            # Get shot counts for each team
            home_shots = shot_depth_payload['home']['total_shots']
            away_shots = shot_depth_payload['away']['total_shots']

            # Blending thresholds
            SHOTS_THRESHOLD = 15.0
            TIME_THRESHOLD = 40.0

            # Calculate live weights for each team
            shots_weight_home = min(1.0, home_shots / SHOTS_THRESHOLD)
            shots_weight_away = min(1.0, away_shots / SHOTS_THRESHOLD)
            time_weight = min(1.0, time_elapsed / TIME_THRESHOLD)

            weight_live_home = max(shots_weight_home, time_weight)
            weight_live_away = max(shots_weight_away, time_weight)

            # Load prior Ginis from rolling averages
            from app.nhl.league_stats import get_current_rolling_averages
            rolling_avgs = get_current_rolling_averages(season=2025)

            if rolling_avgs and weight_live_home < 1.0:  # Only blend if not full confidence yet
                data = sog_by_team(pbp)
                home_data = rolling_avgs.get(data['home_abbrev'])
                away_data = rolling_avgs.get(data['away_abbrev'])

                if home_data and away_data:
                    # Blend home team Ginis
                    weight_prior_home = 1.0 - weight_live_home
                    home_sog_gini = (weight_prior_home * home_data['shot_gini']) + (weight_live_home * home_sog_gini)
                    home_cf_gini = (weight_prior_home * home_data['cf_gini']) + (weight_live_home * home_cf_gini)
                    home_xg_gini = (weight_prior_home * home_data['xg_gini']) + (weight_live_home * home_xg_gini)
                    home_toi_gini = (weight_prior_home * home_data['toi_gini']) + (weight_live_home * home_toi_gini)

                    # Blend away team Ginis
                    weight_prior_away = 1.0 - weight_live_away
                    away_sog_gini = (weight_prior_away * away_data['shot_gini']) + (weight_live_away * away_sog_gini)
                    away_cf_gini = (weight_prior_away * away_data['cf_gini']) + (weight_live_away * away_cf_gini)
                    away_xg_gini = (weight_prior_away * away_data['xg_gini']) + (weight_live_away * away_xg_gini)
                    away_toi_gini = (weight_prior_away * away_data['toi_gini']) + (weight_live_away * away_toi_gini)

        # Calculate TDI from (possibly blended) Ginis
        home_tdi, home_raw_tdi = calculate_tdi(home_cf_gini, home_sog_gini, home_toi_gini, home_xg_gini)
        away_tdi, away_raw_tdi = calculate_tdi(away_cf_gini, away_sog_gini, away_toi_gini, away_xg_gini)

    else:
        # Not enough data yet - show priors if available
        boxscore = scoreboard(pbp)

        if boxscore.get('gameState') in ('FUT', 'PRE', 'LIVE', 'CRIT'):
            # Game hasn't started OR just started - use rolling averages
            from app.nhl.league_stats import get_current_rolling_averages
            rolling_avgs = get_current_rolling_averages(season=2025)

            if rolling_avgs:
                data = sog_by_team(pbp)
                home_abbrev = data['home_abbrev']
                away_abbrev = data['away_abbrev']

                home_data = rolling_avgs.get(home_abbrev)
                away_data = rolling_avgs.get(away_abbrev)

                if home_data and away_data:
                    # Extract weighted_depth from nested structure
                    home_weighted_depth = home_data['weighted_depth']
                    away_weighted_depth = away_data['weighted_depth']

                    total = home_weighted_depth + away_weighted_depth
                    home_tdi_pct = round(100.0 * (home_weighted_depth / total), 1)
                    away_tdi_pct = round(100.0 - home_tdi_pct, 1)
                else:
                    home_weighted_depth = None
                    away_weighted_depth = None
                    home_tdi_pct = 50.0
                    away_tdi_pct = 50.0
            else:
                home_weighted_depth = None
                away_weighted_depth = None
                home_tdi_pct = 50.0
                away_tdi_pct = 50.0
        else:
            # Shouldn't happen, but fallback to N/A
            home_weighted_depth = None
            away_weighted_depth = None
            home_tdi_pct = 50.0
            away_tdi_pct = 50.0

        home_tdi = None
        away_tdi = None
        home_raw_tdi = None
        away_raw_tdi = None

    # Bar visualization using weighted raw depths (not z-scored)
    if home_tdi is not None and away_tdi is not None:
        # Live or finished game - use calculated weighted depths from (blended) Ginis
        home_weighted_depth = (
            FACTOR_SCORE_COEFFICIENTS['cf_depth_z'] * (1 - home_cf_gini) +
            FACTOR_SCORE_COEFFICIENTS['sog_depth_z'] * (1 - home_sog_gini) +
            FACTOR_SCORE_COEFFICIENTS['toi_depth_z'] * (1 - home_toi_gini) +
            FACTOR_SCORE_COEFFICIENTS['xgoal_depth_z'] * (1 - home_xg_gini)
        )

        away_weighted_depth = (
            FACTOR_SCORE_COEFFICIENTS['cf_depth_z'] * (1 - away_cf_gini) +
            FACTOR_SCORE_COEFFICIENTS['sog_depth_z'] * (1 - away_sog_gini) +
            FACTOR_SCORE_COEFFICIENTS['toi_depth_z'] * (1 - away_toi_gini) +
            FACTOR_SCORE_COEFFICIENTS['xgoal_depth_z'] * (1 - away_xg_gini)
        )

        total = home_weighted_depth + away_weighted_depth
        home_tdi_pct = round(100.0 * (home_weighted_depth / total), 1)
        away_tdi_pct = round(100.0 - home_tdi_pct, 1)

    # Parsers to actually work with the data
    data = sog_by_team(pbp)
    hits = hits_by_team(pbp)
    boxscore = scoreboard(pbp)
    clock_data = box.get("clock", {}) or {}
    clock = {
    "inIntermission": clock_data.get("inIntermission"),
    "timeRemaining": clock_data.get("timeRemaining"),
    "running": clock_data.get("running")
    }

    return templates.TemplateResponse(
        "game_dashboard.html",
        {"request": request, 
         "game_id": game_id, 
         "season": season,
         "sog": data, 
         "hits": hits,
         "xg": xg,
         "box": boxscore,
         "clock": clock,
         "rosters": rosters,
         "shot_depth_payload": shot_depth_payload,
         "cf_depth_payload": cf_depth_payload,
         "xg_depth_payload": xg_depth_payload,
         "toi_depth_payload": toi_depth_payload,
         "home_tdi": home_tdi,
         "away_tdi": away_tdi,
         "home_tdi_pct": home_tdi_pct,
         "away_tdi_pct": away_tdi_pct,
         "home_weighted_depth": home_weighted_depth,
         "away_weighted_depth": away_weighted_depth,
         "away_color": TEAM_COLORS.get(data['away_abbrev'], '#999999'),
        "home_color": TEAM_COLORS.get(data['home_abbrev'], '#999999'),
        }
    )

@games_router.get("/dashboard/games/{season}/{game_id}/depth")
async def game_depth_breakdown(request: Request, season: int, game_id: int):
    # Fetch same data as game_dashboard
    # Service Functions to actually get and store data
    pbp = fetch_game_pbp(game_id, season, ttl_seconds=5)
    box = fetch_game_box(game_id, season, ttl_seconds=5)
    xg = fetch_moneypuck_player_xg_csv(game_id, season, ttl_seconds=5)

    rosters = roster_by_team(pbp)
    shot_depth_payload = shot_depth_from_pbp(pbp, rosters) 
    cf_depth_payload = cf_depth_from_pbp(pbp, rosters)
    toi_depth_payload = toi_depth_from_boxscore(pbp, box, rosters)

    xg_depth_payload = xgoal_depth_from_players(
        pbp=pbp,
        roster_rows=rosters,
        xg_df=xg,
        situation="all",        
        adjusted=False,         
        include_goalies=False,
    )

    # BAYESIAN BLENDING: Blend each metric independently
    boxscore = scoreboard(pbp)
    clock_data = box.get("clock", {}) or {}

    # Check if we should blend with priors
    has_shot_data = not shot_depth_payload.get('no_shots', True)
    has_cf_data = not cf_depth_payload.get('no_shots', True)
    has_xg_data = not xg_depth_payload.get('no_xg', True)
    has_toi_data = not toi_depth_payload.get('no_toi', True)

    # If no data AND game hasn't started, use priors
    if not (has_shot_data and has_cf_data and has_xg_data and has_toi_data):
        if boxscore.get('gameState') in ('FUT', 'PRE'):
            # Load priors to display
            from app.nhl.league_stats import get_current_rolling_averages
            rolling_avgs = get_current_rolling_averages(season=2025)

            if rolling_avgs:
                data = sog_by_team(pbp)
                home_data = rolling_avgs.get(data['home_abbrev'])
                away_data = rolling_avgs.get(data['away_abbrev'])

                if home_data and away_data:
                    # Populate shot depth with priors
                    home_shot_depth = 1 - home_data['shot_gini']
                    away_shot_depth = 1 - away_data['shot_gini']
                    shot_total = home_shot_depth + away_shot_depth
                    shot_depth_payload = {
                        'no_shots': False,
                        'home': {'team': data['home_abbrev'], 'depth': 1 - home_data['shot_gini'], 'ineq': home_data['shot_gini'], 'total_shots': 0},
                        'away': {'team': data['away_abbrev'], 'depth': 1 - away_data['shot_gini'], 'ineq': away_data['shot_gini'], 'total_shots': 0},
                        'depth_share': {
                            'away_pct': round(100.0 * (away_shot_depth / shot_total), 1),
                            'home_pct': round(100.0 * (home_shot_depth / shot_total), 1)
                        },
                        'shots': {'home': {}, 'away': {}}
                    }

                    # Populate CF depth with priors
                    home_cf_depth = 1 - home_data['cf_gini']
                    away_cf_depth = 1 - away_data['cf_gini']
                    cf_total = home_cf_depth + away_cf_depth
                    cf_depth_payload = {
                        'no_shots': False,
                        'cf_home': {'team': data['home_abbrev'], 'depth': 1 - home_data['cf_gini'], 'ineq': home_data['cf_gini'], 'total_shots': 0},
                        'cf_away': {'team': data['away_abbrev'], 'depth': 1 - away_data['cf_gini'], 'ineq': away_data['cf_gini'], 'total_shots': 0},
                        'cf_depth_share': {
                            'away_pct': round(100.0 * (away_cf_depth / cf_total), 1),
                            'home_pct': round(100.0 * (home_cf_depth / cf_total), 1)
                        },
                        'cf': {'cf_home': {}, 'cf_away': {}}
                    }

                    # Populate xG depth with priors
                    home_xg_depth = 1 - home_data['xg_gini']
                    away_xg_depth = 1 - away_data['xg_gini']
                    xg_total = home_xg_depth + away_xg_depth
                    xg_depth_payload = {
                        'no_xg': False,
                        'xg_home': {'team': data['home_abbrev'], 'depth': 1 - home_data['xg_gini'], 'ineq': home_data['xg_gini'], 'total_xg': 0.0},
                        'xg_away': {'team': data['away_abbrev'], 'depth': 1 - away_data['xg_gini'], 'ineq': away_data['xg_gini'], 'total_xg': 0.0},
                        'xg_depth_share': {
                            'away_pct': round(100.0 * (away_xg_depth / xg_total), 1),
                            'home_pct': round(100.0 * (home_xg_depth / xg_total), 1)
                        },
                        'xg': {'xg_home': {}, 'xg_away': {}}
                    }

                    # Populate TOI depth with priors
                    home_toi_depth = 1 - home_data['toi_gini']
                    away_toi_depth = 1 - away_data['toi_gini']
                    toi_total = home_toi_depth + away_toi_depth
                    toi_depth_payload = {
                        'no_toi': False,
                        'toi_home': {'team': data['home_abbrev'], 'depth': 1 - home_data['toi_gini'], 'ineq': home_data['toi_gini'], 'total_seconds': 0},
                        'toi_away': {'team': data['away_abbrev'], 'depth': 1 - away_data['toi_gini'], 'ineq': away_data['toi_gini'], 'total_seconds': 0},
                        'toi_depth_share': {
                            'away_pct': round(100.0 * (away_toi_depth / toi_total), 1),
                            'home_pct': round(100.0 * (home_toi_depth / toi_total), 1)
                        }
                    }

    if boxscore.get('gameState') not in ('FINAL', 'OFF', 'FUT', 'PRE'):
        # Game is live - calculate blending weights
        period = boxscore.get('period', 1)
        time_remaining = clock_data.get('timeRemaining', '20:00')

        # Parse time remaining
        try:
            mins, secs = time_remaining.split(':')
            time_remaining_mins = int(mins) + int(secs) / 60
        except:
            time_remaining_mins = 20.0

        # Calculate elapsed time
        if period == 1:
            time_elapsed = 20 - time_remaining_mins
        elif period == 2:
            time_elapsed = 20 + (20 - time_remaining_mins)
        elif period == 3:
            time_elapsed = 40 + (20 - time_remaining_mins)
        else:
            time_elapsed = 60

        # Blending thresholds
        SHOTS_THRESHOLD = 15.0
        TIME_THRESHOLD = 40.0
        time_weight = min(1.0, time_elapsed / TIME_THRESHOLD)

        # Load priors
        from app.nhl.league_stats import get_current_rolling_averages
        rolling_avgs = get_current_rolling_averages(season=2025)

        if rolling_avgs:
            data = sog_by_team(pbp)
            home_data = rolling_avgs.get(data['home_abbrev'])
            away_data = rolling_avgs.get(data['away_abbrev'])

            if home_data and away_data:
                # BLEND SHOT DEPTH
                if has_shot_data:
                    home_shots = shot_depth_payload['home']['total_shots']
                    away_shots = shot_depth_payload['away']['total_shots']

                    weight_live_home = max(min(1.0, home_shots / SHOTS_THRESHOLD), time_weight)
                    weight_live_away = max(min(1.0, away_shots / SHOTS_THRESHOLD), time_weight)

                    if weight_live_home < 1.0:
                        weight_prior_home = 1.0 - weight_live_home
                        home_shot_gini = shot_depth_payload['home']['ineq']
                        blended_gini = (weight_prior_home * home_data['shot_gini']) + (weight_live_home * home_shot_gini)
                        shot_depth_payload['home']['ineq'] = blended_gini
                        shot_depth_payload['home']['depth'] = 1 - blended_gini

                    if weight_live_away < 1.0:
                        weight_prior_away = 1.0 - weight_live_away
                        away_shot_gini = shot_depth_payload['away']['ineq']
                        blended_gini = (weight_prior_away * away_data['shot_gini']) + (weight_live_away * away_shot_gini)
                        shot_depth_payload['away']['ineq'] = blended_gini
                        shot_depth_payload['away']['depth'] = 1 - blended_gini

                # BLEND CF DEPTH
                if has_cf_data:
                    home_cf = cf_depth_payload['cf_home']['total_shots']
                    away_cf = cf_depth_payload['cf_away']['total_shots']

                    weight_live_home = max(min(1.0, home_cf / SHOTS_THRESHOLD), time_weight)
                    weight_live_away = max(min(1.0, away_cf / SHOTS_THRESHOLD), time_weight)

                    if weight_live_home < 1.0:
                        weight_prior_home = 1.0 - weight_live_home
                        home_cf_gini = cf_depth_payload['cf_home']['ineq']
                        blended_gini = (weight_prior_home * home_data['cf_gini']) + (weight_live_home * home_cf_gini)
                        cf_depth_payload['cf_home']['ineq'] = blended_gini
                        cf_depth_payload['cf_home']['depth'] = 1 - blended_gini

                    if weight_live_away < 1.0:
                        weight_prior_away = 1.0 - weight_live_away
                        away_cf_gini = cf_depth_payload['cf_away']['ineq']
                        blended_gini = (weight_prior_away * away_data['cf_gini']) + (weight_live_away * away_cf_gini)
                        cf_depth_payload['cf_away']['ineq'] = blended_gini
                        cf_depth_payload['cf_away']['depth'] = 1 - blended_gini

                # BLEND XG DEPTH
                if has_xg_data:
                    home_shots = shot_depth_payload['home']['total_shots']  # Use shots, not xG total
                    away_shots = shot_depth_payload['away']['total_shots']

                    weight_live_home = max(min(1.0, home_shots / SHOTS_THRESHOLD), time_weight)
                    weight_live_away = max(min(1.0, away_shots / SHOTS_THRESHOLD), time_weight)

                    if weight_live_home < 1.0:
                        weight_prior_home = 1.0 - weight_live_home
                        home_xg_gini = xg_depth_payload['xg_home']['ineq']
                        blended_gini = (weight_prior_home * home_data['xg_gini']) + (weight_live_home * home_xg_gini)
                        xg_depth_payload['xg_home']['ineq'] = blended_gini
                        xg_depth_payload['xg_home']['depth'] = 1 - blended_gini

                    if weight_live_away < 1.0:
                        weight_prior_away = 1.0 - weight_live_away
                        away_xg_gini = xg_depth_payload['xg_away']['ineq']
                        blended_gini = (weight_prior_away * away_data['xg_gini']) + (weight_live_away * away_xg_gini)
                        xg_depth_payload['xg_away']['ineq'] = blended_gini
                        xg_depth_payload['xg_away']['depth'] = 1 - blended_gini

                # BLEND TOI DEPTH (time-based only)
                if has_toi_data and time_weight < 1.0:
                    weight_prior = 1.0 - time_weight

                    home_toi_gini = toi_depth_payload['toi_home']['ineq']
                    blended_gini = (weight_prior * home_data['toi_gini']) + (time_weight * home_toi_gini)
                    toi_depth_payload['toi_home']['ineq'] = blended_gini
                    toi_depth_payload['toi_home']['depth'] = 1 - blended_gini

                    away_toi_gini = toi_depth_payload['toi_away']['ineq']
                    blended_gini = (weight_prior * away_data['toi_gini']) + (time_weight * away_toi_gini)
                    toi_depth_payload['toi_away']['ineq'] = blended_gini
                    toi_depth_payload['toi_away']['depth'] = 1 - blended_gini

    # Parsers to actually work with the data
    data = sog_by_team(pbp)
    hits = hits_by_team(pbp)
    boxscore = scoreboard(pbp)
    clock_data = box.get("clock", {}) or {}
    clock = {
    "inIntermission": clock_data.get("inIntermission"),
    "timeRemaining": clock_data.get("timeRemaining"),
    "running": clock_data.get("running")
    }

    return templates.TemplateResponse(
        "depth.html",
        {"request": request, 
         "game_id": game_id, 
         "season": season,
         "sog": data, 
         "hits": hits,
         "xg": xg,
         "box": boxscore,
         "clock": clock,
         "rosters": rosters,
         "shot_depth_payload": shot_depth_payload,
         "cf_depth_payload": cf_depth_payload,
         "xg_depth_payload": xg_depth_payload,
         "toi_depth_payload": toi_depth_payload,
         "away_color": TEAM_COLORS.get(data['away_abbrev'], '#999999'),
        "home_color": TEAM_COLORS.get(data['home_abbrev'], '#999999'),
         }
    )

@games_router.get("/dashboard/games/{season}/{game_id}/depth/timeseries")
async def game_depth_timeseries(request: Request, season: int, game_id: int):
    """
    Return time series data for live depth tracking.
    Returns JSON with timestamps and depth values for Plotly visualization.
    """
    import pandas as pd
    import s3fs

    s3_path = f"s3://hockey-decoded/live_game_depth/season={season}/game_id={game_id}.parquet"

    try:
        # Read the live tracking file
        df = pd.read_parquet(s3_path, engine='fastparquet')

        if df.empty:
            return {
                "status": "no_data",
                "home_abbrev": None,
                "away_abbrev": None,
                "timestamps": [],
                "home_weighted_depth": [],
                "away_weighted_depth": [],
                "home_sog_depth": [],
                "away_sog_depth": [],
                "home_cf_depth": [],
                "away_cf_depth": [],
                "home_xg_depth": [],
                "away_xg_depth": [],
                "home_toi_depth": [],
                "away_toi_depth": []
            }

        # Sort by timestamp
        df = df.sort_values('timestamp')

        # Calculate game minute from period and time_remaining
        def calc_game_minute(row):
            period = row['period']
            time_remaining = row['time_remaining']

            if not time_remaining or pd.isna(time_remaining):
                return None

            try:
                mins, secs = str(time_remaining).split(':')
                time_remaining_mins = int(mins) + int(secs) / 60
            except:
                time_remaining_mins = 20.0

            # Calculate elapsed time in this period
            elapsed_in_period = 20 - time_remaining_mins

            # Add minutes from previous periods
            if period == 1:
                return elapsed_in_period
            elif period == 2:
                return 20 + elapsed_in_period
            elif period == 3:
                return 40 + elapsed_in_period
            else:  # OT
                return 60 + elapsed_in_period

        df['game_minute'] = df.apply(calc_game_minute, axis=1)

        # Get team abbreviations
        home_abbrev = df['home_abbrev'].iloc[0]
        away_abbrev = df['away_abbrev'].iloc[0]

        # Convert timestamps to strings (ISO format for JavaScript)
        timestamps = df['timestamp'].dt.strftime('%Y-%m-%dT%H:%M:%S').tolist()

        # Prepare data for Plotly
        data = {
            "status": "success",
            "home_abbrev": home_abbrev,
            "away_abbrev": away_abbrev,
            "game_minutes": df['game_minute'].tolist(),
            "timestamps": timestamps,
            "home_weighted_depth": df['home_weighted_depth'].tolist(),
            "away_weighted_depth": df['away_weighted_depth'].tolist(),
            "home_sog_depth": df['home_sog_depth'].tolist(),
            "away_sog_depth": df['away_sog_depth'].tolist(),
            "home_cf_depth": df['home_cf_depth'].tolist(),
            "away_cf_depth": df['away_cf_depth'].tolist(),
            "home_xg_depth": df['home_xg_depth'].tolist(),
            "away_xg_depth": df['away_xg_depth'].tolist(),
            "home_toi_depth": df['home_toi_depth'].tolist(),
            "away_toi_depth": df['away_toi_depth'].tolist()
        }

        return data
    
    except FileNotFoundError:
        return {
            "status": "no_data",
            "home_abbrev": None,
            "away_abbrev": None,
            "timestamps": [],
            "home_weighted_depth": [],
            "away_weighted_depth": []
        }
    except Exception as e:
        logger.error(f"Error reading live depth timeseries: {e}")
        return {
            "status": "error",
            "message": str(e)
        }