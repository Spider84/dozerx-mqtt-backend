"""
Database configuration and session management.

This module provides SQLAlchemy engine configuration, session management,
and context managers for database operations.
"""
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker
from config import config
from logger_config import setup_logger

logger = setup_logger(__name__)

SQLALCHEMY_DATABASE_URL = f"sqlite:///./{config['database']['filename']}"
logger.info("Database URL: %s", SQLALCHEMY_DATABASE_URL)

# SQLite connection pooling and performance optimizations
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 20
    },
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(  # pylint: disable=invalid-name
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)
Base = declarative_base()

@contextmanager
def get_db_session():
    """
    Context manager for database sessions with automatic commit/rollback.

    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
        logger.debug("Database session committed successfully")
    except SQLAlchemyError as e:
        logger.error("Database error, rolling back: %s", e)
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Database session closed")

def get_db():
    """
    Dependency function to get database session.

    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.debug("Database session closed")
