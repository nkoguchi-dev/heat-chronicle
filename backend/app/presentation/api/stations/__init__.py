from fastapi import APIRouter

from app.presentation.api.stations import get_stations

router = APIRouter()
router.include_router(get_stations.router)
