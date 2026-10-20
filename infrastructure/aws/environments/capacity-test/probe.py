"""Bounded infrastructure probe; requires outputs and explicit isolated targets."""

import argparse
import json
import os
import re
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_target(target):
    region = target["region"]
    api_id = target["api_id"]
    if not re.fullmatch(r"[a-z]{2}-[a-z]+-\d", region):
        raise ValueError("Invalid region")
    if not re.fullmatch(r"[a-z0-9]+", api_id):
        raise ValueError("Invalid API id")
    if target["environment"] != "capacity-test" or not re.fullmatch(
        r"heat-capacity-issue5-[a-z0-9-]{1,20}", target["function_name"]
    ):
        raise ValueError("Only Issue 5 capacity-test resources are allowed")
    if target["endpoint"] != f"https://{api_id}.execute-api.{region}.amazonaws.com":
        raise ValueError("Only the exact isolated execute-api endpoint is allowed")


def aws(target, *args):
    return subprocess.run(
        [
            "aws",
            "--region",
            target["region"],
            "--cli-connect-timeout",
            "5",
            "--cli-read-timeout",
            "15",
            *args,
            "--output",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=25,
        env={**os.environ, "AWS_MAX_ATTEMPTS": "1", "AWS_PAGER": ""},
    )


def verify_resources(target):
    api = json.loads(
        aws(target, "apigatewayv2", "get-api", "--api-id", target["api_id"]).stdout
    )
    function = json.loads(
        aws(
            target, "lambda", "get-function", "--function-name", target["function_name"]
        ).stdout
    )
    concurrency = json.loads(
        aws(
            target,
            "lambda",
            "get-function-concurrency",
            "--function-name",
            target["function_name"],
        ).stdout
    )
    if concurrency.get("ReservedConcurrentExecutions") != 5:
        raise ValueError("Fixture concurrency must be 5")
    tags = json.loads(
        aws(
            target,
            "lambda",
            "list-tags",
            "--resource",
            function["Configuration"]["FunctionArn"],
        ).stdout
    )["Tags"]
    if api["ApiEndpoint"] != target["endpoint"] or any(
        t.get("Environment") != "capacity-test" or t.get("Issue") != "5"
        for t in (api.get("Tags", {}), tags)
    ):
        raise ValueError("AWS resource tags do not match isolated targets")


def request(target, path):
    start = time.monotonic()
    req = Request(
        target["endpoint"] + path, headers={"Origin": "http://localhost:4173"}
    )
    try:
        with build_opener(NoRedirect).open(req, timeout=15) as response:
            response.read(4096)
            status, headers = response.status, response.headers
    except HTTPError as error:
        status, headers = error.code, error.headers
        error.close()
    return {
        "status": status,
        "seconds": round(time.monotonic() - start, 3),
        "retry_after": headers.get("Retry-After"),
        "allow_origin": headers.get("Access-Control-Allow-Origin"),
        "expose_headers": headers.get("Access-Control-Expose-Headers"),
    }


def parallel(count, operation):
    barrier = threading.Barrier(count)

    def call(index):
        barrier.wait(timeout=10)
        return operation(index)

    with ThreadPoolExecutor(max_workers=count) as pool:
        return list(pool.map(call, range(count)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputs", type=Path)
    parser.add_argument("--confirm-function", required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    target = json.loads(args.outputs.read_text())["capacity_test"]["value"]
    validate_target(target)
    if args.confirm_function != target["function_name"]:
        parser.error("Confirmation must match the isolated function")
    if args.result.exists():
        parser.error("Result file already exists; choose a new path")
    verify_resources(target)
    result = {
        "kind": "infrastructure-fixture-only",
        "http_request_budget": 29,
        "direct_invoke_budget": 8,
        "phases": {},
    }
    phases = result["phases"]
    try:
        month = "/api/temperature/1/fetch-month"
        phases["normal"] = []
        for _ in range(3):
            phases["normal"] += parallel(2, lambda _: request(target, month))
            time.sleep(2.1)
        phases["busy_cors"] = [request(target, month + "?busy=1")]
        time.sleep(3)
        phases["gateway_burst"] = parallel(12, lambda _: request(target, month))
        time.sleep(6)
        phases["lambda_via_http"] = parallel(
            8, lambda _: request(target, "/slow?slow=1")
        )
        time.sleep(8)

        def invoke(_):
            start = time.monotonic()
            try:
                response = aws(
                    target,
                    "lambda",
                    "invoke",
                    "--invocation-type",
                    "RequestResponse",
                    "--function-name",
                    target["function_name"],
                    "--cli-binary-format",
                    "raw-in-base64-out",
                    "--payload",
                    '{"queryStringParameters":{"slow":"1"}}',
                    os.devnull,
                )
                metadata = json.loads(response.stdout)
                if metadata.get("StatusCode") != 200 or metadata.get("FunctionError"):
                    return {"result": "function-error"}
                return {
                    "result": "accepted",
                    "seconds": round(time.monotonic() - start, 3),
                }
            except subprocess.CalledProcessError as error:
                if "TooManyRequestsException" in error.stderr:
                    return {"result": "throttled"}
                raise

        phases["direct_invoke"] = parallel(8, invoke)
        time.sleep(8)
        phases["recovery"] = [request(target, "/health"), request(target, month)]
        busy = phases["busy_cors"][0]
        checks = {
            "normal": all(r["status"] == 200 for r in phases["normal"]),
            "busy_cors": busy["status"] == 503
            and busy["retry_after"] == "5"
            and busy["allow_origin"] == "http://localhost:4173"
            and "retry-after" in (busy["expose_headers"] or "").lower(),
            "gateway_429": any(r["status"] == 429 for r in phases["gateway_burst"]),
            "lambda_http_rejection": any(
                r["status"] >= 500 for r in phases["lambda_via_http"]
            ),
            "direct_success": any(
                r["result"] == "accepted" for r in phases["direct_invoke"]
            )
            and all(
                r["result"] in ("accepted", "throttled")
                for r in phases["direct_invoke"]
            ),
            "direct_throttle": any(
                r["result"] == "throttled" for r in phases["direct_invoke"]
            ),
            "recovery": all(r["status"] == 200 for r in phases["recovery"]),
            "response_time": all(
                r["seconds"] < 30
                for name, rows in phases.items()
                if name != "direct_invoke"
                for r in rows
            ),
        }
        result["checks"] = checks
        result["passed"] = all(checks.values())
    finally:
        with args.result.open("x") as output:
            json.dump(result, output, indent=2)
            output.write("\n")
    raise SystemExit(0 if result.get("passed") else 1)


if __name__ == "__main__":
    main()
