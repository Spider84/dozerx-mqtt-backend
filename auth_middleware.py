from fastapi import Security, HTTPException, status, Depends, Request
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from database import get_db
from routers.auth import validate_api_key
from logger_config import setup_logger
from contextlib import contextmanager

logger = setup_logger(__name__)

# API Key header security
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Context variable to store API key info for middleware
_api_key_info = {}

@contextmanager
def store_api_key_info(key_info: dict):
    """Context manager to store API key info temporarily"""
    global _api_key_info
    _api_key_info = key_info
    try:
        yield
    finally:
        _api_key_info = {}

async def get_api_key(
    api_key: str = Security(api_key_header),
    db: Session = Depends(get_db)
) -> str:
    """
    Validate API key from X-API-Key header.
    
    Args:
        api_key: API key from header
        db: Database session
        
    Returns:
        Valid API key
        
    Raises:
        HTTPException: If API key is invalid or missing
    """
    if not api_key:
        logger.warning("API request missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Use X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    key_info = validate_api_key(api_key, db)
    if not key_info:
        logger.warning(f"Invalid API key attempt: {api_key[:8] if len(api_key) > 8 else '***'}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # Store key info for middleware
    global _api_key_info
    _api_key_info = key_info
    
    return api_key

# Dependency for protected endpoints
def api_key_auth(api_key: str = Depends(get_api_key)):
    """Simple dependency for API key authentication"""
    return api_key

def get_current_api_key_info():
    """Get current API key info stored by authentication"""
    return _api_key_info
