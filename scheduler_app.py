"""
Scheduler module for DozerX Modular Service.

This module handles scheduled task execution using APScheduler,
including message sending to Telegram and MAX platforms.
"""
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.base import JobLookupError
import httpx
from sqlalchemy.exc import SQLAlchemyError
from database import SessionLocal
from models import DBTask
from logger_config import setup_logger
from config import config
import schemas

logger = setup_logger(__name__)
scheduler = BackgroundScheduler()

def process_message_templates(message: str, device) -> str:
    """
    Replace templates in message with actual device counter values.

    Supported templates:
    - <!--#btn1--> - button 1 counter
    - <!--#btn2--> - button 2 counter
    - <!--#btn3--> - button 3 counter
    - <!--#btn4--> - button 4 counter
    - <!--#btn5--> - button 5 counter
    - <!--#btnlong--> - sum of long press counters
    - <!--#longtime--> - sum of long press duration
    - <!--#total--> - sum of all button presses

    Args:
        message: Message template with placeholders
        device: Device object with counter values

    Returns:
        Processed message with actual values
    """
    if not message:
        return message

    # Replace individual button counters
    message = message.replace("<!--#btn1-->", str(device.btn1_cnt))
    message = message.replace("<!--#btn2-->", str(device.btn2_cnt))
    message = message.replace("<!--#btn3-->", str(device.btn3_cnt))
    message = message.replace("<!--#btn4-->", str(device.btn4_cnt))
    message = message.replace("<!--#btn5-->", str(device.btn5_cnt))

    # Replace long press counter
    message = message.replace("<!--#btnlong-->", str(device.long_cnt))

    # Replace long press duration
    message = message.replace("<!--#longtime-->", str(device.total_duration))

    # Replace total button presses
    message = message.replace("<!--#total-->", str(device.total_cnt))

    return message

def format_time_until_next_run(seconds: int) -> str:
    """
    Convert seconds until next run into hh:mm:ss format with days.

    Args:
        seconds: Number of seconds until next execution

    Returns:
        Time string in format "hh:mm:ss" or "d days hh:mm:ss"
    """
    if seconds < 0:
        return "00:00:00"

    days = seconds // 86400
    remaining_seconds = seconds % 86400

    hours = remaining_seconds // 3600
    remaining_seconds %= 3600

    minutes = remaining_seconds // 60
    remaining_seconds %= 60

    # Format time part
    time_str = f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"

    # Add days if more than 0
    if days > 0:
        if days == 1:
            return f"1 day {time_str}"
        return f"{days} days {time_str}"
    return time_str

def execute_cron_task(task_id: int):
    """
    Execute a scheduled cron task for a device.

    Args:
        task_id: ID of the task to execute
    """
    logger.info("Executing cron task %s", task_id)
    db = SessionLocal()
    try:
        logger.debug("Database session created for task %s", task_id)
        task = db.query(DBTask).filter(DBTask.id == task_id).first()
        if not task or not task.device:
            logger.warning("Task %s not found or has no device", task_id)
            return
        device = task.device
        logger.info("Processing task %s for device %s", task_id, device.mac)
        updated_fields = []

        if task.reset_flag:
            logger.info("Resetting counters for device %s", device.mac)
            device.btn1_cnt = 0
            device.btn2_cnt = 0
            device.btn3_cnt = 0
            device.btn4_cnt = 0
            device.btn5_cnt = 0
            device.btn6_cnt = 0
            device.total_cnt = 0
            device.long_cnt = 0
            device.total_duration = 0
            updated_fields = ["btn1_cnt", "btn2_cnt", "btn3_cnt",
                            "btn4_cnt", "btn5_cnt", "btn6_cnt",
                            "total_cnt", "long_cnt", "total_duration"]
            logger.info("Counters reset for %s: %s", device.mac, updated_fields)

        if task.tg_flag and device.tg_allowed and device.tg_bot_token:
            logger.info("Sending Telegram message for device %s", device.mac)
            # Process message templates
            processed_message = process_message_templates(
                device.tg_message, device
            )
            logger.debug("Processed message template for device %s: %s",
                       device.mac, processed_message)

            url = f"https://api.telegram.org/bot{device.tg_bot_token}/sendMessage"
            payload = {
                "chat_id": device.tg_channel_id,
                "text": processed_message,
                "parse_mode": "HTML"
            }
            try:
                timeout = config.get('timeouts', {}).get('http_request', 30)
                with httpx.Client(timeout=timeout) as client:
                    client.post(url, json=payload)
                    logger.info("Telegram message sent successfully for device %s",
                               device.mac)
            except httpx.TimeoutException:
                logger.error("Timeout sending Telegram message for device %s",
                           device.mac)
            except httpx.HTTPError as e:
                logger.error("Failed to send Telegram message for device %s: %s",
                           device.mac, e)

        if task.max_flag and device.max_allowed and device.max_bot_id:
            logger.info("Sending MAX message for device %s", device.mac)
            # Process message templates
            processed_max_message = process_message_templates(
                device.max_message, device
            )
            logger.debug("Processed MAX message template for device %s: %s",
                       device.mac, processed_max_message)

            # MAX API endpoint based on documentation
            max_url = f"https://platform-api.max.ru/messages?user_id={device.max_channel_id}"
            max_payload = {
                "text": processed_max_message,
                "parse_mode": "html"
            }
            max_headers = {
                "Authorization": device.max_bot_id,  # access_token
                "Content-Type": "application/json"
            }
            try:
                timeout = config.get('timeouts', {}).get('http_request', 30)
                with httpx.Client(timeout=timeout) as client:
                    client.post(max_url, json=max_payload, headers=max_headers)
                    logger.info("MAX message sent successfully for device %s",
                               device.mac)
            except httpx.TimeoutException:
                logger.error("Timeout sending MAX message for device %s",
                           device.mac)
            except httpx.HTTPError as e:
                logger.error("MAX error for device %s: %s", device.mac, e)

        if updated_fields:
            logger.debug("Committing database changes for task %s", task_id)
            db.commit()
            logger.debug("Database commit completed for task %s", task_id)
        else:
            logger.debug("No database changes to commit for task %s", task_id)
    except SQLAlchemyError as e:
        logger.error("Error executing cron task %s: %s", task_id, e)
        db.rollback()
        logger.debug("Database rollback for task %s", task_id)
        raise
    finally:
        db.close()
        logger.debug("Database session closed for task %s", task_id)

def add_task_to_scheduler(task):
    """
    Add a task to the scheduler.

    Args:
        task: DBTask object to add to scheduler
    """
    logger.info("Adding task %s to scheduler with cron: %s",
               task.id, task.cron_expr)
    scheduler.add_job(
        execute_cron_task, CronTrigger.from_crontab(task.cron_expr),
        id=f"task_{task.id}", args=[task.id], replace_existing=True
    )

def start_scheduler():
    """Start the scheduler and load all tasks from database."""
    logger.info("Starting scheduler...")
    db = SessionLocal()
    try:
        logger.debug("Database session created for scheduler startup")
        tasks = db.query(DBTask).all()
        logger.info("Found %s tasks to load", len(tasks))
        for t in tasks:
            add_task_to_scheduler(t)
        db.close()
        logger.debug("Database session closed for scheduler startup")
        scheduler.start()
        logger.info("Scheduler started successfully")
    except SQLAlchemyError as e:
        logger.error("Error starting scheduler: %s", e)
        db.close()
        raise

def get_scheduler_tasks():
    """
    Get all scheduled tasks with time until next execution.

    Returns:
        List of SchedulerTaskInfo objects with human-readable time
    """
    logger.info("Getting scheduler tasks information")
    tasks_info = []

    try:
        # Get all jobs from scheduler
        jobs = scheduler.get_jobs()
        current_time = datetime.now(timezone.utc)

        for job in jobs:
            # Extract task ID from job ID (format: "task_{task_id}")
            if not job.id.startswith("task_"):
                continue

            task_id = int(job.id.split("_")[1])

            # Get task from database
            db = SessionLocal()
            try:
                task = db.query(DBTask).filter(DBTask.id == task_id).first()
                if not task:
                    logger.warning("Task %s found in scheduler but not in database",
                                 task_id)
                    continue

                # Calculate time until next run
                next_run_time = job.next_run_time
                if next_run_time:
                    if next_run_time.tzinfo is None:
                        next_run_time = next_run_time.replace(tzinfo=timezone.utc)

                    seconds_until = int((next_run_time - current_time).total_seconds())
                    human_readable = format_time_until_next_run(seconds_until)
                else:
                    seconds_until = 0
                    human_readable = "unknown"

                task_info = schemas.SchedulerTaskInfo(
                    task_id=task.id,
                    device_mac=task.device_mac,
                    cron_expr=task.cron_expr,
                    tg_flag=task.tg_flag,
                    max_flag=task.max_flag,
                    reset_flag=task.reset_flag,
                    next_run_time=human_readable,
                    next_run_seconds=seconds_until,
                    is_active=True
                )

                tasks_info.append(task_info)
                logger.debug("Task %s: next run in %s", task_id, human_readable)

            finally:
                db.close()

    except (SQLAlchemyError, JobLookupError) as e:
        logger.error("Error getting scheduler tasks: %s", e)
        raise

    logger.info("Retrieved %s scheduler tasks", len(tasks_info))
    return tasks_info

def stop_scheduler():
    """Stop the scheduler and shutdown all scheduled tasks."""
    logger.info("Stopping scheduler...")
    scheduler.shutdown()
    logger.info("Scheduler stopped")
