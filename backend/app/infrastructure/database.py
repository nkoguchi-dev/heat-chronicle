from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Alembicマイグレーションで管理するため、テーブル存在チェックのみ行う"""
    import app.infrastructure.models.tables  # noqa: F401

    async with engine.connect() as conn:
        await conn.execute(
            __import__("sqlalchemy").text(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = 'heat'"
            )
        )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """セッションを取得"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
