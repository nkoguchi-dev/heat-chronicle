"""Local Make targets: command delegation and owned POSIX process groups."""

from __future__ import annotations

import argparse
import os
import shlex
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from types import FrameType
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
START_TIMEOUT = 60.0
STOP_TIMEOUT = 5.0


class DevelopmentError(Exception):
    def __init__(self, message: str, code: int = 1) -> None:
        super().__init__(message)
        self.code = code


class Runner:
    def __init__(self) -> None:
        self.children: list[subprocess.Popen[bytes]] = []
        self.stop_signal = 0

    def request_stop(self, signum: int, frame: FrameType | None) -> None:
        self.stop_signal = self.stop_signal or signum

    def ensure_running(self) -> None:
        if self.stop_signal:
            raise DevelopmentError("Stopping local processes", 128 + self.stop_signal)

    def start(
        self, command: list[str], cwd: Path, env: dict[str, str] | None = None
    ) -> subprocess.Popen[bytes]:
        self.ensure_running()
        print(f"[{cwd.name}] {shlex.join(command)}", flush=True)
        process = subprocess.Popen(
            command, cwd=cwd, env=env, shell=False, start_new_session=True
        )
        self.children.append(process)
        return process

    def run(
        self, command: list[str], cwd: Path, env: dict[str, str] | None = None
    ) -> None:
        process = self.start(command, cwd, env)
        try:
            while process.poll() is None:
                self.ensure_running()
                time.sleep(0.1)
            self.ensure_running()
            if process.returncode:
                raise DevelopmentError(
                    f"Command failed: {shlex.join(command)} ({process.returncode})",
                    exit_code(process.returncode),
                )
        finally:
            stop_groups([process])
            self.children.remove(process)

    def check_children(self) -> None:
        self.ensure_running()
        for process in self.children:
            code = process.poll()
            if code is not None:
                raise DevelopmentError(
                    f"Host process {process.pid} exited unexpectedly ({code})",
                    exit_code(code) if code else 1,
                )

    def wait_http(self, url: str) -> None:
        deadline = time.monotonic() + START_TIMEOUT
        opener = build_opener(ProxyHandler({}))
        while time.monotonic() < deadline:
            self.check_children()
            try:
                with opener.open(url, timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (URLError, TimeoutError, OSError):
                pass
            time.sleep(0.1)
        raise DevelopmentError(f"Readiness timed out: {url}")


def exit_code(code: int) -> int:
    return 128 - code if code < 0 else code


def signal_group(process: subprocess.Popen[bytes], signum: int) -> None:
    try:
        os.killpg(process.pid, signum)
    except ProcessLookupError:
        pass


def group_exists(process: subprocess.Popen[bytes]) -> bool:
    process.poll()
    try:
        os.killpg(process.pid, 0)
        return True
    except ProcessLookupError:
        return False


def stop_groups(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        signal_group(process, signal.SIGTERM)
    deadline = time.monotonic() + STOP_TIMEOUT
    while any(group_exists(process) for process in processes):
        if time.monotonic() >= deadline:
            for process in processes:
                signal_group(process, signal.SIGKILL)
            break
        time.sleep(0.05)
    for process in processes:
        process.wait()


def copy_environment() -> None:
    target = ROOT / "backend/.env.local"
    try:
        # Exclusive create also protects an existing empty file or dangling symlink.
        example = (ROOT / "backend/.env.example").read_text()
        with target.open("x") as output:
            output.write(example)
        print("Created backend/.env.local from example", flush=True)
    except FileExistsError:
        print("Keeping existing backend/.env.local", flush=True)


def local_database() -> str:
    # Use exactly the application's settings precedence and dotenv parser.
    sys.path.insert(0, str(ROOT / "backend"))
    from app.config import Settings

    settings = Settings()
    endpoint = settings.dynamodb_endpoint_url or ""
    parsed = urlsplit(endpoint)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or parsed.port is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise DevelopmentError("Local targets require an explicit loopback HTTP DB URL")
    prefix = settings.dynamodb_table_prefix
    if prefix != "local" and not prefix.startswith("local-"):
        raise DevelopmentError("Local targets require a local or local-* table prefix")
    return endpoint


def port_number(name: str, default: int) -> int:
    value = int(os.environ.get(name, default))
    if not 1 <= value <= 65535:
        raise DevelopmentError(f"Invalid port: {name}")
    return value


def require_free_port(host: str, port: int) -> None:
    # Refuse occupied listeners rather than silently picking another Vite port.
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    for family, socktype, protocol, _, address in addresses:
        with socket.socket(family, socktype, protocol) as listener:
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind(address)
            except OSError as error:
                raise DevelopmentError(f"Port is unavailable: {host}:{port}") from error


def start_database(runner: Runner) -> None:
    runner.run(
        [
            "docker",
            "compose",
            "up",
            "-d",
            "--wait",
            "--wait-timeout",
            "60",
            "dynamodb-local",
        ],
        ROOT,
    )


def develop(runner: Runner) -> None:
    local_database()
    api_port = port_number("HEAT_DEV_API_PORT", 8000)
    frontend_port = port_number("HEAT_DEV_FRONTEND_PORT", 3000)
    require_free_port("127.0.0.1", api_port)
    require_free_port("localhost", frontend_port)
    start_database(runner)
    environment = dict(os.environ)
    environment["CORS_ALLOW_ORIGINS"] = f"http://localhost:{frontend_port}"
    runner.start(
        [
            "uv",
            "run",
            "--locked",
            "--no-sync",
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
        ],
        ROOT / "backend",
        environment,
    )
    environment = dict(os.environ)
    environment["VITE_API_URL"] = ""
    environment["HEAT_CHRONICLE_API_PROXY_TARGET"] = f"http://127.0.0.1:{api_port}"
    runner.start(
        ["npm", "run", "dev", "--", "--port", str(frontend_port), "--strictPort"],
        ROOT / "frontend",
        environment,
    )
    runner.wait_http(f"http://127.0.0.1:{api_port}/health")
    runner.wait_http(f"http://localhost:{frontend_port}/")
    print(
        f"Ready: http://localhost:{frontend_port} (API :{api_port}); "
        "Ctrl+C to stop hosts",
        flush=True,
    )
    print("DynamoDB Local remains available; use make stop to stop it.", flush=True)
    while True:
        runner.check_children()
        time.sleep(0.1)


def check(runner: Runner) -> None:
    endpoint = local_database()
    for arguments in [
        ["black", "--check", "."],
        ["isort", "--check-only", "."],
        ["flake8", "."],
        ["mypy", "."],
        ["pytest", "tests/"],
    ]:
        runner.run(["uv", "run", "--locked", "--no-sync", *arguments], ROOT / "backend")
    start_database(runner)
    environment = dict(
        os.environ, DYNAMODB_ENDPOINT_URL=endpoint, DYNAMODB_TABLE_PREFIX="test-make"
    )
    runner.run(
        ["uv", "run", "--locked", "--no-sync", "pytest", "integration_tests/"],
        ROOT / "backend",
        environment,
    )
    for script in ["format:check", "lint", "typecheck", "test:coverage", "build"]:
        environment = dict(os.environ, VITE_API_URL="http://localhost:8000")
        runner.run(["npm", "run", script], ROOT / "frontend", environment)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", choices=["setup", "dev", "check"])
    target = parser.parse_args().target
    runner = Runner()
    signal.signal(signal.SIGINT, runner.request_stop)
    signal.signal(signal.SIGTERM, runner.request_stop)
    try:
        if target == "setup":
            copy_environment()
            runner.run(["npm", "ci"], ROOT / "frontend")
        elif target == "dev":
            develop(runner)
        else:
            check(runner)
        return 0
    except DevelopmentError as error:
        print(str(error), file=sys.stderr, flush=True)
        return error.code
    except (OSError, ValueError) as error:
        print(f"Local development failed: {error}", file=sys.stderr, flush=True)
        return 1
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        stop_groups(runner.children)


if __name__ == "__main__":
    sys.exit(main())
