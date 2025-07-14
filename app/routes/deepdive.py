from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.utils.markdown_loader import load_deep_dive
import os

templates = Jinja2Templates(directory="templates")
deepdive_router = APIRouter()

# -----------------------------------------------------------------------
# Route: Deep Dives Page ('/deep-dives')
# Loads templates/deep-dives/index.html
# -----------------------------------------------------------------------

@deepdive_router.get("/", response_class=HTMLResponse)
async def deep_dives_home(request: Request):
    return templates.TemplateResponse("deep-dives/index.html", {"request": request})

# -----------------------------------------------------------------------
# Route: Specific Deep Dives
# Loads Dynamically loads Deep Dive posts
# -----------------------------------------------------------------------

@deepdive_router.get("/{slug}", response_class=HTMLResponse)
async def deep_dive_post(request: Request, slug: str):
    post_data = load_deep_dive(slug)

    if not post_data:
        raise HTTPException(status_code=404, detail="Post not found.")

    return templates.TemplateResponse("deep-dives/post.html", {
        "request": request,
        "title": post_data["title"],
        "date": post_data["date"],
        "image": post_data["image"],
        "content": post_data["content"]
    })
