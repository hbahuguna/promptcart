import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Expects: postgresql+asyncpg://user:pass@host/dbname
# Test default: sqlite+aiosqlite:///:memory:
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///:memory:",
)

# Connect args specific for sqlite during test
connect_args = {"check_same_thread": False} if "sqlite" in DATABASE_URL else {}

engine: AsyncEngine = create_async_engine(
    DATABASE_URL,
    echo=False,
    connect_args=connect_args,
)

async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to provide an async session to FastAPI endpoints."""
    async with async_session_maker() as session:
        yield session
