from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(
    tags=["pages"]
)

templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """Homepage"""
    return templates.TemplateResponse(
        "index.html", 
        {"request": request}
    )

@router.get("/about", response_class=HTMLResponse)
async def about_page(request: Request):
    """About page"""
    return templates.TemplateResponse(
        "about.html", 
        {"request": request}
    )