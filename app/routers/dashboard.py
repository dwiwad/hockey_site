from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GameData

router = APIRouter(
    prefix="/dashboard",
    tags=["dashboard", "live-data"]
)

templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def dashboard_index(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )

@router.get("/live-games", response_class=HTMLResponse)
async def live_games_dashboard(request: Request, db: Session = Depends(get_db)):
    """Live games dashboard - pulls from database"""
    # Get live and recent games
    live_games = db.query(GameData).filter(
        GameData.status.in_(["live", "scheduled"])
    ).order_by(GameData.date.desc()).limit(10).all()
    
    return templates.TemplateResponse(
        "dashboard/live_games.html",
        {"request": request, "games": live_games}
    )

@router.get("/player-heatmap", response_class=HTMLResponse)
async def player_heatmap_dashboard(request: Request):
    """Historical player shot heatmap explorer"""
    return templates.TemplateResponse(
        "dashboard/player_heatmap.html",
        {"request": request}
    )

# API endpoints for AJAX calls
@router.get("/api/live-scores")
async def get_live_scores(db: Session = Depends(get_db)):
    """API endpoint for live score updates"""
    live_games = db.query(GameData).filter(
        GameData.status == "live"
    ).all()
    
    return {
        "games": [
            {
                "game_id": game.game_id,
                "home_team": game.home_team,
                "away_team": game.away_team,
                "home_score": game.home_score,
                "away_score": game.away_score,
                "status": game.status
            }
            for game in live_games
        ]
    }