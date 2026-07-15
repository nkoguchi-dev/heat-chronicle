from fastapi import APIRouter

from app.presentation.api.health import get_health

router = APIRouter()
router.include_router(get_health.router)
