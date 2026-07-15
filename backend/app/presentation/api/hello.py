from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter()


class HelloResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    message: str


@router.get("/", response_model=HelloResponse)
async def hello() -> HelloResponse:
    return HelloResponse(message="Hello World")
