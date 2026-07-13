import ssl
import json
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import get_settings

settings = get_settings()

database_url = settings.DATABASE_URL
if "sslmode=require" in database_url:
    database_url = database_url.replace("sslmode=require", "").replace("?&", "?").rstrip("?&")

connect_args = {}
if "neon" in database_url:
    connect_args = {"ssl": ssl.create_default_context()}

engine = create_async_engine(
    database_url,
    echo=False,
    pool_size=2,
    max_overflow=2,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


class ModelBase(Base):
    __abstract__ = True

    def to_dict(self) -> dict:
        result = {}
        for c in self.__table__.columns:
            val = getattr(self, c.name)
            if isinstance(val, Decimal):
                val = float(val)
            elif isinstance(val, (datetime, date)):
                val = val.isoformat()
            elif isinstance(val, bytes):
                val = val.decode("utf-8", errors="replace")
            result[c.name] = val
        return result


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    await engine.dispose()
