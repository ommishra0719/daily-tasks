from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Using aiosqlite for async SQLite
SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./app.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, 
    echo=True, # Set to False in production
)

AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

class Base(DeclarativeBase):
    pass

# FastAPI Dependency to get DB session per request
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session