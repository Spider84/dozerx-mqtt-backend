"""
Router for scheduler management endpoints.

This module provides endpoints for viewing scheduled tasks and manually
executing tasks.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from database import get_db
from logger_config import setup_logger
from scheduler_app import get_scheduler_tasks, execute_cron_task
from models import DBTask
from auth_middleware import api_key_auth

logger = setup_logger(__name__)

router = APIRouter(prefix="/scheduler", tags=["Scheduler"])

@router.get(
    "/tasks",
    summary="Get scheduled tasks",
    description="Get all scheduled tasks with time until next execution"
)
def get_scheduled_tasks(_: str = Depends(api_key_auth)):
    """
    Get all scheduled tasks with time until next execution.

    Returns:
        List of scheduled tasks with human-readable time until next execution

    Raises:
        401: Invalid API key
        500: Database error
    """
    logger.info("API request: Get all scheduled tasks")
    try:
        tasks = get_scheduler_tasks()
        logger.info("API response: Returning %s scheduled tasks", len(tasks))
        return tasks
    except SQLAlchemyError as e:
        logger.error("API error: Failed to get scheduled tasks: %s", e)
        raise

@router.post(
    "/tasks/{task_id}/run",
    summary="Run task manually",
    description="Manually execute a task immediately"
)
async def run_task_manually(
    task_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Manually execute a task immediately.

    Args:
        task_id: ID of the task to execute (path parameter)

    Returns:
        Execution result message

    Raises:
        404: Task not found
        401: Invalid API key
        500: Database error
    """
    logger.info("API request: Manual execution of task %s", task_id)
    try:
        # Check if task exists in database
        task = db.query(DBTask).filter(DBTask.id == task_id).first()
        if not task:
            logger.warning("Task %s not found in database", task_id)
            raise HTTPException(status_code=404, detail=f"Task with ID {task_id} not found")

        logger.info("Manually executing task %s for device %s", task_id, task.device_mac)

        # Execute the task
        await execute_cron_task(task_id)

        logger.info("Manual execution of task %s completed successfully", task_id)
        return {
            "status": "success",
            "message": f"Task {task_id} executed successfully for device {task.device_mac}",
            "task_id": task_id,
            "device_mac": task.device_mac
        }

    except SQLAlchemyError as e:
        logger.error("API error: Failed to execute task %s: %s", task_id, e)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute task {task_id}: {str(e)}"
        ) from e
