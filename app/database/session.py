"""
Database session management for async SQLAlchemy.
Provides async engine and session factory.
"""
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy import text
import logging
from typing import AsyncGenerator, Optional

from app.core.config import settings
from app.database.base import Base  # Re-export Base for convenience

logger = logging.getLogger(__name__)

_async_engine: Optional[AsyncEngine] = None
_async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_async_engine() -> AsyncEngine:
    """
    Lazily create async engine.
    Avoids DB initialization side effects during module import on Render.
    """
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=10,  # Number of connections to maintain in the pool
            max_overflow=20,  # Maximum number of connections beyond pool_size
            pool_pre_ping=True,  # Verify connections before using them
            pool_recycle=3600,  # Recycle connections after 1 hour
            future=True,
        )
    return _async_engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Lazily create session factory bound to async engine."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_async_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _async_session_factory


def AsyncSessionLocal() -> AsyncSession:
    """
    Backward-compatible session creator used as:
    async with AsyncSessionLocal() as db:
    """
    return get_session_factory()()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    Use with FastAPI Depends().
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Alias for backward compatibility
get_db = get_db_session

async def init_database():
    """Initialize database connection"""
    try:
        # Test connection using SQLAlchemy 2.x compliant method
        engine = get_async_engine()
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise


async def close_database():
    """Close database connections"""
    global _async_engine, _async_session_factory
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
    _async_session_factory = None
    logger.info("Database connections closed")