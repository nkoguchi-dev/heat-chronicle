from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class InternalServerErrorResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    detail: str


def storage_error_response() -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=InternalServerErrorResponse(
            detail="Internal server error"
        ).model_dump(),
    )
