"""
Middleware for adding API key information to response headers.

This module provides middleware to add X-API-Key-Created-At and X-API-Key-Expires-At
headers to responses for authenticated requests.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from auth_middleware import get_current_api_key_info
from logger_config import setup_logger

logger = setup_logger(__name__)

class APIKeyHeadersMiddleware(BaseHTTPMiddleware):  # pylint: disable=too-few-public-methods
    """
    Middleware to add API key information to response headers.

    This middleware adds X-API-Key-Created-At and X-API-Key-Expires-At headers
    to responses for authenticated requests.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process request and add API key headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler

        Returns:
            HTTP response with API key headers if authenticated
        """
        # Process the request
        response = await call_next(request)

        # Get API key info if available
        api_key_info = get_current_api_key_info()

        if api_key_info:
            # Add API key information to response headers
            if api_key_info.get("created_at"):
                response.headers["X-API-Key-Created-At"] = (
                    api_key_info["created_at"].isoformat()
                )

            if api_key_info.get("expires_at"):
                response.headers["X-API-Key-Expires-At"] = (
                    api_key_info["expires_at"].isoformat()
                )

            if api_key_info.get("last_used_at"):
                response.headers["X-API-Key-Last-Used-At"] = (
                    api_key_info["last_used_at"].isoformat()
                )

            logger.debug("Added API key headers to response for request: %s",
                       request.url)

        return response
