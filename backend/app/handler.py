from mangum import Mangum
from mangum.types import LambdaContext

from app.di.lifecycle import initialize_lambda
from app.main import app

LambdaEvent = dict[str, object]

initialize_lambda()

mangum_handler = Mangum(app, lifespan="off")


def handler(event: LambdaEvent, context: LambdaContext) -> dict[str, object]:
    return mangum_handler(event, context)
