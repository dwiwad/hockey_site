# Import core FastAPI tools and classes
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import core_router, deepdive_router, dashboard_router

# Initialize the FastAPI app
app = FastAPI()

# Mount the /static URL path to serve all the static files
app.mount("/static", StaticFiles(directory = "static"), name = "static")

# Tell FastAPI to use the "Templates" folder for the html Templates
templates = Jinja2Templates(directory = "templates")

# Include the routers
app.include_router(core_router)
app.include_router(deepdive_router, prefix="/deep-dives")
app.include_router(dashboard_router)






















