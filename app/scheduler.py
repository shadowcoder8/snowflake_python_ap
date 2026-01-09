"""
------------------------------------------------------------------------------
Project: Snowflake Data Product API
Developer: Rikesh Chhetri
Description: Scheduler module using APScheduler for background tasks.
------------------------------------------------------------------------------
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.config import logger
import asyncio

# Initialize Scheduler
scheduler = AsyncIOScheduler()

async def health_check_task():
    """
    Example periodic task: Logs a health check message.
    """
    logger.info("✅ Scheduled Task: System is healthy.")

def start_scheduler():
    """
    Starts the scheduler and adds jobs.
    """
    # Example: Run every 1 minute
    scheduler.add_job(
        health_check_task, 
        CronTrigger(minute="*"), 
        id="health_check", 
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("⏳ Scheduler started.")

def stop_scheduler():
    """
    Stops the scheduler.
    """
    scheduler.shutdown()
    logger.info("🛑 Scheduler stopped.")
