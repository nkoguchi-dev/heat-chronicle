from mangum import Mangum

from app.infrastructure.seed import seed_stations
from app.main import app

seed_stations()

mangum_handler = Mangum(app, lifespan="off")


def handler(event, context):
    return mangum_handler(event, context)
