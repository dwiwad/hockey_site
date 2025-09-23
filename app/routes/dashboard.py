from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from app.nhl.get_todays_games import get_games_for_date

# Tell Jinja where to find the html
templates = Jinja2Templates(directory = "templates")
dashboard_router = APIRouter()

TZ = ZoneInfo("America/Toronto")

def parse_or_today(date_str: str | None) -> date:
    if not date_str:
        return datetime.now(TZ).date()
    return date.fromisoformat(date_str) 

# -----------------------------------------------------------------------
# Route: Dashboard page ('/dashboard')
# Loads templates/dashboard.html
# -----------------------------------------------------------------------

@dashboard_router.get("/dashboard", response_class = HTMLResponse)
async def dashboard(request: Request, date_str: str | None = Query(default=None, alias="date")):
    d = parse_or_today(date_str)

    # If your getter only returns *today’s* games, add a date-aware helper later.
    # For now: if d != today, you can call a more general function (recommended),
    # but to keep this minimal, pretend get_todays_games handles the given date.
    games_today_df = get_games_for_date(d)  # change your function to accept a `date` arg
    games_today = games_today_df.to_dict(orient="records")

    prev_day = (d - timedelta(days=1)).isoformat()
    next_day = (d + timedelta(days=1)).isoformat()
    is_today = (d == datetime.now(TZ).date())
    pretty_date = d.strftime("%B %-d, %Y")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "date_str": d.isoformat(),
            "pretty_date": pretty_date,
            "prev_day": prev_day,
            "next_day": next_day,
            "is_today": is_today,
            "games_today": games_today,
        },
    )
