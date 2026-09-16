import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

raw_db_url = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/t20i_cricket_analytics",
)

# Render provides postgres:// or postgresql:// which need to be converted to postgresql+asyncpg://
if raw_db_url.startswith("postgres://"):
    DATABASE_URL = raw_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif raw_db_url.startswith("postgresql://"):
    DATABASE_URL = raw_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = raw_db_url

# Strip sslmode parameters if present, as asyncpg dialect does not accept 'sslmode'
import re
DATABASE_URL = re.sub(r'[?&]sslmode=[^&]+', '', DATABASE_URL)
if '?' not in DATABASE_URL and '&' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('&', '?', 1)

engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10, max_overflow=20)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    """Dependency that provides an async database session."""
    async with async_session() as session:
        yield session

