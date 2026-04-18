from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import get_db
from models import DBApiKey
from logger_config import setup_logger
from config import config
import secrets
import hashlib

logger = setup_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

def generate_api_key() -> str:
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

@router.post("/login", summary="User login", description="Authenticate user and return temporary API key")
def login(username: str, password: str, db: Session = Depends(get_db)):
    """
    Authenticate user and return temporary API key.
    
    Args:
        username: User username (query parameter)
        password: User password (query parameter)
        
    Returns:
        API key that expires after 10 minutes of inactivity
        
    Raises:
        401: Invalid credentials
        500: Server error
    """
    logger.info(f"Login attempt for user: {username}")
    
    # Validate credentials
    config_username = config.get('auth', {}).get('username')
    config_password = config.get('auth', {}).get('password')
    
    if not config_username or not config_password:
        logger.error("Authentication configuration missing")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication not configured"
        )
    
    if username != config_username or hash_password(password) != hash_password(config_password):
        logger.warning(f"Failed login attempt for user: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    logger.info(f"User {username} authenticated successfully")
    
    # Clean up expired keys
    cleanup_expired_keys(db)
    
    # Generate new API key
    api_key = generate_api_key()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Store API key in database
    db_key = DBApiKey(
        key=api_key,
        expires_at=expires_at,
        last_used_at=datetime.utcnow()
    )
    db.add(db_key)
    db.commit()
    
    logger.info(f"Generated API key for user {username}, expires at {expires_at}")
    
    return {
        "api_key": api_key,
        "expires_at": expires_at.isoformat(),
        "expires_in_minutes": 10
    }

def cleanup_expired_keys(db: Session):
    """Remove expired API keys from database"""
    try:
        expired_keys = db.query(DBApiKey).filter(
            DBApiKey.expires_at < datetime.utcnow()
        ).all()
        
        for key in expired_keys:
            db.delete(key)
        
        if expired_keys:
            db.commit()
            logger.info(f"Cleaned up {len(expired_keys)} expired API keys")
    except Exception as e:
        logger.error(f"Error cleaning up expired keys: {e}")
        db.rollback()

def validate_api_key(api_key: str, db: Session) -> dict:
    """
    Validate API key and update last used time.
    
    Args:
        api_key: API key to validate
        db: Database session
        
    Returns:
        Dictionary with key info if valid, None if invalid
    """
    try:
        # Clean up expired keys first
        cleanup_expired_keys(db)
        
        # Find the key
        db_key = db.query(DBApiKey).filter(
            DBApiKey.key == api_key,
            DBApiKey.is_active == True
        ).first()
        
        if not db_key:
            logger.warning(f"API key not found or inactive: {api_key[:8]}...")
            return None
        
        # Check if expired
        if db_key.expires_at < datetime.utcnow():
            logger.warning(f"API key expired: {api_key[:8]}...")
            db.delete(db_key)
            db.commit()
            return None
        
        # Update last used time and extend expiration
        db_key.last_used_at = datetime.utcnow()
        db_key.expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.commit()
        
        logger.debug(f"API key validated and extended: {api_key[:8]}...")
        
        return {
            "key": db_key.key,
            "created_at": db_key.created_at,
            "expires_at": db_key.expires_at,
            "last_used_at": db_key.last_used_at
        }
        
    except Exception as e:
        logger.error(f"Error validating API key: {e}")
        return None
