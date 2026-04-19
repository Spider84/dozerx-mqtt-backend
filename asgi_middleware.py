"""
ASGI middleware for removing Server header.

This module provides middleware to remove the 'Server' header from HTTP
responses for security purposes.
"""
from logger_config import setup_logger

logger = setup_logger(__name__)

class RemoveServerHeaderASGIMiddleware:
    """
    ASGI middleware to remove Server header from HTTP responses.

    This middleware removes the 'Server' header from all HTTP responses
    to hide server information for security purposes.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                # Remove Server header from response headers
                headers = []
                for name, value in message.get("headers", []):
                    if name.lower() != b"server":
                        headers.append((name, value))
                    else:
                        logger.debug("Removed Server header from response")
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)
