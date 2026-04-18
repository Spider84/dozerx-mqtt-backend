from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from auth_middleware import get_current_api_key_info
from logger_config import setup_logger

logger = setup_logger(__name__)

class APIKeyHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add API key information to response headers.
    
    This middleware adds X-API-Key-Created-At and X-API-Key-Expires-At headers
    to responses for authenticated requests.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Process the request
        response = await call_next(request)
        
        # Get API key info if available
        api_key_info = get_current_api_key_info()
        
        if api_key_info:
            # Add API key information to response headers
            if api_key_info.get("created_at"):
                response.headers["X-API-Key-Created-At"] = api_key_info["created_at"].isoformat()
            
            if api_key_info.get("expires_at"):
                response.headers["X-API-Key-Expires-At"] = api_key_info["expires_at"].isoformat()
            
            if api_key_info.get("last_used_at"):
                response.headers["X-API-Key-Last-Used-At"] = api_key_info["last_used_at"].isoformat()
            
            logger.debug(f"Added API key headers to response for request: {request.url}")
        
        return response
