"""
Main entry point for DozerX Modular Service.

This module initializes the FastAPI application with all routers,
middleware, and lifecycle management for MQTT and scheduler services.
"""
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError
from logger_config import setup_logger
import models
from database import engine
from routers import clients, devices, tasks, scheduler, auth
from mqtt_app import start_mqtt, stop_mqtt
from scheduler_app import start_scheduler, stop_scheduler
from config import config
from api_key_headers_middleware import APIKeyHeadersMiddleware
from migrations import run_migrations
from rate_limiter import limiter, RATE_LIMITS
from git_info import get_version_string
from systemd_notify import sd_ready, sd_status, sd_stopping, is_systemd_notify_available

logger = setup_logger(__name__)

models.Base.metadata.create_all(bind=engine)

# Security scheme for Swagger UI
api_key_scheme = APIKeyHeader(name="X-API-Key", description="API Key for authentication")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for the lifespan of the FastAPI application.

    This context manager starts the MQTT and scheduler functionality when the application starts,
    and runs database migrations.

    Yields:
        None

    """
    version_info = get_version_string()
    logger.info("Starting DozerX Modular Service v1.0.0%s", version_info)

    # Notify systemd that we're starting (if available)
    if is_systemd_notify_available():
        sd_status("Initializing...")

    # Run database migrations
    try:
        if is_systemd_notify_available():
            sd_status("Running database migrations...")
        run_migrations()
    except SQLAlchemyError as e:
        logger.error("Database migration failed: %s", e)
        raise

    if is_systemd_notify_available():
        sd_status("Starting MQTT and scheduler...")

    start_mqtt()
    start_scheduler()
    logger.info("DozerX Modular Service started successfully")

    # Notify systemd that we're ready
    if is_systemd_notify_available():
        sd_ready()
        sd_status("Running")

    yield
    logger.info("Shutting down DozerX Modular Service...")

    # Notify systemd that we're stopping
    if is_systemd_notify_available():
        sd_stopping()

    stop_scheduler()
    stop_mqtt()
    logger.info("DozerX Modular Service stopped")

app = FastAPI(
    title="DozerX Modular Service",
    lifespan=lifespan,
    description="IoT Device Management Service with MQTT integration",
    version="1.0.0"
)

# Set up rate limiting with global limiter
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Add security scheme for Swagger UI
app.openapi_components = {
    "securitySchemes": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key for authentication. Get it from /auth/login endpoint"
        }
    },
    "security": [
        {"ApiKeyAuth": []}
    ]
}

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/health", summary="Health check", description="Check service health status")
@limiter.limit(RATE_LIMITS["health"])  # Health check can be called frequently
async def health_check(request: Request):
    """Health check endpoint for monitoring"""
    try:
        # Check database connection
        from database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()

        # Get git information
        git_info = get_version_string()

        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": f"1.0.0{git_info}",
            "services": {
                "database": "connected",
                "mqtt": "running",
                "scheduler": "running"
            }
        }
    except SQLAlchemyError as e:
        logger.error("Health check failed: %s", e)
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }, 500

@app.get("/docs-custom", response_class=HTMLResponse, include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI with collapsed Schemas by default"""
    try:
        with open("static/swagger-ui.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        # Fallback to default Swagger UI if custom file not found
        return """
        <html>
        <head><title>Swagger UI Not Found</title></head>
        <body>
            <h1>Custom Swagger UI not found</h1>
            <p>Please use <a href="/docs">default Swagger UI</a></p>
        </body>
        </html>
        """

# Add middleware (order matters - first added runs last)
app.add_middleware(APIKeyHeadersMiddleware)

# Add all routers to FastAPI app
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(devices.router)
app.include_router(tasks.router)
app.include_router(scheduler.router)

if __name__ == "__main__":
    """
    Entry point for running the FastAPI application.

    This function starts the FastAPI application using uvicorn.
    """
    import uvicorn
    logger.info("Starting FastAPI server on %s:%s",
               config['rest']['host'], config['rest']['port'])
    uvicorn.run(
        "main:app",
        host=config['rest']['host'],
        port=config['rest']['port'],
        server_header=False,
    )