from fastapi import APIRouter

from app.domain.prefectures import PREFECTURES
from app.domain.schemas import PrefectureResponse

router = APIRouter()


@router.get("/", response_model=list[PrefectureResponse])
async def get_prefectures() -> list[PrefectureResponse]:
    return [PrefectureResponse(prec_no=k, name=v) for k, v in PREFECTURES.items()]
