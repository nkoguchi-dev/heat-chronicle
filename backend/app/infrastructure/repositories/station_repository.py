from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.tables import Station


class StationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(self) -> list[Station]:
        result = await self.session.execute(
            select(Station).order_by(Station.id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, station_id: int) -> Station | None:
        result = await self.session.execute(
            select(Station).where(Station.id == station_id)
        )
        return result.scalar_one_or_none()
