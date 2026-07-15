from fastapi import APIRouter

from app.presentation.api.prefectures import get_prefectures

router = APIRouter()
router.include_router(get_prefectures.router)
