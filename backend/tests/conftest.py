import os
import socket
from typing import Generator, NoReturn

import pytest


@pytest.fixture(autouse=True)
def _aws_credentials() -> Generator[None, None, None]:
    """Mocked AWS credentials for moto."""
    # Clear any real AWS credentials that could interfere with moto
    env_backup = {}
    aws_keys = [k for k in os.environ if k.startswith("AWS_")]
    for key in aws_keys:
        env_backup[key] = os.environ.pop(key)

    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "ap-northeast-1"
    os.environ["AWS_CONFIG_FILE"] = "/dev/null"
    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = "/dev/null"

    yield

    # Restore original env
    for key in (
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
        "AWS_CONFIG_FILE",
        "AWS_SHARED_CREDENTIALS_FILE",
    ):
        os.environ.pop(key, None)
    os.environ.update(env_backup)


@pytest.fixture(autouse=True)
def _deny_unit_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unit tests use mocks; even configured local endpoints must not be contacted."""

    def deny_connection(*args: object, **kwargs: object) -> NoReturn:
        raise AssertionError("Unit tests must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", deny_connection)
    monkeypatch.setattr(socket.socket, "connect_ex", deny_connection)
