from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.nhl.get_todays_games import get_todays_games

# Tell Jinja where to find the html
templates = Jinja2Templates(directory = "templates")
dashboard_router = APIRouter()


# -----------------------------------------------------------------------
# Route: Dashboard page ('/dashboard')
# Loads templates/dashboard.html
# -----------------------------------------------------------------------

@dashboard_router.get("/dashboard", response_class = HTMLResponse)
async def dashboard(request: Request):
    games_today_df = get_todays_games()
    games_today = games_today_df.to_dict(orient="records")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "games_today": games_today
        })
