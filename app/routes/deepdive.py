from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.utils.markdown_loader import load_deep_dive, load_all_deep_dives
import os

templates = Jinja2Templates(directory="templates")
deepdive_router = APIRouter()

# -----------------------------------------------------------------------
# Route: Deep Dives Page ('/deep-dives')
# Loads templates/deep-dives/index.html
# -----------------------------------------------------------------------

@deepdive_router.get("/", response_class=HTMLResponse)
async def deep_dives_home(request: Request):
    posts = load_all_deep_dives()
    return templates.TemplateResponse("deep-dives/index.html", {
        "request": request,
        "posts": posts
    })

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
        "short_title": post_data.get("short_title"),
        "date": post_data["date_str"],
        "image": post_data["image"],
        "summary": post_data["summary"],
        "description": post_data["description"],
        "keywords": post_data["keywords"],
        "slug": post_data["slug"],
        "content": post_data["content"],
        "data_source": post_data["data_source"]
    })
