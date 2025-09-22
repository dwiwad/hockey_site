# app/core/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from pytz import timezone

TZ = timezone("America/Toronto")

def get_scheduler():
    # Make a new scheduler each process; caller should keep it on app.state
    return AsyncIOScheduler(timezone=TZ)

def daily_trigger(hour=5, minute=1):
    # Adjust the time as you like
    return CronTrigger(hour=hour, minute=minute, timezone=TZ)

def every_5s_trigger():
    return IntervalTrigger(seconds=5)
