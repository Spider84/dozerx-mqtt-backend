from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from scheduler_app import add_task_to_scheduler, scheduler
from logger_config import setup_logger
from auth_middleware import api_key_auth
from decorators import validate_mac_param
from rate_limiter import limiter, RATE_LIMITS

logger = setup_logger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"], dependencies=[Depends(api_key_auth)])

@router.post("/device/{mac}", summary="Create task for device", description="Create a new scheduled task for a specific device")
@validate_mac_param()
@limiter.limit(RATE_LIMITS["task_create"])  # Task creation should be heavily limited
def create_task(request: Request, mac: str, task: schemas.TaskCreate, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):
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
    logger.info(f"Creating new task for device {mac}: {task.cron_expr}")
    try:
        # Validate MAC address format
        if not schemas.validate_mac_address(mac):
            logger.warning(f"Invalid MAC address format: {mac}")
            raise HTTPException(status_code=400, detail="Invalid MAC address format")
        
        # Check if device exists
        device = db.query(models.DBDevice).filter(models.DBDevice.mac == mac).first()
        if not device: 
            logger.warning(f"Cannot create task - device with MAC {mac} does not exist")
            raise HTTPException(status_code=404, detail=f"Device with MAC {mac} not found. Cannot create task for non-existent device.")
        
        logger.debug(f"Device {mac} found, proceeding with task creation")
        
        db_task = models.DBTask(device_mac=mac, **task.model_dump())
        db.add(db_task)
        logger.debug(f"Added task for device {mac} to database session")
        db.commit()
        logger.debug(f"Database commit completed for task creation")
        db.refresh(db_task)
        
        add_task_to_scheduler(db_task)
        logger.info(f"Created task with ID: {db_task.id} for device {mac}")
        return db_task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task for device {mac}: {e}")
        db.rollback()
        logger.debug(f"Database rollback for task creation {mac}")
        raise

@router.get("/device/{mac}", summary="Get device tasks", description="Get all tasks for a specific device")
@validate_mac_param()
@limiter.limit(RATE_LIMITS["read"])  # Read operations for tasks
def get_tasks(request: Request, mac: str, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):
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
    logger.info(f"Getting tasks for device {mac}")
    try:
        # Validate MAC address format
        if not schemas.validate_mac_address(mac):
            logger.warning(f"Invalid MAC address format: {mac}")
            raise HTTPException(status_code=400, detail="Invalid MAC address format")
        
        tasks = db.query(models.DBTask).filter(models.DBTask.device_mac == mac).all()
        logger.info(f"Found {len(tasks)} tasks for device {mac}")
        return tasks
    except Exception as e:
        logger.error(f"Error retrieving tasks for device {mac}: {e}")
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
    logger.info(f"Deleting task with ID: {task_id}")
    try:
        db_task = db.query(models.DBTask).filter(models.DBTask.id == task_id).first()
        if not db_task: 
            logger.warning(f"Task with ID {task_id} not found")
            raise HTTPException(status_code=404, detail="Task not found")
        
        logger.info(f"Removing scheduled job for task {task_id}")
        try: 
            scheduler.remove_job(f"task_{task_id}")
            logger.info(f"Successfully removed scheduled job for task {task_id}")
        except Exception as e:
            logger.warning(f"Could not remove scheduled job for task {task_id}: {e}")
        
        logger.debug(f"Deleting task record {task_id}")
        db.delete(db_task)
        
        db.commit()
        logger.debug(f"Database commit completed for task deletion {task_id}")
        logger.info(f"Successfully deleted task with ID: {task_id}")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        db.rollback()
        logger.debug(f"Database rollback for task deletion {task_id}")
        raise
