from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.nhl.service import fetch_game_pbp, fetch_game_box
from app.nhl.parsers.sogs import sog_by_team
from app.nhl.parsers.hits import hits_by_team
from app.nhl.parsers.scoreboard import scoreboard

# Anchor templates to project root so it works no matter where you run uvicorn
# PROJECT_ROOT = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory="templates")

games_router = APIRouter()

@games_router.get("/dashboard/games/{season}/{game_id}", response_class=HTMLResponse)
async def game_dashboard(request: Request, season: int, game_id: int, fresh: bool = False):
    pbp = fetch_game_pbp(game_id, season, ttl_seconds=5)
    box = fetch_game_box(game_id, season, ttl_seconds=5)
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
         "box": boxscore,
         "clock": clock, 
         }
    )
