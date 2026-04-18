from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
from logger_config import setup_logger

logger = setup_logger(__name__)

class RemoveServerHeaderMiddleware(BaseHTTPMiddleware):
    """
    Middleware to remove Server header from HTTP responses.
    
    This middleware removes the 'Server' header from all HTTP responses
    to hide server information for security purposes.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Process the request
        response = await call_next(request)
        
        # Remove Server header if present (case-insensitive)
        if "server" in response.headers:
            del response.headers["server"]
            logger.debug("Removed Server header from response")
        
        # Also check for uppercase variants
        if "Server" in response.headers:
            del response.headers["Server"]
            logger.debug("Removed Server header from response")
        
        return response
