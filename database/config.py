"""
Database configuration and connection management.
"""

import os
import logging
from typing import Generator
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.pool import QueuePool

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    logging.warning(
        "python-dotenv not installed. Install with: pip install python-dotenv"
    )

logger = logging.getLogger(__name__)

# Create declarative base for models
Base = declarative_base()

# Database URL from environment or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/video_llm_eval")

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL query logging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Get a database session with context manager support.

    Usage:
        with get_session() as session:
            # Use session here
            pass

    The session will automatically commit on success or rollback on error.

    Yields:
        Database session
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection() -> bool:
    """
    Check if database connection is working.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_database_url() -> str:
    """
    Get the current database URL (with password hidden).

    Returns:
        Database URL string with password masked
    """
    url = str(engine.url)
    if engine.url.password:
        url = url.replace(str(engine.url.password), "****")
    return url
