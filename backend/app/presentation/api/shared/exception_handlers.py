import logging

from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.presentation.api.shared.internal_server_error import (
    InternalServerErrorResponse,
)

logger = logging.getLogger(__name__)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    response = InternalServerErrorResponse(detail="Internal server error")
    return JSONResponse(
        status_code=500,
        content=response.model_dump(),
    )
