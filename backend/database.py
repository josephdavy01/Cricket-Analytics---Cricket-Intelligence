"""
Async database connection setup for FastAPI backend.
Uses SQLAlchemy async engine with asyncpg driver.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/t20i_cricket_analytics"

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Dependency that provides an async database session."""
    async with async_session() as session:
        yield session
