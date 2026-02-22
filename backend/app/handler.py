from mangum import Mangum

from app.infrastructure.seed import seed_stations
from app.main import app

seed_stations()

handler = Mangum(app, lifespan="off")
