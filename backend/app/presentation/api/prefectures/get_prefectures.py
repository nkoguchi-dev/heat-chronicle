from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.di.container import GetPrefectureUseCaseDep

router = APIRouter()


class PrefectureResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    prec_no: int
    name: str


@router.get("/", response_model=list[PrefectureResponse])
async def get_prefectures(
    use_case: GetPrefectureUseCaseDep,
) -> list[PrefectureResponse]:
    return [
        PrefectureResponse(prec_no=item.prec_no, name=item.name)
        for item in use_case.get_all()
    ]
