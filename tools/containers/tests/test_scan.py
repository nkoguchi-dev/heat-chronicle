import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "scan.py"
spec = importlib.util.spec_from_file_location("container_scan", SOURCE)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


def report():
    return {
        "SchemaVersion": 2,
        "Metadata": {
            "ImageID": "sha256:" + "0" * 64,
            "OS": {"Family": "amazon", "EOSL": False},
        },
        "Results": [
            {"Class": "os-pkgs", "Type": "amazon", "Packages": [{"Name": "rpm"}]},
            {
                "Class": "lang-pkgs",
                "Type": "python-pkg",
                "Packages": [{"Name": "fastapi"}],
            },
        ],
    }


class GateTests(unittest.TestCase):
    def test_clean_inventory_passes(self):
        self.assertTrue(scan.evaluate(report())[0]["passed"])

    def test_high_and_critical_block_even_without_a_fix(self):
        for severity in ["HIGH", "CRITICAL"]:
            for fixed in ["", "2.0"]:
                with self.subTest(severity=severity, fixed=fixed):
                    value = report()
                    value["Results"][0]["Vulnerabilities"] = [
                        {"Severity": severity, "FixedVersion": fixed}
                    ]
                    self.assertFalse(scan.evaluate(value)[0]["passed"])

    def test_lower_severities_remain_visible(self):
        value = report()
        value["Results"][0]["Vulnerabilities"] = [
            {"Severity": s} for s in ["UNKNOWN", "LOW", "MEDIUM"]
        ]
        summary, findings = scan.evaluate(value)
        self.assertTrue(summary["passed"])
        self.assertEqual(len(findings), 3)
        self.assertEqual(
            summary["severity_counts"], {"UNKNOWN": 1, "LOW": 1, "MEDIUM": 1}
        )

    def test_any_secret_blocks_without_publishing_match_or_code(self):
        value = report()
        value["Results"][0]["Secrets"] = [
            {
                "Severity": "LOW",
                "RuleID": "fixture",
                "Match": "DO_NOT_PUBLISH",
                "Code": {"Lines": [{"Content": "DO_NOT_PUBLISH"}]},
                "UnrecognizedNewField": "DO_NOT_PUBLISH",
            }
        ]
        summary, findings = scan.evaluate(value)
        self.assertFalse(summary["passed"])
        self.assertNotIn("DO_NOT_PUBLISH", json.dumps(findings))

    def test_missing_inventory_eosl_and_schema_fail_closed(self):
        invalid = [{}, {"SchemaVersion": 2, "Results": []}]
        for index in [0, 1]:
            value = report()
            value["Results"].pop(index)
            invalid.append(value)
        value = report()
        value["Metadata"]["OS"]["EOSL"] = True
        invalid.append(value)
        value = report()
        value["Results"][0]["Vulnerabilities"] = [{"Severity": "UNRECOGNIZED"}]
        invalid.append(value)
        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    scan.evaluate(value)

    def test_cli_failure_removes_stale_success_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ["summary.json", "findings.json", "sbom.cdx.json"]:
                (root / name).write_text("stale")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SOURCE),
                    "--trivy",
                    str(root / "missing"),
                    "--image",
                    "unused",
                    "--output-dir",
                    str(root),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(
                json.loads((root / "summary.json").read_text())["analysis_complete"]
            )
            self.assertFalse((root / "sbom.cdx.json").exists())
            self.assertFalse((root / "findings.json").exists())

    def test_unreviewed_archive_is_rejected_before_installation(self):
        import io

        installer_spec = importlib.util.spec_from_file_location(
            "container_install", SOURCE.with_name("install.py")
        )
        installer = importlib.util.module_from_spec(installer_spec)
        installer_spec.loader.exec_module(installer)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                installer.platform, "system", return_value="Linux"
            ), patch.object(
                installer.platform, "machine", return_value="x86_64"
            ), patch.object(
                installer.urllib.request,
                "urlopen",
                return_value=io.BytesIO(b"unreviewed archive"),
            ):
                with self.assertRaisesRegex(ValueError, "checksum"):
                    installer.install(Path(directory))
            self.assertFalse((Path(directory) / "trivy").exists())

    @unittest.skipUnless(
        os.environ.get("TRIVY_BIN"),
        "Provide pinned Trivy for the actual detection fixture",
    )
    def test_actual_scanner_detects_synthetic_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Synthetic credential, assembled only in the temporary fixture.
            (root / "credentials.env").write_text(
                'aws_access_key_id = "' + "AKIA" + "7Q6F2M5N8P4R9S3T" + '"\n'
            )
            output = root.parent / (root.name + "-report.json")
            try:
                subprocess.run(
                    [
                        os.environ["TRIVY_BIN"],
                        "fs",
                        "--scanners",
                        "secret",
                        "--offline-scan",
                        "--format",
                        "json",
                        "--output",
                        str(output),
                        str(root),
                    ],
                    capture_output=True,
                    check=True,
                )
                found = sum(
                    len(r.get("Secrets", []))
                    for r in json.loads(output.read_text()).get("Results", [])
                )
                self.assertGreater(found, 0)
            finally:
                output.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
