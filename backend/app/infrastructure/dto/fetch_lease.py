from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FetchLeaseItemDTO(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    station_id: Decimal = Field(ge=0, le=0)
    year_month: Literal["__upstream_lease__"]
    owner_token: str | None = None
    expires_at: Decimal
    next_start: Decimal | None = None
