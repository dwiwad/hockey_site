# Import core FastAPI tools and classes
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes import core_router, deepdive_router, dashboard_router, games_router

# Scheduler imports
from app.core.scheduler import get_scheduler, daily_trigger, every_5s_trigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger("scheduler")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = get_scheduler()
    app.state.scheduler = scheduler

    async def _noop_job():
        logger.info("✅ APScheduler fired (noop job).")

    # listener to log executions & errors
    def _listener(event):
        if isinstance(event, JobExecutionEvent):
            if event.exception:
                logger.error("❌ Job crashed", exc_info=True)
            else:
                logger.info("⏱️ Job ran successfully.")

    scheduler.add_listener(_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    scheduler.add_job(
        _noop_job,
        trigger=daily_trigger(hour=5, minute=1),
        id="refresh_game_ids_daily",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        misfire_grace_time=300,
    )

    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)

# Initialize the FastAPI app
app = FastAPI(lifespan=lifespan)

# Mount the /static URL path to serve all the static files
app.mount("/static", StaticFiles(directory = "static"), name = "static")

# Tell FastAPI to use the "Templates" folder for the html Templates
templates = Jinja2Templates(directory = "templates")

# Include the routers
app.include_router(core_router)
app.include_router(deepdive_router, prefix="/deep-dives")
app.include_router(dashboard_router)
app.include_router(games_router)




















