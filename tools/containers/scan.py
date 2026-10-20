"""Scan the final image, fail closed and publish only allowlisted finding fields."""

import argparse
import json
import os
import subprocess
import tempfile
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def evaluate(report):
    if report.get("SchemaVersion") != 2 or not isinstance(report.get("Results"), list):
        raise ValueError("Missing or unsupported Trivy report")
    metadata = report.get("Metadata", {})
    if not metadata.get("ImageID") or not metadata.get("OS", {}).get("Family"):
        raise ValueError("Missing image identity or OS metadata")
    results = report["Results"]
    if any(not isinstance(result, dict) for result in results):
        raise ValueError("Invalid result schema")
    os_coverage = any(
        r.get("Class") == "os-pkgs"
        and isinstance(r.get("Packages"), list)
        and r["Packages"]
        for r in results
    )
    python_coverage = any(
        r.get("Type") == "python-pkg"
        and isinstance(r.get("Packages"), list)
        and r["Packages"]
        for r in results
    )
    if (
        not os_coverage
        or not python_coverage
        or report.get("Metadata", {}).get("OS", {}).get("EOSL")
    ):
        raise ValueError("Missing OS/Python inventory or unsupported OS lifecycle")
    findings = []
    severities = Counter()
    secrets = 0
    blocking = 0
    for result in results:
        for vulnerability in result.get("Vulnerabilities", []):
            severity = vulnerability["Severity"]
            if severity not in {"UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                raise ValueError("Unknown severity schema")
            severities[severity] += 1
            blocking += severity in {"HIGH", "CRITICAL"}
            findings.append(
                {
                    "kind": "vulnerability",
                    "type": result.get("Type"),
                    **{
                        k: vulnerability.get(k)
                        for k in [
                            "VulnerabilityID",
                            "PkgName",
                            "InstalledVersion",
                            "FixedVersion",
                            "Severity",
                            "Status",
                        ]
                    },
                }
            )
        for secret in result.get("Secrets", []):
            secrets += 1
            # Never copy Match, Code or an unrecognized scanner field.
            findings.append(
                {
                    "kind": "secret",
                    **{
                        k: secret.get(k)
                        for k in [
                            "RuleID",
                            "Category",
                            "Severity",
                            "Title",
                            "StartLine",
                            "EndLine",
                        ]
                    },
                }
            )
    summary = {
        "analysis_complete": True,
        "os_inventory": True,
        "python_inventory": True,
        "image_id": report.get("Metadata", {}).get("ImageID"),
        "severity_counts": dict(severities),
        "blocking_vulnerabilities": blocking,
        "secret_count": secrets,
        "passed": blocking == 0 and secrets == 0,
    }
    return summary, findings


def scan(binary, image, output, cache):
    version = json.loads((HERE / "version.json").read_text())["version"]
    actual = subprocess.run(
        [binary, "--version"], capture_output=True, text=True, check=True
    )
    if actual.stdout.partition("\n")[0].strip() != f"Version: {version}":
        raise ValueError("Unexpected Trivy version")
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("TRIVY_")
    }
    with tempfile.TemporaryDirectory(prefix="container-scan-") as directory:
        raw = Path(directory) / "raw.json"
        config = Path(directory) / "config.yaml"
        ignore = Path(directory) / "empty.ignore"
        config.write_text("{}\n")
        ignore.write_text("")
        common = [
            binary,
            "image",
            "--image-src",
            "docker",
            "--platform",
            "linux/amd64",
            "--config",
            str(config),
            "--ignorefile",
            str(ignore),
            "--cache-dir",
            str(cache),
            "--timeout",
            "10m",
        ]
        command = common + [
            "--ignore-unfixed=false",
            "--scanners",
            "vuln,secret",
            "--list-all-pkgs",
            "--format",
            "json",
            "--output",
            str(raw),
            image,
        ]
        subprocess.run(command, capture_output=True, check=True, env=environment)
        summary, findings = evaluate(json.loads(raw.read_text()))
        metadata = json.loads((cache / "db" / "metadata.json").read_text())
        updated = datetime.fromisoformat(metadata["UpdatedAt"].replace("Z", "+00:00"))
        if datetime.now(timezone.utc) - updated > timedelta(hours=48):
            raise ValueError("Vulnerability DB is older than 48 hours")
        summary["scanner_version"] = version
        summary["database_updated_at"] = metadata["UpdatedAt"]
        (output / "findings.json").write_text(json.dumps(findings, indent=2) + "\n")
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        if not summary["secret_count"]:
            subprocess.run(
                common
                + [
                    "--format",
                    "cyclonedx",
                    "--output",
                    str(output / "sbom.cdx.json"),
                    image,
                ],
                capture_output=True,
                check=True,
                env=environment,
            )
            sbom = json.loads((output / "sbom.cdx.json").read_text())
            if sbom.get("bomFormat") != "CycloneDX" or not sbom.get("components"):
                raise ValueError("Missing SBOM inventory")
        return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trivy", required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Prevent stale evidence from an earlier invocation appearing successful.
    for name in ["summary.json", "findings.json", "sbom.cdx.json"]:
        (output / name).unlink(missing_ok=True)
    try:
        summary = scan(
            args.trivy, args.image, output, args.cache_dir or output / "cache"
        )
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        IndexError,
        subprocess.SubprocessError,
    ):
        summary = {
            "analysis_complete": False,
            "passed": False,
            "error": "Scanner, inventory, database or SBOM generation failed",
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
