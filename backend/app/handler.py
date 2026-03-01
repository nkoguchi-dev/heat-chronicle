from mangum import Mangum
from mangum.types import LambdaContext

from app.infrastructure.seed import seed_and_migrate
from app.main import app

LambdaEvent = dict[str, object]

seed_and_migrate()

mangum_handler = Mangum(app, lifespan="off")


def handler(event: LambdaEvent, context: LambdaContext) -> dict[str, object]:
    return mangum_handler(event, context)
