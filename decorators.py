from functools import wraps
from fastapi import HTTPException
from logger_config import setup_logger
import re
from functools import lru_cache

logger = setup_logger(__name__)

@lru_cache(maxsize=1)
def get_mac_pattern():
    """Get compiled MAC address regex pattern (cached)"""
    return re.compile(r'^[0-9A-F]{12}$')

def validate_mac_address(mac: str) -> bool:
    """
    Validate MAC address format.
    
    Args:
        mac: MAC address string
        
    Returns:
        True if valid, False otherwise
    """
    if not mac or not isinstance(mac, str):
        return False
    cleaned_mac = mac.replace(':', '').replace('-', '').upper()
    return bool(get_mac_pattern().match(cleaned_mac))

def validate_mac_param(param_name: str = "mac"):
    """
    Decorator to validate MAC address parameters in FastAPI endpoints.
    
    Args:
        param_name: Name of the parameter to validate (default: "mac")
        
    Usage:
        @validate_mac_param()
        def get_device(mac: str, db: Session = Depends(get_db)):
            # mac is already validated
            pass
            
        @validate_mac_param("device_mac")
        def get_task(device_mac: str, db: Session = Depends(get_db)):
            # device_mac is already validated
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get the MAC address from kwargs
            mac_value = kwargs.get(param_name)
            
            if mac_value and not validate_mac_address(mac_value):
                logger.warning(f"Invalid MAC address format: {mac_value}")
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid MAC address format: {param_name}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
