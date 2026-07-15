from fastapi import APIRouter

from app.presentation.api.temperature import fetch_month, get_temperature

router = APIRouter()
router.include_router(get_temperature.router)
router.include_router(fetch_month.router)
