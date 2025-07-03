from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import BlogPost

router = APIRouter(
    prefix="/deep-dives",
    tags=["blog", "deep-dives"]
)

templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def deep_dives_index(request: Request, db: Session = Depends(get_db)):
    """Blog post listing page - now dynamic from database"""
    # Get published blog posts
    posts = db.query(BlogPost).filter(
        BlogPost.published == True,
        BlogPost.category == "deep-dive"
    ).order_by(BlogPost.created_at.desc()).all()
    
    return templates.TemplateResponse(
        "deep-dives/index.html",
        {"request": request, "posts": posts}
    )

@router.get("/{slug}", response_class=HTMLResponse)
async def blog_post_detail(slug: str, request: Request, db: Session = Depends(get_db)):
    """Individual blog post page - dynamic from database"""
    post = db.query(BlogPost).filter(
        BlogPost.slug == slug,
        BlogPost.published == True
    ).first()
    
    if not post:
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    return templates.TemplateResponse(
        "deep-dives/post_detail.html",
        {"request": request, "post": post}
    )

# Legacy routes for your existing posts - these will be migrated to database
@router.get("/historical_player_analysis_072025", response_class=HTMLResponse)
async def legacy_hist_analysis_post(request: Request):
    """Legacy route - should migrate this content to database"""
    return templates.TemplateResponse(
        "deep-dives/historical_player_analysis_072025/nhl-player-demographics.html",
        {"request": request}
    )

@router.get("/player_movement_072025", response_class=HTMLResponse)
async def legacy_player_movement_post(request: Request):
    """Legacy route - should migrate this content to database"""
    return templates.TemplateResponse(
        "deep-dives/player_movement_072025/player_movement.html",
        {"request": request}
    )