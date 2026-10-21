import logging

from app.infrastructure.init_tables import ensure_tables_exist
from app.infrastructure.seed import seed_and_migrate

logger = logging.getLogger(__name__)


def initialize_host() -> None:
    logger.info("Initializing DynamoDB tables...")
    ensure_tables_exist()
    logger.info("DynamoDB tables ready.")
    logger.info("Running station migrations...")
    seed_and_migrate()
    logger.info("Station migrations complete.")


def initialize_lambda() -> None:
    # Lambda tables are provisioned externally; preserve cold-start seed only.
    seed_and_migrate()
