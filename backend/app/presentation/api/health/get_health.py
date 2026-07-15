from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter()


class HealthResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    status: str


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    return HealthResponse(status="ok")
