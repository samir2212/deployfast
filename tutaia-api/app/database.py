import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

logger = logging.getLogger(__name__)

engine = None
AsyncSessionLocal = None


class Base(DeclarativeBase):
    pass


async def init_db():
    """Initialize database connection and create tables."""
    global engine, AsyncSessionLocal

    settings = get_settings()
    db_url = settings.database_url

    # Convert standard postgres URL to async
    async_url = db_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    ).replace(
        "postgres://", "postgresql+asyncpg://"
    )

    engine = create_async_engine(
        async_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    AsyncSessionLocal = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        # Create enum type only if it doesn't exist
        # Cannot use IF NOT EXISTS syntax - check pg_type instead
        await conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_type WHERE typname = 'deploymentstatus'
                ) THEN
                    CREATE TYPE deploymentstatus AS ENUM (
                        'pending', 'building', 'deploying',
                        'running', 'failed', 'stopped'
                    );
                END IF;
            END$$;
        """))

        # Create all tables - checkfirst skips existing tables
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

    logger.info("Database tables created/verified")


async def get_db():
    """Dependency injection for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()