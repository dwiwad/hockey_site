from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from app.nhl.get_todays_games import get_games_for_date
from app.nhl.league_stats import get_league_depth_data, create_league_depth_boxplot
from app.core.config import get_current_season

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

    games_today_df = get_games_for_date(d)  
    games_today = games_today_df.to_dict(orient="records")

    prev_day = (d - timedelta(days=1)).isoformat()
    next_day = (d + timedelta(days=1)).isoformat()
    is_today = (d == datetime.now(TZ).date())
    pretty_date = d.strftime("%B %-d, %Y")

    # Generate league depth chart
    try:
        df_depth, last_modified = get_league_depth_data(season=get_current_season())  # Unpack tuple
        fig = create_league_depth_boxplot(df_depth)
        depth_chart_html = fig.to_html(include_plotlyjs='cdn', div_id='league-depth-chart', config={'displayModeBar': False})

        # Format update timestamp from S3 file metadata
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/Toronto")
        update_time = last_modified.astimezone(et).strftime('%B %-d, %Y at %I:%M %p ET')

    except Exception as e:
        # If chart fails, just show an error message instead of breaking the page
        depth_chart_html = f"<p>Chart unavailable: {e}</p>"
        update_time = None

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
            "depth_chart_html": depth_chart_html,
            "update_time": update_time,
        },
    )
