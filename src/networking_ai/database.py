"""
Database Configuration and Connection Management.

Sets up PostgreSQL connection using SQLAlchemy ORM.
"""

from typing import Generator
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import Pool

from .config import config


# Database URL from environment or config
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'sqlite:///./data/networking_ai.db'  # Default to SQLite for easy setup
)

# Create SQLAlchemy engine with SQLite-specific optimizations
if DATABASE_URL.startswith('sqlite'):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},  # Required for SQLite with FastAPI
        echo=config.DEBUG,  # Log SQL queries in debug mode
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=10,  # Connection pool size
        max_overflow=20,  # Max connections beyond pool_size
        echo=config.DEBUG,  # Log SQL queries in debug mode
    )

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Base class for all models
Base = declarative_base()


# Database session dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Dependency function that provides database session.

    Usage in FastAPI endpoints:
        @app.get("/users/")
        def read_users(db: Session = Depends(get_db)):
            return db.query(User).all()

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Event listener to set timezone on connection
@event.listens_for(Pool, "connect")
def set_postgres_timezone(dbapi_connection, connection_record):
    """Set timezone to UTC for all connections (PostgreSQL only)."""
    # Only run for PostgreSQL, skip for SQLite (used in tests)
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("SET timezone='UTC'")
        cursor.close()
    except Exception:
        # Skip for non-PostgreSQL databases (like SQLite)
        pass


def init_db() -> None:
    """
    Initialize database by creating all tables.

    This should be called on application startup.
    In production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)
    print("[DATABASE] All tables created successfully")


def drop_db() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data!
    Only use in development/testing.
    """
    Base.metadata.drop_all(bind=engine)
    print("[DATABASE] All tables dropped")
