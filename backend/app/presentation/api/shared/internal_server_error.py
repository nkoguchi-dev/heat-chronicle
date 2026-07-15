from pydantic import BaseModel, ConfigDict


class InternalServerErrorResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    detail: str
