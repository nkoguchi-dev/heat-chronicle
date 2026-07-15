from fastapi import APIRouter

from app.presentation.api.hello import get_hello

router = APIRouter()
router.include_router(get_hello.router)
