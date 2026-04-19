"""
Router for device management endpoints.

This module provides endpoints for creating, retrieving, updating, and deleting
device information including settings for Telegram, MAX, and console.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas
from logger_config import setup_logger
from auth_middleware import api_key_auth
from decorators import validate_mac_param
from rate_limiter import limiter, RATE_LIMITS

logger = setup_logger(__name__)

router = APIRouter(prefix="/devices", tags=["Devices"])

@router.get(
    "/",
    summary="Get all devices",
    description="Retrieve MAC addresses of all devices or filter by client"
)
@limiter.limit(RATE_LIMITS["read"])
def get_devices(
    request: Request,  # pylint: disable=unused-argument
    client_id: int = None,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Get all devices MAC addresses.

    Args:
        client_id: Optional filter for specific client (query parameter)

    Returns:
        List of device MAC addresses

    Raises:
        401: Invalid API key
        500: Database error
    """
    logger.info("Getting device MAC addresses with client_id=%s", client_id)
    try:
        query = db.query(models.DBDevice.mac)

        if client_id is not None:
            # Filter devices for specific client
            query = query.filter(models.DBDevice.client_id == client_id)
            logger.debug("Applied filter: devices for client %s", client_id)
        # If client_id is None, return all devices (default behavior)

        mac_addresses = [mac[0] for mac in query.all()]
        logger.info("Found %s device MAC addresses", len(mac_addresses))
        return mac_addresses
    except SQLAlchemyError as e:
        logger.error("Error retrieving device MAC addresses: %s", e)
        raise

def convert_device_create_to_db(device: schemas.DeviceCreate) -> dict:
    """
    Convert grouped DeviceCreate schema to flat database fields.

    Args:
        device: DeviceCreate schema with grouped fields

    Returns:
        Dictionary with flat fields for database
    """
    db_data = {
        "mac": device.mac,
        "short_name": device.short_name,
        "description": device.description,
    }

    # Convert telegram settings
    if device.telegram:
        db_data.update({
            "tg_allowed": device.telegram.allowed,
            "tg_bot_token": device.telegram.bot_token,
            "tg_message": device.telegram.message,
            "tg_channel_id": device.telegram.channel_id,
        })

    # Convert max settings
    if device.max:
        db_data.update({
            "max_allowed": device.max.allowed,
            "max_bot_id": device.max.bot_id,
            "max_message": device.max.message,
            "max_channel_id": device.max.channel_id,
        })

    # Convert console settings
    if device.cons:
        db_data.update({
            "cons_1": device.cons.cons_1,
            "cons_2": device.cons.cons_2,
            "cons_3": device.cons.cons_3,
            "cons_4": device.cons.cons_4,
            "cons_5": device.cons.cons_5,
            "stop_flags": device.cons.stop_flags,
        })

    return db_data

def convert_device_update_to_db(device: schemas.DeviceUpdate) -> dict:  # pylint: disable=too-many-branches
    """
    Convert grouped DeviceUpdate schema to flat database fields.

    Args:
        device: DeviceUpdate schema with grouped fields

    Returns:
        Dictionary with flat fields for database
    """
    db_data = {}

    if device.short_name is not None:
        db_data["short_name"] = device.short_name
    if device.description is not None:
        db_data["description"] = device.description

    # Convert telegram settings
    if device.telegram:
        if device.telegram.allowed is not None:
            db_data["tg_allowed"] = device.telegram.allowed
        if device.telegram.bot_token is not None:
            db_data["tg_bot_token"] = device.telegram.bot_token
        if device.telegram.message is not None:
            db_data["tg_message"] = device.telegram.message
        if device.telegram.channel_id is not None:
            db_data["tg_channel_id"] = device.telegram.channel_id

    # Convert max settings
    if device.max:
        if device.max.allowed is not None:
            db_data["max_allowed"] = device.max.allowed
        if device.max.bot_id is not None:
            db_data["max_bot_id"] = device.max.bot_id
        if device.max.message is not None:
            db_data["max_message"] = device.max.message
        if device.max.channel_id is not None:
            db_data["max_channel_id"] = device.max.channel_id

    # Convert console settings
    if device.cons:
        if device.cons.cons_1 is not None:
            db_data["cons_1"] = device.cons.cons_1
        if device.cons.cons_2 is not None:
            db_data["cons_2"] = device.cons.cons_2
        if device.cons.cons_3 is not None:
            db_data["cons_3"] = device.cons.cons_3
        if device.cons.cons_4 is not None:
            db_data["cons_4"] = device.cons.cons_4
        if device.cons.cons_5 is not None:
            db_data["cons_5"] = device.cons.cons_5
        if device.cons.stop_flags is not None:
            db_data["stop_flags"] = device.cons.stop_flags

    return db_data

@router.post("/", summary="Create device", description="Create a new device with grouped settings")
@limiter.limit(RATE_LIMITS["write"])  # Write operations should be more limited
def create_device(
    request: Request,  # pylint: disable=unused-argument
    device: schemas.DeviceCreate,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Create a new device.

    Args:
        device: Device data with MAC address and grouped settings

    Returns:
        Created device object

    Raises:
        400: Invalid MAC format or device already exists
        401: Invalid API key
        500: Database error
    """
    logger.info("Creating new device with MAC: %s", device.mac)
    try:

        existing_device = db.query(models.DBDevice).filter(
            models.DBDevice.mac == device.mac
        ).first()
        if existing_device:
            logger.warning(
                "Device with MAC %s already exists with ID: %s",
                device.mac,
                existing_device.id
            )
            raise HTTPException(status_code=400, detail="Device with this MAC already exists")

        # Convert grouped schema to flat database fields
        db_data = convert_device_create_to_db(device)
        logger.debug("Converted device data for database: %s", list(db_data.keys()))

        db_dev = models.DBDevice(**db_data)
        db.add(db_dev)
        logger.debug("Added device %s to database session", device.mac)
        db.commit()
        logger.debug("Database commit completed for device %s", device.mac)
        db.refresh(db_dev)
        logger.info("Created device with MAC: %s", device.mac)
        return db_dev
    except SQLAlchemyError as e:
        logger.error("Error creating device %s: %s", device.mac, e)
        db.rollback()
        logger.debug("Database rollback for device creation %s", device.mac)
        raise

@router.get(
    "/{mac}",
    summary="Get device details",
    description="Get detailed information about a specific device with grouped data"
)
@validate_mac_param()
@limiter.limit(RATE_LIMITS["read"])
def get_device_detail(
    request: Request,  # pylint: disable=unused-argument
    mac: str,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Get detailed device information.

    Args:
        mac: MAC address of the device (path parameter)

    Returns:
        Detailed device information with grouped settings

    Raises:
        400: Invalid MAC format
        404: Device not found
        401: Invalid API key
        500: Database error
    """
    logger.info("Getting detailed device information for MAC: %s", mac)
    try:

        device = db.query(models.DBDevice).filter(models.DBDevice.mac == mac).first()
        if not device:
            logger.warning("Device with MAC %s not found", mac)
            raise HTTPException(status_code=404, detail="Device not found")

        # Group button counters into array of objects
        buttons = [
            schemas.ButtonInfo(num=1, count=device.btn1_cnt, global_count=device.global_btn1),
            schemas.ButtonInfo(num=2, count=device.btn2_cnt, global_count=device.global_btn2),
            schemas.ButtonInfo(num=3, count=device.btn3_cnt, global_count=device.global_btn3),
            schemas.ButtonInfo(num=4, count=device.btn4_cnt, global_count=device.global_btn4),
            schemas.ButtonInfo(num=5, count=device.btn5_cnt, global_count=device.global_btn5),
            schemas.ButtonInfo(num=6, count=device.btn6_cnt, global_count=device.global_btn6),
        ]

        # Group wifi settings
        wifi = schemas.WifiInfo(
            ip=device.ip,
            ssid=device.ssid,
            bssid=device.bssid,
            rssi=device.rssi,
        )

        # Group telegram settings
        telegram = schemas.TelegramInfo(
            allowed=device.tg_allowed,
            bot_token=device.tg_bot_token,
            message=device.tg_message,
            channel_id=device.tg_channel_id,
        )

        # Group max settings
        max_settings = schemas.MaxInfo(
            allowed=device.max_allowed,
            bot_id=device.max_bot_id,
            message=device.max_message,
            channel_id=device.max_channel_id,
        )

        # Group console settings
        console_settings = schemas.ConsInfo(
            cons_1=device.cons_1,
            cons_2=device.cons_2,
            cons_3=device.cons_3,
            cons_4=device.cons_4,
            cons_5=device.cons_5,
            stop_flags=device.stop_flags,
        )

        # Group counters into structured object
        counters = schemas.CountersInfo(
            total_cnt=device.total_cnt,
            long_cnt=device.long_cnt,
            total_duration=device.total_duration,
            global_total_cnt=device.global_total_cnt,
            global_long_cnt=device.global_long_cnt,
            global_total_duration=device.global_total_duration,
        )

        device_detail = schemas.DeviceDetail(
            mac=device.mac,
            client_id=device.client_id,
            short_name=device.short_name,
            description=device.description,
            fw_version=device.fw_version,
            uptime=device.uptime,
            wifi=wifi,
            telegram=telegram,
            max=max_settings,
            cons=console_settings,
            buttons=buttons,
            counters=counters,
        )

        logger.info("Retrieved detailed information for device %s", mac)
        return device_detail
    except SQLAlchemyError as e:
        logger.error("Error retrieving device details for %s: %s", mac, e)
        raise

def has_device_changes(db_device: models.DBDevice, update_data: dict) -> bool:
    """
    Check if any fields actually changed compared to current device values.

    Args:
        db_device: Current device from database
        update_data: Dictionary of fields to update

    Returns:
        True if any values are different, False if no changes
    """
    for field, new_value in update_data.items():
        current_value = getattr(db_device, field, None)

        # Handle None values properly
        if current_value is None and new_value is None:
            continue
        if current_value is None or new_value is None:
            return True
        if current_value != new_value:
            logger.debug("Field %s changed: %s -> %s", field, current_value, new_value)
            return True

    return False

@router.get(
    "/{mac}/history",
    summary="Get device history",
    description="Retrieve MQTT message history for a specific device"
)
@validate_mac_param()
@limiter.limit(RATE_LIMITS["read"])  # Read operations
def get_device_history(  # pylint: disable=too-many-arguments
    request: Request,  # pylint: disable=unused-argument
    mac: str,
    *,
    limit: int = Query(default=100, le=1000, ge=1),
    offset: int = Query(default=0, ge=0),
    event_type: str = None,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Get MQTT message history for a device.

    Args:
        mac: MAC address of the device (path parameter)
        limit: Maximum number of entries to return (query parameter, default: 100)
        offset: Number of entries to skip (query parameter, default: 0)
        event_type: Filter by event type (query parameter, optional)

    Returns:
        List of history entries with pagination info

    Raises:
        400: Invalid MAC format
        404: Device not found
        401: Invalid API key
        500: Database error
    """
    logger.info(
        "Getting history for device %s (limit=%s, offset=%s, event_type=%s)",
        mac,
        limit,
        offset,
        event_type
    )
    try:

        # Check if device exists
        device = db.query(models.DBDevice).filter(models.DBDevice.mac == mac).first()
        if not device:
            logger.warning("Device with MAC %s not found", mac)
            raise HTTPException(status_code=404, detail="Device not found")

        # Build query
        query = db.query(models.DBHistory).filter(models.DBHistory.mac == mac)

        # Apply event type filter if provided
        if event_type:
            query = query.filter(models.DBHistory.event_type == event_type)
            logger.debug("Applied event_type filter: %s", event_type)

        # Get total count for pagination info
        total_count = query.count()

        # Apply pagination and ordering (newest first)
        history_entries = query.order_by(
            models.DBHistory.timestamp.desc()
        ).offset(offset).limit(limit).all()

        # Convert to response format
        history_list = []
        for entry in history_entries:
            history_list.append(schemas.HistoryEntry(
                id=entry.id,
                timestamp=entry.timestamp.isoformat(),
                mac=entry.mac,
                event_type=entry.event_type,
                event_data=entry.event_data
            ))

        logger.info(
            "Retrieved %s history entries for device %s (total: %s)",
            len(history_list),
            mac,
            total_count
        )

        return {
            "history": history_list,
            "pagination": {
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
        }

    except SQLAlchemyError as e:
        logger.error("Error retrieving history for device %s: %s", mac, e)
        raise

@router.put(
    "/{mac}",
    summary="Update device",
    description="Update device settings with grouped structure"
)
@validate_mac_param()
@limiter.limit(RATE_LIMITS["write"])
def update_device(
    request: Request,  # pylint: disable=unused-argument
    mac: str,
    device: schemas.DeviceUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Update device settings.

    Args:
        mac: MAC address of the device (path parameter)
        device: Device update data with grouped settings

    Returns:
        Updated device object

    Raises:
        400: Invalid MAC format
        404: Device not found
        401: Invalid API key
        500: Database error
    """
    logger.info("Updating device with MAC: %s", mac)
    try:

        db_dev = db.query(models.DBDevice).filter(models.DBDevice.mac == mac).first()
        if not db_dev:
            logger.warning("Device with MAC %s not found", mac)
            raise HTTPException(status_code=404, detail="Device not found")

        # Convert grouped schema to flat database fields
        update_data = convert_device_update_to_db(device)
        if not update_data:
            logger.info("No fields to update for device %s", mac)
            return db_dev

        # Check if any fields actually changed
        if not has_device_changes(db_dev, update_data):
            logger.info("No actual changes detected for device %s - skipping database update", mac)
            return db_dev

        logger.info("Updating fields for device %s: %s", mac, list(update_data.keys()))
        for k, v in update_data.items():
            setattr(db_dev, k, v)
            logger.debug("Set %s = %s for device %s", k, v, mac)

        db.commit()
        logger.debug("Database commit completed for device update %s", mac)
        db.refresh(db_dev)
        logger.info("Successfully updated device with MAC: %s", mac)
        return db_dev
    except SQLAlchemyError as e:
        logger.error("Error updating device %s: %s", mac, e)
        db.rollback()
        logger.debug("Database rollback for device update %s", mac)
        raise
