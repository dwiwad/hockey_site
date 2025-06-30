# Import core FastAPI tools and classes
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# Initialize the FastAPI app
app = FastAPI()

# Mount the /static URL path to serve all the static files
app.mount("/static", StaticFiles(directory = "static"), name = "static")

# Tell FastAPI to use the "Templates" folder for the html Templates
templates = Jinja2Templates(directory = "templates")

# -----------------------------------------------------------------------
# Route: Homepage ('/')
# Loads templates/index.html
# -----------------------------------------------------------------------

@app.get("/", response_class = HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# -----------------------------------------------------------------------
# Route: About Page ('/about')
# Loads templates/about.html
# -----------------------------------------------------------------------

@app.get("/about", response_class = HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

# -----------------------------------------------------------------------
# Route: Blog Page ('/blog')
# Loads templates/blog/index.html
# -----------------------------------------------------------------------

@app.get("/blog", response_class = HTMLResponse)
async def blog(request: Request):
    return templates.TemplateResponse("blog/index.html", {"request": request})

# -----------------------------------------------------------------------
# Route: Dashboard page ('/dashboard')
# Loads templates/dashboard.html
# -----------------------------------------------------------------------

@app.get("/dashboard", response_class = HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

# -----------------------------------------------------------------------
# Route: Player history Blog Page Page ('/blog/historical_player_analysis.html')
# Loads templates/blog/historical_player_analysis.html
# -----------------------------------------------------------------------

@app.get("/blog/historical_player_analysis_072025", response_class=HTMLResponse)
async def blog_hist_analysis_post(request: Request):
    return templates.TemplateResponse(
        "blog/historical_player_analysis_072025/nhl-player-demographics.html",
        {"request": request}
    )























