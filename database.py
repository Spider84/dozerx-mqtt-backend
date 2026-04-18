from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config import config
from logger_config import setup_logger

logger = setup_logger(__name__)

SQLALCHEMY_DATABASE_URL = f"sqlite:///./{config['database']['filename']}"
logger.info(f"Database URL: {SQLALCHEMY_DATABASE_URL}")

# SQLite connection pooling and performance optimizations
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={
        "check_same_thread": False,
        "timeout": 20,  # SQLite timeout
        "isolation_level": None  # Autocommit mode for better performance
    },
    pool_pre_ping=True,  # Validate connections before use
    echo=False  # Disable SQL logging in production
)

SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine,
    expire_on_commit=False  # Prevent detached instance issues
)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        logger.debug("Database session created")
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Database session closed")
