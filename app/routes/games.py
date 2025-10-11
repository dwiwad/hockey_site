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
from app.nhl.parsers.depth import shot_depth_from_pbp, cf_depth_from_pbp, xgoal_depth_from_players

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

    xg_depth_payload = xgoal_depth_from_players(
        pbp=pbp,
        roster_rows=rosters,
        xg_df=xg,
        situation="all",        # or "5on5"
        adjusted=False,         # True for flurry/score/venue adjusted if available
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
         }
    )
