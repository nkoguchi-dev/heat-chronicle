"""Verify the failing gate and real detection in both supported application languages."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scan.py"
SPEC = importlib.util.spec_from_file_location("security_scan", SCRIPT)
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "unsafe.py").write_text("eval(user_input)\n")
        self.result = {
            "check_id": "unsafe-eval",
            "path": "unsafe.py",
            "start": {"offset": 0},
            "end": {"offset": 16},
        }
        self.report = {
            "paths": {"scanned": ["unsafe.py", "client.ts"]},
            "results": [self.result],
            "errors": [],
        }
        self.today = date(2026, 10, 20)
        rule_id, path, digest = scan.fingerprint(self.result, self.root)
        self.exception = {
            "rule_id": rule_id,
            "path": path,
            "match_sha256": digest,
            "reason": "Fixture only",
            "owner": "maintainer",
            "review_by": "2027-01-20",
        }

    def classify(self, exceptions):
        return scan.classify(self.report, exceptions, self.root, self.today)

    def test_new_finding_remains_blocking(self):
        findings, accepted = self.classify([])
        self.assertEqual(findings, [self.result])
        self.assertEqual(accepted, [])

    def test_exact_reviewed_exception(self):
        self.assertEqual(self.classify([self.exception]), ([], [self.result]))

    def test_changed_source_invalidates_exception(self):
        (self.root / "unsafe.py").write_text("exec(user_input)\n")
        with self.assertRaisesRegex(ValueError, "Stale"):
            self.classify([self.exception])

    def test_duplicate_occurrence_is_not_silently_accepted(self):
        self.report["results"].append(deepcopy(self.result))
        findings, accepted = self.classify([self.exception])
        self.assertEqual(len(findings), 1)
        self.assertEqual(len(accepted), 1)

    def test_expired_exception_fails(self):
        self.exception["review_by"] = "2026-10-19"
        with self.assertRaisesRegex(ValueError, "Expired"):
            self.classify([self.exception])

    def test_partial_analysis_fails(self):
        self.report["errors"] = [{"type": "PartialParsing"}]
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.classify([])

    def test_missing_language_fails(self):
        for paths in (["unsafe.py"], ["client.ts"], []):
            self.report["paths"]["scanned"] = paths
            with self.assertRaisesRegex(ValueError, "No .* files analyzed"):
                self.classify([])


@unittest.skipUnless(
    os.environ.get("SECURITY_RULES_DIR"),
    "Set SECURITY_RULES_DIR for real scanner fixtures",
)
class DetectionTests(unittest.TestCase):
    def test_both_languages_detect_injection_and_clean_code_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            python = source / "sample.py"
            typescript = source / "sample.ts"
            command = [
                sys.executable,
                str(SCRIPT),
                "--rules-dir",
                os.environ["SECURITY_RULES_DIR"],
                "--output-dir",
                str(root / "report"),
                "--no-exceptions",
                str(source),
            ]
            python.write_text("def execute(user_input):\n    return eval(user_input)\n")
            typescript.write_text(
                "function execute(userInput: string) { return eval(userInput); }\n"
            )
            vulnerable = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(
                vulnerable.returncode, 1, vulnerable.stdout + vulnerable.stderr
            )
            summary = json.loads((root / "report/summary.json").read_text())
            self.assertGreater(summary["unreviewed_findings"], 0)
            report = json.loads((root / "report/semgrep.json").read_text())
            paths = {Path(result["path"]).suffix for result in report["results"]}
            self.assertIn(".py", paths)
            self.assertIn(".ts", paths)
            python.write_text("def greet(name):\n    return 'Hello ' + name\n")
            typescript.write_text(
                "function greet(name: string) { return 'Hello ' + name; }\n"
            )
            clean = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(clean.returncode, 0, clean.stdout + clean.stderr)


if __name__ == "__main__":
    unittest.main()
