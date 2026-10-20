"""Run inside the candidate image with networking disabled; never contact AWS."""

import importlib.util
from unittest.mock import patch

assert importlib.util.find_spec("pip") is None
assert importlib.util.find_spec("ensurepip") is None
with patch("app.infrastructure.seed.seed_and_migrate"):
    from app.handler import handler

response = handler(
    {
        "version": "2.0",
        "routeKey": "GET /health",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {},
        "isBase64Encoded": False,
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/health",
                "sourceIp": "127.0.0.1",
                "protocol": "HTTP/1.1",
            },
            "requestId": "offline-container-smoke",
            "stage": "$default",
        },
    },
    None,
)
assert response["statusCode"] == 200
print("Isolated candidate Lambda health handler: passed (seed stubbed, no network)")
