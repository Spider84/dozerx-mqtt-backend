"""
Router for task management endpoints.

This module provides endpoints for creating, retrieving, and deleting
scheduled tasks for devices.
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from apscheduler.jobstores.base import JobLookupError
from database import get_db
import models
import schemas
from scheduler_app import add_task_to_scheduler, scheduler
from logger_config import setup_logger
from auth_middleware import api_key_auth
from decorators import validate_mac_param
from rate_limiter import limiter, RATE_LIMITS

logger = setup_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"], dependencies=[Depends(api_key_auth)])

@router.post(
    "/device/{mac}",
    summary="Create task for device",
    description="Create a new scheduled task for a specific device"
)
@validate_mac_param()
@limiter.limit(RATE_LIMITS["task_create"])  # Task creation should be heavily limited
def create_task(
    request: Request,  # pylint: disable=unused-argument
    mac: str,
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Create a new task for a device.

    Args:
        mac: MAC address of the device (path parameter)
        task: Task configuration with cron expression and flags

    Returns:
        Created task object

    Raises:
        400: Invalid MAC format or device not found
        401: Invalid API key
        500: Database error
    """
    logger.info("Creating new task for device %s: %s", mac, task.cron_expr)
    try:
        # Validate MAC address format
        if not schemas.validate_mac_address(mac):
            logger.warning("Invalid MAC address format: %s", mac)
            raise HTTPException(status_code=400, detail="Invalid MAC address format")

        # Check if device exists
        device = db.query(models.DBDevice).filter(models.DBDevice.mac == mac).first()
        if not device:
            logger.warning("Cannot create task - device with MAC %s does not exist", mac)
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Device with MAC {mac} not found. "
                    f"Cannot create task for non-existent device."
                )
            )

        logger.debug("Device %s found, proceeding with task creation", mac)

        db_task = models.DBTask(device_mac=mac, **task.model_dump())
        db.add(db_task)
        logger.debug("Added task for device %s to database session", mac)
        db.commit()
        logger.debug("Database commit completed for task creation")
        db.refresh(db_task)

        add_task_to_scheduler(db_task)
        logger.info("Created task with ID: %s for device %s", db_task.id, mac)
        return db_task
    except SQLAlchemyError as e:
        logger.error("Error creating task for device %s: %s", mac, e)
        db.rollback()
        logger.debug("Database rollback for task creation %s", mac)
        raise

@router.get(
    "/device/{mac}",
    summary="Get device tasks",
    description="Get all tasks for a specific device"
)
@validate_mac_param()
@limiter.limit(RATE_LIMITS["read"])  # Read operations for tasks
def get_tasks(
    request: Request,  # pylint: disable=unused-argument
    mac: str,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Get all tasks for a device.

    Args:
        mac: MAC address of the device (path parameter)

    Returns:
        List of tasks for the device

    Raises:
        400: Invalid MAC format
        401: Invalid API key
        500: Database error
    """
    logger.info("Getting tasks for device %s", mac)
    try:
        # Validate MAC address format
        if not schemas.validate_mac_address(mac):
            logger.warning("Invalid MAC address format: %s", mac)
            raise HTTPException(status_code=400, detail="Invalid MAC address format")

        tasks = db.query(models.DBTask).filter(models.DBTask.device_mac == mac).all()
        logger.info("Found %s tasks for device %s", len(tasks), mac)
        return tasks
    except SQLAlchemyError as e:
        logger.error("Error retrieving tasks for device %s: %s", mac, e)
        raise

@router.delete("/{task_id}", summary="Delete task", description="Delete a scheduled task by ID")
def delete_task(task_id: int, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):
    """
    Delete a task.

    Args:
        task_id: ID of the task to delete (path parameter)

    Returns:
        Success status

    Raises:
        404: Task not found
        401: Invalid API key
        500: Database error
    """
    logger.info("Deleting task with ID: %s", task_id)
    try:
        db_task = db.query(models.DBTask).filter(models.DBTask.id == task_id).first()
        if not db_task:
            logger.warning("Task with ID %s not found", task_id)
            raise HTTPException(status_code=404, detail="Task not found")

        logger.info("Removing scheduled job for task %s", task_id)
        try:
            scheduler.remove_job(f"task_{task_id}")
            logger.info("Successfully removed scheduled job for task %s", task_id)
        except JobLookupError as e:
            logger.warning("Could not remove scheduled job for task %s: %s", task_id, e)

        logger.debug("Deleting task record %s", task_id)
        db.delete(db_task)

        db.commit()
        logger.debug("Database commit completed for task deletion %s", task_id)
        logger.info("Successfully deleted task with ID: %s", task_id)
        return {"status": "ok"}
    except SQLAlchemyError as e:
        logger.error("Error deleting task %s: %s", task_id, e)
        db.rollback()
        logger.debug("Database rollback for task deletion %s", task_id)
        raise
