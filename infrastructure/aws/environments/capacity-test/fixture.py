"""Infrastructure-only fixed response. No app, AWS SDK, or external I/O."""

import json
import time


def handler(event, context):
    query = event.get("queryStringParameters") or {}
    if query.get("slow") == "1":
        time.sleep(6)
    status = 503 if query.get("busy") == "1" else 200
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Retry-After": "5"},
        "body": json.dumps({"fixture": "capacity-test", "status": status}),
    }
