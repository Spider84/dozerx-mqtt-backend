"""
Database migration system for SQLite.
Handles version tracking and automatic schema migrations using PRAGMA user_version.
"""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database import engine
from logger_config import setup_logger

logger = setup_logger(__name__)

# Current database schema version
CURRENT_VERSION = 1

def get_current_db_version():
    """
    Get current database schema version using PRAGMA user_version.

    Returns:
        int: Current version, 0 if not set
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA user_version"))
            row = result.fetchone()
            return row[0] if row else 0
    except (SQLAlchemyError, OSError) as e:
        logger.error("Error getting database version: %s", e)
        return 0

def set_db_version(version):
    """
    Set database schema version using PRAGMA user_version.

    Args:
        version: Version number to set
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(f"PRAGMA user_version = {version}"))
            conn.commit()
            logger.info("Database version set to %s", version)
    except (SQLAlchemyError, OSError) as e:
        logger.error("Error setting database version: %s", e)
        raise

def migrate_to_v1():
    """
    Migration to version 1 - Initial schema.
    Sets PRAGMA user_version to 1.
    """
    try:
        with engine.connect() as conn:
            # Set version to 1 using PRAGMA user_version
            conn.execute(text("PRAGMA user_version = 1"))
            conn.commit()

            logger.info("Migration to version 1 completed successfully")
    except (SQLAlchemyError, OSError) as e:
        logger.error("Error during migration to v1: %s", e)
        raise

# Migration functions for each version
MIGRATIONS = {
    1: migrate_to_v1,
    # Future migrations will be added here:
    # 2: migrate_to_v2,
    # 3: migrate_to_v3,
}

def run_migrations():
    """
    Run all pending migrations to bring database to current version.
    This should be called on application startup.
    """
    try:
        current_version = get_current_db_version()
        logger.info("Current database version: %s", current_version)
        logger.info("Target database version: %s", CURRENT_VERSION)

        if current_version == CURRENT_VERSION:
            logger.info("Database is already at current version")
            return

        if current_version > CURRENT_VERSION:
            logger.warning(
                "Database version (%s) is newer than application version (%s)",
                current_version, CURRENT_VERSION
            )
            return

        # Run migrations from current version to target version
        for version in range(current_version + 1, CURRENT_VERSION + 1):
            if version in MIGRATIONS:
                logger.info("Running migration to version %s", version)
                MIGRATIONS[version]()
            else:
                logger.error("Migration function for version %s not found",
                            version)
                raise RuntimeError(f"Migration to version {version} not implemented")

        logger.info("All migrations completed successfully")

    except (SQLAlchemyError, OSError, RuntimeError) as e:
        logger.error("Migration failed: %s", e)
        raise

def check_migration_required():
    """
    Check if database migration is required.

    Returns:
        bool: True if migration is required, False otherwise
    """
    current_version = get_current_db_version()
    return current_version < CURRENT_VERSION
