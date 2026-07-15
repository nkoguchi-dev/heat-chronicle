import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request

from app.config import settings
from app.infrastructure.init_tables import ensure_tables_exist
from app.infrastructure.seed import seed_and_migrate
from app.presentation.api import health, hello, prefectures, stations, temperature
from app.presentation.api.shared.internal_server_error import (
    InternalServerErrorResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("Initializing DynamoDB tables...")
    ensure_tables_exist()
    logger.info("DynamoDB tables ready.")
    logger.info("Running station migrations...")
    seed_and_migrate()
    logger.info("Station migrations complete.")
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
app.include_router(health.router, tags=["health"])


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception")
    response = InternalServerErrorResponse(detail="Internal server error")
    return JSONResponse(
        status_code=500,
        content=response.model_dump(),
    )
