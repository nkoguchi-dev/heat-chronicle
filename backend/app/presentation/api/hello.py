from fastapi import APIRouter

router = APIRouter()


@router.get("/", response_model=dict[str, str])
async def hello() -> dict[str, str]:
    return {"message": "Hello World"}
