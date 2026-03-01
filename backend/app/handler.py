from typing import Any

from mangum import Mangum

from app.infrastructure.seed import seed_and_migrate
from app.main import app

seed_and_migrate()

mangum_handler = Mangum(app, lifespan="off")


def handler(event: dict[str, Any], context: Any) -> Any:
    return mangum_handler(event, context)
