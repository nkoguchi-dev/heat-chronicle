"""Use upstream-style generated samples only; no issued credential or provider request."""

import contextlib
import importlib.util
import io
import json
import os
import secrets
import shutil
import string
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "secret_summary", ROOT / "tools/secrets/summarize.py"
)
summary = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(summary)


def synthetic_token():
    # Same sample construction as upstream GitHubPat() validation, never issued by GitHub.
    return "ghp_" + "".join(
        secrets.choice(string.ascii_letters + string.digits) for _ in range(36)
    )


class InstallerTests(unittest.TestCase):
    def test_bad_archive_is_rejected_before_writing_executable(self):
        spec = importlib.util.spec_from_file_location(
            "secret_install", ROOT / "tools/secrets/install.py"
        )
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "bin"
            with patch.object(
                installer.platform, "system", return_value="Linux"
            ), patch.object(
                installer.platform, "machine", return_value="x86_64"
            ), patch.object(
                installer.urllib.request,
                "urlopen",
                return_value=io.BytesIO(b"invalid archive"),
            ):
                with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                    installer.install(target)
            self.assertFalse(target.exists())


class SummaryTests(unittest.TestCase):
    def test_raw_fields_never_reach_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory) / "report.json"
            report.write_text(
                json.dumps(
                    [
                        {
                            "RuleID": "sample",
                            "File": "sample.txt",
                            "StartLine": 1,
                            "Commit": "sample",
                            "Secret": "DO_NOT_PUBLISH",
                            "Match": "DO_NOT_PUBLISH",
                            "Email": "private@example.invalid",
                            "Author": "DO_NOT_PUBLISH",
                        }
                    ]
                )
            )
            output = io.StringIO()
            with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stdout(
                output
            ):
                code = summary.summarize(report, 10, "staged")
            self.assertEqual(code, 1)
            self.assertNotIn("DO_NOT_PUBLISH", output.getvalue())
            self.assertNotIn("private@example.invalid", output.getvalue())
            self.assertEqual(json.loads(output.getvalue())["findings_count"], 1)

    def test_tool_error_is_not_a_clean_scan(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(summary.summarize(Path("does-not-exist"), 2, "history"), 2)


@unittest.skipUnless(
    os.environ.get("GITLEAKS_BIN"), "Set GITLEAKS_BIN for real scanner tests"
)
class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        self.env = {
            key: value
            for key, value in os.environ.items()
            if key not in ("GITHUB_STEP_SUMMARY", "SECRET_SCAN_OUTPUT_DIR")
        }
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Secret scanner fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        for name in ("scan.sh", "summarize.py", "version.json"):
            destination = self.repo / "tools/secrets" / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / "tools/secrets" / name, destination)
        shutil.copy2(ROOT / ".gitleaks.toml", self.repo / ".gitleaks.toml")
        shutil.copytree(ROOT / ".githooks", self.repo / ".githooks")
        (self.repo / "sample.txt").write_text("hello\n")
        self.git("add", "sample.txt")
        self.git("commit", "-m", "clean fixture")
        self.git("config", "core.hooksPath", ".githooks")

    def git(self, *args):
        result = subprocess.run(
            ["git", *args], cwd=self.repo, env=self.env, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout.strip()

    def test_real_precommit_rejects_sample_and_clean_commit_passes(self):
        token = synthetic_token()
        (self.repo / "sample.txt").write_text("token = " + token + "\n")
        self.git("add", "sample.txt")
        blocked = subprocess.run(
            ["git", "commit", "-m", "blocked fixture"],
            cwd=self.repo,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn('"findings_count": 1', blocked.stdout + blocked.stderr)
        self.assertNotIn(token, blocked.stdout + blocked.stderr)
        (self.repo / "sample.txt").write_text("hello again\n")
        self.git("add", "sample.txt")
        self.git("commit", "-m", "clean fixture update")

    def test_real_prepush_rejects_local_bare_remote_without_sending_commit(self):
        remote = Path(self.temp.name) / "remote.git"
        self.git("init", "--bare", str(remote))
        self.git("remote", "add", "origin", str(remote))
        self.git("push", "origin", "main")
        clean = self.git("rev-parse", "HEAD")
        (self.repo / "sample.txt").write_text("token = " + synthetic_token() + "\n")
        self.git("add", "sample.txt")
        # Simulate bypassing pre-commit, then verify pre-push still rejects it.
        self.git(
            "-c", "core.hooksPath=/dev/null", "commit", "-m", "blocked push fixture"
        )
        blocked = subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=self.repo,
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(blocked.returncode, 0)
        self.assertIn('"findings_count": 1', blocked.stdout + blocked.stderr)
        received = subprocess.check_output(
            ["git", "--git-dir", str(remote), "rev-parse", "refs/heads/main"], text=True
        ).strip()
        self.assertEqual(received, clean)

    def test_custom_patterns_and_public_recipient_allowlist(self):
        examples = [
            ("AGE-SECRET-" + "KEY-1" + "A" * 58, "heat-age-private-key"),
            (
                "https://discord.com/api/" + "webhooks/" + "0" * 18 + "/" + "A" * 64,
                "heat-discord-webhook",
            ),
            ("# public key: age1" + "a" * 58, None),
        ]
        for value, expected_rule in examples:
            with self.subTest(rule=expected_rule):
                (self.repo / "sample.txt").write_text(value + "\n")
                self.git("add", "sample.txt")
                result = subprocess.run(
                    ["bash", str(self.repo / "tools/secrets/scan.sh"), "staged"],
                    cwd=self.repo,
                    env=self.env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    1 if expected_rule else 0,
                    result.stdout + result.stderr,
                )
                if expected_rule:
                    self.assertIn(expected_rule, result.stdout)
                    self.assertNotIn(value, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
