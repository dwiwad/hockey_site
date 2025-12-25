# Import core FastAPI tools and classes
from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone
from fastapi import Response, status as http_status

from app.routes import core_router, deepdive_router, dashboard_router, games_router
from app.core.depth_job import track_live_game_depth, schedule_depth_tracking_for_today
from app.core.config import S3_BUCKET

# Scheduler imports
from app.core.scheduler import get_scheduler, daily_trigger, every_5s_trigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR, JobExecutionEvent

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger("scheduler")

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = get_scheduler()
    app.state.scheduler = scheduler

    # listener to log executions & errors
    def _listener(event):
        if isinstance(event, JobExecutionEvent):
            if event.exception:
                logger.error("❌ Job crashed", exc_info=True)
            else:
                logger.info("⏱️ Job ran successfully.")

    scheduler.add_listener(_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR)

    # Add MANAGER job that runs once per day at 5 AM
    from apscheduler.triggers.interval import IntervalTrigger

    scheduler.add_job(
      lambda: schedule_depth_tracking_for_today(scheduler),  # Pass scheduler
      #trigger=IntervalTrigger(minutes=45),
      trigger=daily_trigger(hour=5, minute=0),
      id="depth_tracking_manager",
      replace_existing=True,
      coalesce=True,
      max_instances=1,
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


# Health checks
@app.get("/health")
async def health_check(response: Response):
    """System health check endpoint."""
    issues = []

    # Check 1: Is scheduler running?
    scheduler_running = False
    try:
        scheduler_running = app.state.scheduler.running
        if not scheduler_running:
            issues.append("Scheduler not running")
    except Exception as e:
        issues.append(f"Scheduler error: {str(e)}")

    # Check 2: Are required jobs scheduled?
    required_jobs = ["depth_tracking_manager"]
    try:
        active_jobs = [job.id for job in app.state.scheduler.get_jobs()]
        missing_jobs = [job for job in required_jobs if job not in active_jobs]
        if missing_jobs:
            issues.append(f"Missing jobs: {missing_jobs}")
    except Exception as e:
        issues.append(f"Job check error: {str(e)}")
        active_jobs = []

    # Check 3: Can we reach S3? (optional, can be slow)
    # Uncomment if you want to test S3 connectivity
    try:
        import s3fs
        s3 = s3fs.S3FileSystem(anon=False)
        s3.exists(f"{S3_BUCKET}/depth_scores/depth_scores.parquet")
    except Exception as e:
        issues.append(f"S3 connectivity issue: {str(e)}")

    # Determine overall status
    if issues:
        overall_status = "unhealthy"
        response.status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        overall_status = "healthy"
        response.status_code = http_status.HTTP_200_OK
    return {
        "status": overall_status,
        "scheduler_running": scheduler_running,
        "active_jobs": active_jobs,
        "issues": issues if issues else None,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Tell FastAPI to use the "Templates" folder for the html Templates
templates = Jinja2Templates(directory = "templates")

# Include the routers
app.include_router(core_router)
app.include_router(deepdive_router, prefix="/deep-dives")
app.include_router(dashboard_router)
app.include_router(games_router)




















