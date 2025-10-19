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
        # Extract Gini coefficients
        home_sog_gini = shot_depth_payload['home']['ineq']
        away_sog_gini = shot_depth_payload['away']['ineq']

        home_cf_gini = cf_depth_payload['cf_home']['ineq']
        away_cf_gini = cf_depth_payload['cf_away']['ineq']

        home_xg_gini = xg_depth_payload['xg_home']['ineq']
        away_xg_gini = xg_depth_payload['xg_away']['ineq']

        home_toi_gini = toi_depth_payload['toi_home']['ineq']
        away_toi_gini = toi_depth_payload['toi_away']['ineq']

        # Calculate TDI
        home_tdi, home_raw_tdi = calculate_tdi(home_cf_gini, home_sog_gini, home_toi_gini, home_xg_gini)
        away_tdi, away_raw_tdi = calculate_tdi(away_cf_gini, away_sog_gini, away_toi_gini, away_xg_gini)

    else:
        # Not enough data yet (pregame or very early in game)
        home_tdi = None
        away_tdi = None
        home_raw_tdi = None
        away_raw_tdi = None

    # Bar visualization using weighted raw depths (not z-scored)
    if home_tdi is not None and away_tdi is not None:
        # Use raw depths (not z-scored) weighted by factor coefficients
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
    else:
        home_tdi_pct = 50.0
        away_tdi_pct = 50.0

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
         "home_weighted_depth": home_weighted_depth if home_tdi is not None else None,
         "away_weighted_depth": away_weighted_depth if home_tdi is not None else None,
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