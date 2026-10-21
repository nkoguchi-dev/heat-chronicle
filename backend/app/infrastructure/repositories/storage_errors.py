import logging

from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)

logger = logging.getLogger(__name__)
STORAGE_EXCEPTIONS = (
    ClientError,
    EndpointConnectionError,
    ConnectTimeoutError,
    ReadTimeoutError,
    ConnectionClosedError,
)
STORAGE_CODES = frozenset(
    {
        "ProvisionedThroughputExceededException",
        "ThrottlingException",
        "RequestLimitExceeded",
        "InternalServerError",
        "ServiceUnavailable",
    }
)


def expected_storage_failure(exc: Exception, operation: str) -> bool:
    if (
        isinstance(exc, ClientError)
        and exc.response["Error"]["Code"] not in STORAGE_CODES
    ):
        return False
    logger.warning("storage_unavailable operation=%s", operation)
    return True
