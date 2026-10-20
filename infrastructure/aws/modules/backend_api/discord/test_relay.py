"""Offline delivery/security tests: no Discord or AWS calls."""

import json
import os
import sys
import unittest
from types import ModuleType
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import relay

TOPIC = "arn:aws:sns:ap-northeast-1:123456789012:app-alerts"
PREFIX = "arn:aws:cloudwatch:ap-northeast-1:123456789012:alarm:"
NAME = "app-prod-lambda-errors"
WEBHOOK = "https://discord.com/api/webhooks/123/fake_test_token"
ENV = {
    "EXPECTED_TOPIC_ARN": TOPIC,
    "ALARM_ARN_PREFIX": PREFIX,
    "ALARM_NAMES": json.dumps([NAME]),
    "WEBHOOK_PARAMETER_NAME": "/test/discord-webhook",
}


def event(state="ALARM"):
    return {
        "Records": [
            {
                "EventSource": "aws:sns",
                "Sns": {
                    "TopicArn": TOPIC,
                    "Message": json.dumps(
                        {
                            "AlarmName": NAME,
                            "AlarmArn": PREFIX + NAME,
                            "NewStateValue": state,
                            "StateChangeTime": "2026-10-19T00:00:00Z",
                            "NewStateReason": "CONTROLLED NOTIFICATION TEST / Issue #6",
                            "IgnoredField": "not-forwarded",
                        }
                    ),
                },
            }
        ]
    }


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, ENV)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_alarm_and_recovery_use_safe_embeds(self):
        for state in ("ALARM", "OK"):
            with self.subTest(state=state), patch.object(
                relay, "_webhook_url", return_value=WEBHOOK
            ), patch.object(relay, "_post") as post:
                relay.handler(event(state), None)
                payload = post.call_args.args[1]
                self.assertEqual(payload["allowed_mentions"], {"parse": []})
                self.assertIn(state, payload["embeds"][0]["title"])
                self.assertNotIn("not-forwarded", json.dumps(payload))
                self.assertIn("CONTROLLED NOTIFICATION TEST", json.dumps(payload))

    def test_ignore_insufficient_data(self):
        with patch.object(relay, "_webhook_url") as secret, patch.object(
            relay, "_post"
        ) as post:
            relay.handler(event("INSUFFICIENT_DATA"), None)
            secret.assert_not_called()
            post.assert_not_called()

    def test_reject_untrusted_topic_or_alarm(self):
        for field, value in (
            ("TopicArn", "other-topic"),
            ("AlarmName", "other-alarm"),
            ("AlarmArn", "other-arn"),
        ):
            sample = event()
            sns = sample["Records"][0]["Sns"]
            if field == "TopicArn":
                sns[field] = value
            else:
                alarm = json.loads(sns["Message"])
                alarm[field] = value
                sns["Message"] = json.dumps(alarm)
            with self.subTest(field=field), patch.object(relay, "_post") as post:
                with self.assertRaises(relay.DeliveryError):
                    relay.handler(sample, None)
                post.assert_not_called()

    def test_reject_invalid_envelope(self):
        for sample in ({}, {"Records": []}, {"Records": [None]}, {"Records": [{}, {}]}):
            with self.subTest(sample=sample), self.assertRaises(relay.DeliveryError):
                relay.handler(sample, None)

    def test_bounded_reason(self):
        sample = event()
        alarm = json.loads(sample["Records"][0]["Sns"]["Message"])
        alarm["NewStateReason"] = "x" * 10000
        sample["Records"][0]["Sns"]["Message"] = json.dumps(alarm)
        payload = relay._payload(sample["Records"][0])
        self.assertEqual(len(payload["embeds"][0]["fields"][2]["value"]), 1000)

    def _parameter_modules(self, value):
        boto = ModuleType("boto3")
        boto.client = MagicMock()
        boto.client.return_value.get_parameter.return_value = {
            "Parameter": {"Value": value}
        }
        config = ModuleType("botocore.config")
        config.Config = MagicMock()
        return {
            "boto3": boto,
            "botocore": ModuleType("botocore"),
            "botocore.config": config,
        }

    def test_parameter_url_and_wait_confirmation(self):
        modules = self._parameter_modules(WEBHOOK)
        with patch.dict(sys.modules, modules):
            self.assertEqual(relay._webhook_url(), WEBHOOK + "?wait=true")
            self.assertEqual(modules["boto3"].client.call_args.args, ("ssm",))
            modules["boto3"].client.return_value.get_parameter.assert_called_once_with(
                Name="/test/discord-webhook", WithDecryption=True
            )

    def test_reject_secret_urls_that_could_leak_token(self):
        for value in (
            WEBHOOK.replace("discord.com", "evil.test"),
            WEBHOOK.replace("https:", "http:"),
            WEBHOOK + "?wait=false",
            WEBHOOK + "#fragment",
            "https://user:password@discord.com/api/webhooks/123/token",
            "{}",
            "https://discord.com:443/api/webhooks/123/token",
        ):
            with self.subTest(value=value), patch.dict(
                sys.modules, self._parameter_modules(value)
            ):
                with self.assertRaises(relay.DeliveryError) as caught:
                    relay._webhook_url()
                self.assertNotIn(value, str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)

    def test_parameter_error_is_sanitized(self):
        modules = self._parameter_modules(WEBHOOK)
        modules["boto3"].client.return_value.get_parameter.side_effect = RuntimeError(
            WEBHOOK
        )
        with patch.dict(sys.modules, modules), self.assertRaises(
            relay.DeliveryError
        ) as caught:
            relay._webhook_url()
        self.assertNotIn(WEBHOOK, str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    def test_post_confirms_delivery_and_disables_redirects(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.status = 200
        with patch.object(relay, "build_opener", return_value=opener) as build:
            relay._post(WEBHOOK + "?wait=true", {"allowed_mentions": {"parse": []}})
        self.assertIsInstance(build.call_args.args[0], relay.NoRedirect)
        request = opener.open.call_args.args[0]
        self.assertEqual(opener.open.call_args.kwargs["timeout"], 5)
        self.assertEqual(request.full_url, WEBHOOK + "?wait=true")
        self.assertEqual(request.get_method(), "POST")

    def test_http_failures_propagate_safely_for_async_retry(self):
        for error in (
            HTTPError(WEBHOOK, 429, "rate limited", {}, None),
            HTTPError(WEBHOOK, 500, "server error", {}, None),
            URLError(WEBHOOK),
            TimeoutError(WEBHOOK),
        ):
            opener = MagicMock()
            opener.open.side_effect = error
            with self.subTest(error=type(error).__name__), patch.object(
                relay, "build_opener", return_value=opener
            ):
                with self.assertRaises(relay.DeliveryError) as caught:
                    relay._post(WEBHOOK, {})
                self.assertNotIn(WEBHOOK, str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)

    def test_204_is_not_confirmation(self):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value.status = 204
        with patch.object(
            relay, "build_opener", return_value=opener
        ), self.assertRaises(relay.DeliveryError):
            relay._post(WEBHOOK, {})

    def test_redirect_handler_does_not_follow(self):
        self.assertIsNone(
            relay.NoRedirect().redirect_request(
                None, None, 302, "", {}, "https://evil.test"
            )
        )


if __name__ == "__main__":
    unittest.main()
