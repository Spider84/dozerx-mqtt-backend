"""
Router for client management endpoints.

This module provides endpoints for creating, retrieving, and deleting
client information.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
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

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.get(
    "/",
    summary="Get all clients",
    description="Retrieve a list of all clients in the system"
)
@limiter.limit(RATE_LIMITS["clients_read"])
def get_clients(request: Request, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):  # pylint: disable=unused-argument
    """
    Get all clients.

    Returns:
        List of all clients

    Raises:
        401: Invalid API key
        500: Database error
    """
    logger.info("Getting all clients")
    try:
        clients = db.query(models.DBClient).all()
        logger.info("Found %s clients", len(clients))
        return clients
    except SQLAlchemyError as e:
        logger.error("Error retrieving clients: %s", e)
        raise

@router.post("/", summary="Create client", description="Create a new client in the system")
def create_client(
    client: schemas.ClientCreate,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Create a new client.

    Args:
        client: Client data with name

    Returns:
        Created client object with ID

    Raises:
        401: Invalid API key
        500: Database error
    """
    logger.info("Creating new client: %s", client.name)
    try:
        db_client = models.DBClient(name=client.name)
        db.add(db_client)
        logger.debug("Added client %s to database session", client.name)
        db.commit()
        logger.debug("Database commit completed for client %s", client.name)
        db.refresh(db_client)
        logger.info("Created client with ID: %s", db_client.id)
        return db_client
    except SQLAlchemyError as e:
        logger.error("Error creating client %s: %s", client.name, e)
        db.rollback()
        logger.debug("Database rollback for client creation")
        raise

@router.post(
    "/{client_id}/devices/{mac}",
    summary="Bind device to client",
    description=(
        "Bind a device to a specific client. "
        "One device can only be bound to one client."
    )
)
@validate_mac_param()
@limiter.limit(RATE_LIMITS["clients_write"])
def bind_device_to_client(
    request: Request,  # pylint: disable=unused-argument
    client_id: int,
    mac: str,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Bind a device to a client.

    Args:
        client_id: ID of the client (path parameter)
        mac: MAC address of the device (path parameter)

    Returns:
        Success message with binding details

    Raises:
        400: Invalid MAC format or device already bound to another client
        404: Client or device not found
        401: Invalid API key
    """
    logger.info("Binding device %s to client %s", mac, client_id)
    try:
        # Check if client exists
        client = db.query(models.DBClient).filter(models.DBClient.id == client_id).first()
        if not client:
            logger.warning("Client with ID %s not found", client_id)
            raise HTTPException(status_code=404, detail="Client not found")

        # Check if device exists
        device = db.query(models.DBDevice).filter(models.DBDevice.mac == mac).first()
        if not device:
            logger.warning("Device with MAC %s not found", mac)
            raise HTTPException(status_code=404, detail="Device not found")

        # Check if device is already bound to another client
        if device.client_id and device.client_id != client_id:
            logger.warning("Device %s already bound to client %s", mac, device.client_id)
            raise HTTPException(status_code=400, detail="Device already bound to another client")

        # Bind device to client
        device.client_id = client_id
        db.commit()
        logger.info("Successfully bound device %s to client %s", mac, client_id)

        return {
            "status": "success",
            "message": f"Device {mac} bound to client {client_id}",
            "client_id": client_id,
            "device_mac": mac
        }
    except SQLAlchemyError as e:
        logger.error("Error binding device %s to client %s: %s", mac, client_id, e)
        db.rollback()
        logger.debug("Database rollback for device binding %s to client %s", mac, client_id)
        raise

@router.delete(
    "/{client_id}/devices/{mac}",
    summary="Unbind device from client",
    description="Unbind a device from a specific client"
)
@validate_mac_param()
@limiter.limit(RATE_LIMITS["clients_write"])  # Write operations
def unbind_device_from_client(
    request: Request,  # pylint: disable=unused-argument
    client_id: int,
    mac: str,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Unbind a device from a client.

    Args:
        client_id: ID of the client (path parameter)
        mac: MAC address of the device (path parameter)

    Returns:
        Success message with unbinding details

    Raises:
        400: Invalid MAC format or device not bound to this client
        404: Client or device not found
        401: Invalid API key
    """
    logger.info("Unbinding device %s from client %s", mac, client_id)
    try:
        # Check if client exists
        client = db.query(models.DBClient).filter(models.DBClient.id == client_id).first()
        if not client:
            logger.warning("Client with ID %s not found", client_id)
            raise HTTPException(status_code=404, detail="Client not found")

        # Check if device exists
        device = db.query(models.DBDevice).filter(models.DBDevice.mac == mac).first()
        if not device:
            logger.warning("Device with MAC %s not found", mac)
            raise HTTPException(status_code=404, detail="Device not found")

        # Check if device is bound to this client
        if device.client_id != client_id:
            logger.warning("Device %s not bound to client %s", mac, client_id)
            raise HTTPException(status_code=400, detail="Device not bound to this client")

        # Unbind device from client
        device.client_id = None
        db.commit()
        logger.info("Successfully unbound device %s from client %s", mac, client_id)

        return {
            "status": "success",
            "message": f"Device {mac} unbound from client {client_id}",
            "client_id": client_id,
            "device_mac": mac
        }
    except SQLAlchemyError as e:
        logger.error("Error unbinding device %s from client %s: %s", mac, client_id, e)
        db.rollback()
        logger.debug("Database rollback for device unbinding %s from client %s", mac, client_id)
        raise

@router.get(
    "/{client_id}/devices",
    summary="Get client devices",
    description="Get all devices bound to a specific client"
)
def get_client_devices(
    client_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(api_key_auth)
):
    """
    Get all devices bound to a specific client.

    Args:
        client_id: ID of the client (path parameter)

    Returns:
        List of device MAC addresses

    Raises:
        404: Client not found
        401: Invalid API key
        500: Database error
    """
    logger.info("Getting devices for client %s", client_id)
    try:
        # Check if client exists
        client = db.query(models.DBClient).filter(models.DBClient.id == client_id).first()
        if not client:
            logger.warning("Client with ID %s not found", client_id)
            raise HTTPException(status_code=404, detail="Client not found")

        # Get devices bound to this client
        devices = db.query(models.DBDevice.mac).filter(models.DBDevice.client_id == client_id).all()
        mac_addresses = [device[0] for device in devices]

        logger.info("Found %s devices for client %s", len(mac_addresses), client_id)
        return mac_addresses
    except SQLAlchemyError as e:
        logger.error("Error retrieving devices for client %s: %s", client_id, e)
        raise

@router.delete(
    "/{client_id}",
    summary="Delete client",
    description="Delete a client and unbind all associated devices"
)
def delete_client(client_id: int, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):
    """
    Delete a client.

    Args:
        client_id: ID of the client to delete

    Returns:
        Success status

    Raises:
        401: Invalid API key
        404: Client not found
        500: Database error
    """
    logger.info("Deleting client with ID: %s", client_id)
    try:
        db_client = db.query(models.DBClient).filter(models.DBClient.id == client_id).first()
        if not db_client:
            logger.warning("Client with ID %s not found", client_id)
            raise HTTPException(status_code=404)

        logger.info("Unbinding devices from client %s", client_id)
        affected_devices = db.query(models.DBDevice).filter(
            models.DBDevice.client_id == client_id
        ).update({"client_id": None})
        logger.debug("Unbound %s devices from client %s", affected_devices, client_id)

        db.delete(db_client)
        db.commit()
        logger.info("Successfully deleted client with ID: %s", client_id)
        return {"status": "ok"}
    except SQLAlchemyError as e:
        logger.error("Error deleting client %s: %s", client_id, e)
        db.rollback()
        logger.debug("Database rollback for client deletion %s", client_id)
        raise
