import asyncio
import json
import logging

from mangum import Mangum

from app.infrastructure.seed import seed_stations
from app.main import app

logger = logging.getLogger(__name__)

seed_stations()

mangum_handler = Mangum(app, lifespan="off")


def handler(event, context):
    if event.get("action") == "execute_scrape_job":
        from app.application.scrape_service import ScrapeService
        from app.infrastructure.database import get_dynamodb_resource
        from app.infrastructure.repositories.job_repository import JobRepository
        from app.infrastructure.repositories.station_repository import (
            StationRepository,
        )
        from app.infrastructure.repositories.temperature_repository import (
            TemperatureRepository,
        )

        dynamodb = get_dynamodb_resource()
        service = ScrapeService(
            StationRepository(dynamodb),
            TemperatureRepository(dynamodb),
            JobRepository(dynamodb),
        )
        asyncio.run(service.execute_job(event["job_id"], lambda_context=context))
        return {"statusCode": 200}

    return mangum_handler(event, context)
