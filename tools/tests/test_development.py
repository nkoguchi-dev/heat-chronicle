"""Contract and actual POSIX lifecycle checks, without Docker or upstream access."""

from __future__ import annotations

import ast
import json
import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import development as dev  # noqa: E402


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


@pytest.mark.parametrize(
    "endpoint,prefix",
    [
        ("", "local"),
        ("https://dynamodb.ap-northeast-1.amazonaws.com", "local"),
        ("http://example.com:8001", "local"),
        ("http://localhost", "local"),
        ("http://localhost:8001/path", "local"),
        ("http://user@localhost:8001", "local"),
        ("http://localhost:8001?x=1", "local"),
        ("http://localhost:8001", "production"),
        ("http://localhost:8001", "test"),
    ],
)
def test_reject_nonlocal_configuration(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, endpoint: str, prefix: str
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DYNAMODB_ENDPOINT_URL", endpoint)
    monkeypatch.setenv("DYNAMODB_TABLE_PREFIX", prefix)
    with pytest.raises(dev.DevelopmentError):
        dev.local_database()


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "[::1]"])
def test_accept_explicit_loopback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, host: str
) -> None:
    monkeypatch.chdir(tmp_path)
    endpoint = f"http://{host}:8001"
    monkeypatch.setenv("DYNAMODB_ENDPOINT_URL", endpoint)
    monkeypatch.setenv("DYNAMODB_TABLE_PREFIX", "local-probe")
    assert dev.local_database() == endpoint


def test_setup_preserves_files_and_symlinks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(dev, "ROOT", tmp_path)
    backend = tmp_path / "backend"
    backend.mkdir()
    (backend / ".env.example").write_text("example\n")
    target = backend / ".env.local"
    dev.copy_environment()
    assert target.read_text() == "example\n"
    for content in ["custom\n", ""]:
        target.write_text(content)
        before = target.stat().st_mtime_ns
        dev.copy_environment()
        assert target.read_text() == content
        assert target.stat().st_mtime_ns == before
    target.unlink()
    target.symlink_to(backend / "missing")
    dev.copy_environment()
    assert target.is_symlink()
    assert not (backend / "missing").exists()


def test_occupied_port_is_refused() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        with pytest.raises(dev.DevelopmentError, match="unavailable"):
            dev.require_free_port("127.0.0.1", listener.getsockname()[1])
        assert listener.fileno() >= 0


def test_make_targets_delegate_without_implicit_setup() -> None:
    for target in ["setup", "dev", "stop", "check", "browser-smoke"]:
        result = subprocess.run(
            ["make", "--no-print-directory", "-n", target],
            cwd=dev.ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert "--delete" not in result
        assert "down" not in result
        assert "prune" not in result
        if target == "setup":
            assert "uv sync --locked" in result and "development.py setup" in result
        elif target in {"dev", "check"}:
            assert f"development.py {target}" in result
            assert "uv sync" not in result and "npm ci" not in result
        elif target == "stop":
            assert result.strip() == "docker compose stop dynamodb-local"
        else:
            assert result.strip() == "sh tools/run-browser-smoke.sh"


class RecordingRunner(dev.Runner):
    def __init__(self, fail: bool = False) -> None:
        super().__init__()
        self.commands: list[tuple[list[str], Path, dict[str, str] | None]] = []
        self.fail = fail

    def run(
        self, command: list[str], cwd: Path, env: dict[str, str] | None = None
    ) -> None:
        self.commands.append((command, cwd, env))
        if self.fail:
            raise dev.DevelopmentError("fixture failure", 7)


def test_check_order_and_integration_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dev, "local_database", lambda: "http://localhost:8001")
    runner = RecordingRunner()
    dev.check(runner)
    commands = [command for command, _, _ in runner.commands]
    assert [command[4] for command in commands[:5]] == [
        "black",
        "isort",
        "flake8",
        "mypy",
        "pytest",
    ]
    assert commands[5][-2:] == ["pytest", "../tools/tests/"]
    assert commands[6][:3] == ["docker", "compose", "up"]
    assert commands[7][-2:] == ["pytest", "integration_tests/"]
    integration_env = runner.commands[7][2]
    assert integration_env is not None
    assert integration_env["DYNAMODB_TABLE_PREFIX"] == "test-make"
    assert integration_env["DYNAMODB_ENDPOINT_URL"] == "http://localhost:8001"
    assert [command[2] for command in commands[8:]] == [
        "format:check",
        "lint",
        "typecheck",
        "test:coverage",
        "build",
    ]
    failing = RecordingRunner(fail=True)
    with pytest.raises(dev.DevelopmentError) as error:
        dev.check(failing)
    assert error.value.code == 7
    assert len(failing.commands) == 1


STUB = r"""
import http.server, json, os, signal, subprocess, sys, threading, time
from pathlib import Path
from unittest.mock import Mock
name=Path(sys.argv[0]).name
mode=os.environ.get('FIXTURE_MODE','')
root=Path(os.environ['FIXTURE_ROOT'])
with (root/'commands.jsonl').open('a') as out:
 out.write(json.dumps({'name':name,'args':sys.argv[1:],'cwd':os.getcwd()})+'\n')
if name=='docker':sys.exit(19 if mode=='docker-fail' else 0)
if name=='uv' and sys.argv[1]=='sync':sys.exit(29 if mode=='uv-sync-fail' else 0)
if name=='uv' and 'python' in sys.argv:
 index=sys.argv.index('python')
 os.execv(sys.executable,[sys.executable,*sys.argv[index+1:]])
if name=='npm' and sys.argv[1:] == ['ci']:sys.exit(0)
child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
with (root/'pids').open('a') as out:out.write(f'{os.getpid()}\n{child.pid}\n')
def stop(*args):
 child.terminate()
 child.wait()
 sys.exit(0)
signal.signal(signal.SIGTERM,stop)
if mode==name+'-start':sys.exit(17)
if mode==name+'-zero':sys.exit(0)
if mode==name+'-runtime':
 threading.Timer(1.0,lambda:os._exit(23)).start()
if mode==name+'-no-ready':
 while True:time.sleep(.1)
port=int(sys.argv[sys.argv.index('--port')+1])
class Handler(http.server.BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(b'ok')
 def log_message(self,*args):pass
http.server.HTTPServer(('127.0.0.1',port),Handler).serve_forever()
"""


def is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False


def assert_fixture_stopped(root: Path) -> None:
    path = root / "pids"
    pids = [int(value) for value in path.read_text().split()] if path.exists() else []
    deadline = time.monotonic() + 4
    while any(is_alive(pid) for pid in pids) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not [pid for pid in pids if is_alive(pid)]


@pytest.fixture
def cli_fixture(tmp_path: Path) -> Iterator[tuple[Path, dict[str, str]]]:
    root = tmp_path
    for name in ["backend/app", "frontend", "tools", "bin"]:
        (root / name).mkdir(parents=True)
    (root / "Makefile").write_text((dev.ROOT / "Makefile").read_text())
    (root / "backend/.env.example").write_text("fixture=example\n")
    source = (dev.ROOT / "tools/development.py").read_text()
    # Shorten only the fixture deadline; retain the production lifecycle logic.
    (root / "tools/development.py").write_text(
        source.replace("START_TIMEOUT = 60.0", "START_TIMEOUT = 2.0")
    )
    (root / "backend/app/config.py").write_text(
        "import os\nclass Settings:\n"
        " dynamodb_endpoint_url=os.environ['DYNAMODB_ENDPOINT_URL']\n"
        " dynamodb_table_prefix=os.environ['DYNAMODB_TABLE_PREFIX']\n"
    )
    for name in ["uv", "npm", "docker"]:
        executable = root / "bin" / name
        executable.write_text(f"#!{sys.executable}\n" + STUB)
        executable.chmod(0o755)
    env = dict(
        os.environ,
        PATH=f"{root / 'bin'}:{os.environ['PATH']}",
        FIXTURE_ROOT=str(root),
        DYNAMODB_ENDPOINT_URL="http://127.0.0.1:8001",
        DYNAMODB_TABLE_PREFIX="local-fixture",
        HEAT_DEV_API_PORT=str(free_port()),
        HEAT_DEV_FRONTEND_PORT=str(free_port()),
    )
    try:
        yield root, env
    finally:
        path = root / "pids"
        if path.exists():
            for value in path.read_text().split():
                try:
                    os.kill(int(value), signal.SIGTERM)
                except ProcessLookupError:
                    pass


@pytest.mark.parametrize("signum,code", [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_ready_and_signal_cleanup(
    cli_fixture: tuple[Path, dict[str, str]], signum: int, code: int
) -> None:
    root, env = cli_fixture
    with (root / "output").open("w+") as output:
        process = subprocess.Popen(
            [sys.executable, "../tools/development.py", "dev"],
            cwd=root / "backend",
            env=env,
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 8
            while "Ready:" not in (root / "output").read_text():
                assert process.poll() is None, (root / "output").read_text()
                assert time.monotonic() < deadline
                time.sleep(0.05)
            process.send_signal(signum)
            assert process.wait(timeout=10) == code
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
    assert_fixture_stopped(root)


@pytest.mark.parametrize(
    "mode,code",
    [
        ("uv-start", 17),
        ("npm-start", 17),
        ("uv-runtime", 23),
        ("npm-runtime", 23),
        ("uv-zero", 1),
        ("npm-zero", 1),
        ("docker-fail", 19),
        ("uv-no-ready", 1),
    ],
)
def test_failure_cleanup(
    cli_fixture: tuple[Path, dict[str, str]], mode: str, code: int
) -> None:
    root, env = cli_fixture
    env["FIXTURE_MODE"] = mode
    result = subprocess.run(
        [sys.executable, "../tools/development.py", "dev"],
        cwd=root / "backend",
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == code, result.stdout + result.stderr
    assert_fixture_stopped(root)
    if mode == "docker-fail":
        commands = [
            json.loads(line)
            for line in (root / "commands.jsonl").read_text().splitlines()
        ]
        assert [command["name"] for command in commands] == ["docker"]
    if mode == "uv-no-ready":
        assert "Readiness timed out" in result.stderr


def test_no_destructive_database_cleanup() -> None:
    tree = ast.parse((dev.ROOT / "tools/development.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert node.value not in {"down", "prune", "rm", "--volumes"}
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            assert node.func.attr not in {"unlink", "rmdir", "rmtree"}


def test_actual_make_setup_and_repeated_stop(
    cli_fixture: tuple[Path, dict[str, str]],
) -> None:
    root, env = cli_fixture

    def make(target: str) -> None:
        subprocess.run(
            ["make", target],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )

    make("setup")
    target = root / "backend/.env.local"
    assert target.read_text() == "fixture=example\n"
    target.write_text("existing=custom\n")
    before = target.stat().st_mtime_ns
    make("setup")
    assert target.read_text() == "existing=custom\n"
    assert target.stat().st_mtime_ns == before
    make("stop")
    make("stop")
    commands = [
        json.loads(line) for line in (root / "commands.jsonl").read_text().splitlines()
    ]
    assert [item["args"] for item in commands if item["name"] == "docker"] == [
        ["compose", "stop", "dynamodb-local"],
        ["compose", "stop", "dynamodb-local"],
    ]


def test_make_setup_stops_before_copy_or_npm_on_sync_failure(
    cli_fixture: tuple[Path, dict[str, str]],
) -> None:
    root, env = cli_fixture
    env["FIXTURE_MODE"] = "uv-sync-fail"
    result = subprocess.run(
        ["make", "setup"], cwd=root, env=env, capture_output=True, text=True, timeout=15
    )
    assert result.returncode != 0
    assert not (root / "backend/.env.local").exists()
    commands = [
        json.loads(line) for line in (root / "commands.jsonl").read_text().splitlines()
    ]
    assert [item["name"] for item in commands] == ["uv"]


@pytest.mark.parametrize("state", ["", "123 Z\n", "999 S\n123 Z+\n"])
def test_zombie_group_permission_is_not_a_live_process(
    monkeypatch: pytest.MonkeyPatch,
    state: str,
) -> None:
    process = Mock(pid=123)
    monkeypatch.setattr(os, "killpg", Mock(side_effect=PermissionError))
    monkeypatch.setattr(subprocess, "check_output", Mock(return_value=state))
    assert not dev.group_exists(process)
    dev.signal_group(process, signal.SIGTERM)


@pytest.mark.parametrize("operation", ["poll", "signal"])
def test_live_group_permission_failure_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    process = Mock(pid=123)
    monkeypatch.setattr(os, "killpg", Mock(side_effect=PermissionError))
    monkeypatch.setattr(subprocess, "check_output", Mock(return_value="123 S\n"))
    with pytest.raises(PermissionError):
        if operation == "poll":
            dev.group_exists(process)
        else:
            dev.signal_group(process, signal.SIGTERM)
