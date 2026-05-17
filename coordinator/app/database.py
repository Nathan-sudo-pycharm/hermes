from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# SQLAlchemy does not support plain postgresql:// URLs in async mode.
# We replace it with postgresql+asyncpg:// which tells SQLAlchemy
# to use the asyncpg driver for async database communication.
DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# The engine is the core connection to the database.
# echo=False means SQL queries won't be printed to the console.
# Set echo=True temporarily if you want to debug queries.
engine = create_async_engine(DATABASE_URL, echo=False)

# AsyncSessionLocal is a factory that creates new database sessions.
# expire_on_commit=False means objects remain usable after a commit
# without needing to re-query the database.
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Base is the parent class that all our database models will inherit from.
# SQLAlchemy uses it to track which classes map to which tables.
class Base(DeclarativeBase):
    pass

# get_db is a dependency used by FastAPI endpoints.
# It creates a new session for each request and automatically
# closes it when the request is done — even if an error occurs.
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session