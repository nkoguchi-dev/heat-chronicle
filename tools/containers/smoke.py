"""Run inside the candidate image with networking disabled; never contact AWS."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

assert sys.version_info[:2] == (3, 14)
for name in ("uv", "poetry", "pytest", "black", "mypy", "flake8"):
    assert importlib.util.find_spec(name) is None, name
assert importlib.util.find_spec("pip") is None
assert importlib.util.find_spec("ensurepip") is None
assert not Path("/usr/local/bin/aws-lambda-rie").exists()
with patch("app.di.lifecycle.seed_and_migrate"):
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

# A representative read-only application route, still with no AWS/upstream access.
response = handler(
    {
        "version": "2.0",
        "routeKey": "GET /api/prefectures/",
        "rawPath": "/api/prefectures/",
        "rawQueryString": "",
        "headers": {},
        "isBase64Encoded": False,
        "requestContext": {
            "http": {
                "method": "GET",
                "path": "/api/prefectures/",
                "sourceIp": "127.0.0.1",
                "protocol": "HTTP/1.1",
            },
            "requestId": "offline-prefectures-smoke",
            "stage": "$default",
        },
    },
    None,
)
assert response["statusCode"] == 200
print("Isolated Lambda prefecture route and runtime-only dependencies: passed")

# Exercise the real AWS entrypoint/bootstrap against an in-container Runtime API.
# A tiny handler avoids application initialization/AWS calls; the application
# handler and DI are covered above. No host ports or external network are needed.
received = threading.Event()
responses = []


class RuntimeAPI(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        assert self.path == "/2018-06-01/runtime/invocation/next"
        event = b'{"probe":"entrypoint"}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(event)))
        self.send_header("Content-Type", "application/json")
        self.send_header("Lambda-Runtime-Aws-Request-Id", "offline-runtime-smoke")
        self.send_header("Lambda-Runtime-Deadline-Ms", "4102444800000")
        self.send_header("Lambda-Runtime-Invoked-Function-Arn", "offline")
        self.send_header(
            "Lambda-Runtime-Trace-Id",
            "Root=1-00000000-000000000000000000000000;Sampled=0",
        )
        self.end_headers()
        self.wfile.write(event)

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        responses.append((self.path, json.loads(body)))
        self.send_response(202)
        self.send_header("Content-Length", "0")
        self.end_headers()
        received.set()


with tempfile.TemporaryDirectory(prefix="runtime-smoke-") as directory:
    Path(directory, "runtime_probe.py").write_text(
        "def handler(event, context):\n"
        "    return {'probe': event['probe'], 'requestId': context.aws_request_id}\n"
    )
    server = ThreadingHTTPServer(("127.0.0.1", 0), RuntimeAPI)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    environment = {
        **os.environ,
        "AWS_LAMBDA_RUNTIME_API": f"127.0.0.1:{server.server_port}",
        "PYTHONPATH": directory,
        "NO_PROXY": "*",
        "no_proxy": "*",
    }
    with tempfile.TemporaryFile() as output:
        process = subprocess.Popen(
            ["/lambda-entrypoint.sh", "runtime_probe.handler"],
            env=environment,
            stdout=output,
            stderr=output,
        )
        thread.start()
        try:
            if not received.wait(15):
                output.seek(0)
                raise AssertionError(output.read().decode(errors="replace"))
            assert responses[0] == (
                "/2018-06-01/runtime/invocation/offline-runtime-smoke/response",
                {"probe": "entrypoint", "requestId": "offline-runtime-smoke"},
            ), responses[0]
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
print("AWS entrypoint/bootstrap with isolated Runtime API: passed (no RIE)")
