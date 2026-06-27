from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

if settings.use_sqlite:
    _db_url = f"sqlite+aiosqlite:///{settings.sqlite_path}"
    _engine_kwargs: dict = {"connect_args": {"check_same_thread": False}}
else:
    _db_url = settings.database_url
    _engine_kwargs = {}

engine = create_async_engine(_db_url, echo=False, future=True, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
