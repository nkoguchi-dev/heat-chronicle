"""Forward only application CloudWatch state transitions to Discord.

Never log the event, secret, response body or underlying network exceptions.
A sanitized error lets Lambda retry and ultimately preserve the SNS event in SQS.
"""

import json
import os
import re
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class DeliveryError(RuntimeError):
    """Safe to surface in Lambda logs (no credential-bearing exception chain)."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        return None


def _webhook_url() -> str:
    # Lazy import keeps pure unit tests independent of AWS runtime packages.
    import boto3
    from botocore.config import Config

    try:
        client = boto3.client(
            "ssm",
            config=Config(
                connect_timeout=2, read_timeout=2, retries={"max_attempts": 1}
            ),
        )
        url = client.get_parameter(
            Name=os.environ["WEBHOOK_PARAMETER_NAME"], WithDecryption=True
        )["Parameter"]["Value"]
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "discord.com"
            or not re.fullmatch(r"/api/webhooks/[0-9]+/[A-Za-z0-9_-]+", parsed.path)
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError
    except Exception:
        raise DeliveryError("Discord webhook configuration unavailable") from None
    return url + "?wait=true"


def _payload(record: dict) -> dict | None:
    try:
        sns = record["Sns"]
        if (
            record["EventSource"] != "aws:sns"
            or sns["TopicArn"] != os.environ["EXPECTED_TOPIC_ARN"]
        ):
            raise ValueError
        alarm = json.loads(sns["Message"])
        name = alarm["AlarmName"]
        if name not in json.loads(os.environ["ALARM_NAMES"]):
            raise ValueError
        if alarm["AlarmArn"] != os.environ["ALARM_ARN_PREFIX"] + name:
            raise ValueError
        state = alarm["NewStateValue"]
        if state not in ("ALARM", "OK"):
            return None
        # Explicit fields, not full SNS messages or metric payloads. Discord
        # mentions are disabled and no user-input/error-body fields are sent.
        return {
            "allowed_mentions": {"parse": []},
            "embeds": [
                {
                    "title": f"Heat Chronicle: {state}",
                    "color": 15158332 if state == "ALARM" else 3066993,
                    "fields": [
                        {"name": "Alarm", "value": name[:256]},
                        {
                            "name": "State change time",
                            "value": str(alarm["StateChangeTime"])[:128],
                        },
                        {
                            "name": "Reason",
                            "value": str(alarm["NewStateReason"])[:1000],
                        },
                    ],
                    "footer": {
                        "text": (
                            "OK alone does not prove recovery. "
                            "Verify health and a cached API request."
                        )
                    },
                }
            ],
        }
    except (KeyError, TypeError, ValueError, AttributeError):
        raise DeliveryError("Invalid application alarm notification") from None


def _post(url: str, payload: dict) -> None:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "heat-chronicle-alerts",
        },
        method="POST",
    )
    try:
        with build_opener(NoRedirect()).open(request, timeout=5) as response:
            # wait=true must confirm a persisted message (200), not merely 204.
            if response.status != 200:
                raise ValueError
    except Exception:
        raise DeliveryError("Discord delivery failed; event will be retried") from None


def handler(event: dict, context: object) -> None:
    records = event.get("Records")
    if not isinstance(records, list) or len(records) != 1:
        raise DeliveryError("Expected one SNS alarm notification")
    payload = _payload(records[0])
    if payload is not None:
        _post(_webhook_url(), payload)
