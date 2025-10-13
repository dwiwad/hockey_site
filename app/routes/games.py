from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.nhl.service import fetch_game_pbp, fetch_game_box, fetch_moneypuck_player_xg_csv, fetch_game_shifts
from app.nhl.parsers.sogs import sog_by_team
from app.nhl.parsers.hits import hits_by_team
from app.nhl.parsers.rosters import roster_by_team
from app.nhl.parsers.scoreboard import scoreboard
from app.nhl.parsers.depth import shot_depth_from_pbp, cf_depth_from_pbp, xgoal_depth_from_players, toi_depth_from_shifts

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
    shifts = fetch_game_shifts(game_id, season, ttl_seconds=5)

    rosters = roster_by_team(pbp)
    shot_depth_payload = shot_depth_from_pbp(pbp, rosters) 
    cf_depth_payload = cf_depth_from_pbp(pbp, rosters)
    toi_depth_payload = toi_depth_from_shifts(pbp, shifts, rosters)

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
         }
    )

@games_router.get("/dashboard/games/{season}/{game_id}/depth")
async def game_depth_breakdown(request: Request, season: int, game_id: int):
    # Fetch same data as game_dashboard
        # Service Functions to actually get and store data
    pbp = fetch_game_pbp(game_id, season, ttl_seconds=5)
    box = fetch_game_box(game_id, season, ttl_seconds=5)
    xg = fetch_moneypuck_player_xg_csv(game_id, season, ttl_seconds=5)
    shifts = fetch_game_shifts(game_id, season, ttl_seconds=5)

    rosters = roster_by_team(pbp)
    shot_depth_payload = shot_depth_from_pbp(pbp, rosters) 
    cf_depth_payload = cf_depth_from_pbp(pbp, rosters)
    toi_depth_payload = toi_depth_from_shifts(pbp, shifts, rosters)

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
         }
    )