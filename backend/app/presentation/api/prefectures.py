from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.di.container import PrefectureServiceDep

router = APIRouter()


class PrefectureResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    prec_no: int
    name: str


@router.get("/", response_model=list[PrefectureResponse])
async def get_prefectures(
    service: PrefectureServiceDep,
) -> list[PrefectureResponse]:
    return [
        PrefectureResponse(prec_no=item.prec_no, name=item.name)
        for item in service.get_all()
    ]
