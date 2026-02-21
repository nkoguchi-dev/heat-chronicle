from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import async_session, get_session


# Auto-commit/rollback session for standard endpoints
async def get_db_session() -> AsyncSession:
    async for session in get_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# Manual session for SSE streaming (no auto-commit/rollback)
async def get_manual_session() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


ManualSessionDep = Annotated[AsyncSession, Depends(get_manual_session)]
