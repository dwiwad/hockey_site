from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import logging

# Import your routers
from app.routers import pages, blog, dashboard
from app.database import engine
from app.models import Base

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Hockey Decoded",
    description="Hockey Analytics Website",
    version="1.0.0"
)

# Add CORS middleware (for API endpoints)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers - this is the key part!
app.include_router(pages.router)           # Homepage, about
app.include_router(blog.router)            # /deep-dives/* routes  
app.include_router(dashboard.router)       # /dashboard/* routes

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Custom 404 handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    from fastapi.templating import Jinja2Templates
    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse(
        "404.html", 
        {"request": request}, 
        status_code=404
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)