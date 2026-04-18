from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from logger_config import setup_logger
from auth_middleware import api_key_auth
from decorators import validate_mac_param
from rate_limiter import limiter, RATE_LIMITS

logger = setup_logger(__name__)

router = APIRouter(prefix="/clients", tags=["Clients"])

@router.get("/", summary="Get all clients", description="Retrieve a list of all clients in the system")
@limiter.limit(RATE_LIMITS["clients_read"])  # Read operations for clients
def get_clients(request: Request, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):
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
        logger.info(f"Found {len(clients)} clients")
        return clients
    except Exception as e:
        logger.error(f"Error retrieving clients: {e}")
        raise

@router.post("/", summary="Create client", description="Create a new client in the system")
def create_client(client: schemas.ClientCreate, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):
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
    logger.info(f"Creating new client: {client.name}")
    try:
        db_client = models.DBClient(name=client.name)
        db.add(db_client)
        logger.debug(f"Added client {client.name} to database session")
        db.commit()
        logger.debug(f"Database commit completed for client {client.name}")
        db.refresh(db_client)
        logger.info(f"Created client with ID: {db_client.id}")
        return db_client
    except Exception as e:
        logger.error(f"Error creating client {client.name}: {e}")
        db.rollback()
        logger.debug("Database rollback for client creation")
        raise

@router.post("/{client_id}/devices/{mac}", summary="Bind device to client", 
             description="Bind a device to a specific client. One device can only be bound to one client.")
@validate_mac_param()
@limiter.limit(RATE_LIMITS["clients_write"])  # Write operations
def bind_device_to_client(request: Request, client_id: int, mac: str, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):
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
    logger.info(f"Binding device {mac} to client {client_id}")
    try:
        # Validate MAC address format
        if not schemas.validate_mac_address(mac):
            logger.warning(f"Invalid MAC address format: {mac}")
            raise HTTPException(status_code=400, detail="Invalid MAC address format")
        
        # Check if client exists
        client = db.query(models.DBClient).filter(models.DBClient.id == client_id).first()
        if not client:
            logger.warning(f"Client with ID {client_id} not found")
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Check if device exists
        device = db.query(models.DBDevice).filter(models.DBDevice.mac == mac).first()
        if not device:
            logger.warning(f"Device with MAC {mac} not found")
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Check if device is already bound to another client
        if device.client_id and device.client_id != client_id:
            logger.warning(f"Device {mac} already bound to client {device.client_id}")
            raise HTTPException(status_code=400, detail=f"Device already bound to another client")
        
        # Bind device to client
        device.client_id = client_id
        db.commit()
        logger.info(f"Successfully bound device {mac} to client {client_id}")
        
        return {
            "status": "success",
            "message": f"Device {mac} bound to client {client_id}",
            "client_id": client_id,
            "device_mac": mac
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error binding device {mac} to client {client_id}: {e}")
        db.rollback()
        logger.debug(f"Database rollback for device binding {mac} to client {client_id}")
        raise

@router.delete("/{client_id}/devices/{mac}", summary="Unbind device from client", 
             description="Unbind a device from a specific client")
@validate_mac_param()
@limiter.limit(RATE_LIMITS["clients_write"])  # Write operations
def unbind_device_from_client(request: Request, client_id: int, mac: str, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):
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
    logger.info(f"Unbinding device {mac} from client {client_id}")
    try:
        # Validate MAC address format
        if not schemas.validate_mac_address(mac):
            logger.warning(f"Invalid MAC address format: {mac}")
            raise HTTPException(status_code=400, detail="Invalid MAC address format")
        
        # Check if client exists
        client = db.query(models.DBClient).filter(models.DBClient.id == client_id).first()
        if not client:
            logger.warning(f"Client with ID {client_id} not found")
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Check if device exists
        device = db.query(models.DBDevice).filter(models.DBDevice.mac == mac).first()
        if not device:
            logger.warning(f"Device with MAC {mac} not found")
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Check if device is bound to this client
        if device.client_id != client_id:
            logger.warning(f"Device {mac} not bound to client {client_id}")
            raise HTTPException(status_code=400, detail="Device not bound to this client")
        
        # Unbind device from client
        device.client_id = None
        db.commit()
        logger.info(f"Successfully unbound device {mac} from client {client_id}")
        
        return {
            "status": "success",
            "message": f"Device {mac} unbound from client {client_id}",
            "client_id": client_id,
            "device_mac": mac
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unbinding device {mac} from client {client_id}: {e}")
        db.rollback()
        logger.debug(f"Database rollback for device unbinding {mac} from client {client_id}")
        raise

@router.get("/{client_id}/devices", summary="Get client devices", 
           description="Get all devices bound to a specific client")
def get_client_devices(client_id: int, db: Session = Depends(get_db), _: str = Depends(api_key_auth)):
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
    logger.info(f"Getting devices for client {client_id}")
    try:
        # Check if client exists
        client = db.query(models.DBClient).filter(models.DBClient.id == client_id).first()
        if not client:
            logger.warning(f"Client with ID {client_id} not found")
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Get devices bound to this client
        devices = db.query(models.DBDevice.mac).filter(models.DBDevice.client_id == client_id).all()
        mac_addresses = [device[0] for device in devices]
        
        logger.info(f"Found {len(mac_addresses)} devices for client {client_id}")
        return mac_addresses
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving devices for client {client_id}: {e}")
        raise

@router.delete("/{client_id}", summary="Delete client", description="Delete a client and unbind all associated devices")
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
    logger.info(f"Deleting client with ID: {client_id}")
    try:
        db_client = db.query(models.DBClient).filter(models.DBClient.id == client_id).first()
        if not db_client: 
            logger.warning(f"Client with ID {client_id} not found")
            raise HTTPException(status_code=404)
        
        logger.info(f"Unbinding devices from client {client_id}")
        affected_devices = db.query(models.DBDevice).filter(models.DBDevice.client_id == client_id).update({"client_id": None})
        logger.debug(f"Unbound {affected_devices} devices from client {client_id}")
        
        db.delete(db_client)
        db.commit()
        logger.info(f"Successfully deleted client with ID: {client_id}")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting client {client_id}: {e}")
        db.rollback()
        logger.debug(f"Database rollback for client deletion {client_id}")
        raise
