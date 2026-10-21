from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from app.application.prefecture.ports.inbound.list_prefecture import ListPrefecturePort
from app.presentation.api.shared.dependencies import get_prefecture_port

router = APIRouter()


class PrefectureResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    prec_no: int
    name: str


@router.get("/", response_model=list[PrefectureResponse])
async def get_prefectures(
    use_case: Annotated[ListPrefecturePort, Depends(get_prefecture_port)],
) -> list[PrefectureResponse]:
    return [
        PrefectureResponse(prec_no=item.prec_no, name=item.name)
        for item in use_case.list_prefectures()
    ]
