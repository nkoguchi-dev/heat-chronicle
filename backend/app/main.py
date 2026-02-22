import logging

logging.basicConfig(level=logging.INFO)
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.config import settings
from app.infrastructure.init_tables import ensure_tables_exist
from app.infrastructure.seed import seed_stations
from app.presentation.api import hello, prefectures, stations, temperature

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Initializing DynamoDB tables...")
    ensure_tables_exist()
    logger.info("DynamoDB tables ready.")
    logger.info("Seeding stations...")
    seed_stations()
    logger.info("Stations seeded.")
    yield


app = FastAPI(
    title="Heat Chronicle API",
    description="Heat Chronicle API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(hello.router, prefix="/api/hello", tags=["hello"])
app.include_router(prefectures.router, prefix="/api/prefectures", tags=["prefectures"])
app.include_router(stations.router, prefix="/api/stations", tags=["stations"])
app.include_router(temperature.router, prefix="/api/temperature", tags=["temperature"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
