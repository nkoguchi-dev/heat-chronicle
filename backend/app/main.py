import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.di.container import register_dependencies
from app.di.lifecycle import initialize_host
from app.presentation.api import health, hello, prefectures, stations, temperature
from app.presentation.api.shared.exception_handlers import unhandled_exception_handler

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    initialize_host()
    yield


app = FastAPI(
    title="Heat Chronicle API",
    description="Heat Chronicle API",
    version="0.1.0",
    lifespan=lifespan,
)

register_dependencies(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins.split(","),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Accept-Language", "Content-Language", "Content-Type"],
    expose_headers=["Retry-After"],
    max_age=86400,
)

app.include_router(hello.router, prefix="/api/hello", tags=["hello"])
app.include_router(prefectures.router, prefix="/api/prefectures", tags=["prefectures"])
app.include_router(stations.router, prefix="/api/stations", tags=["stations"])
app.include_router(temperature.router, prefix="/api/temperature", tags=["temperature"])
app.include_router(health.router, tags=["health"])


app.add_exception_handler(Exception, unhandled_exception_handler)
