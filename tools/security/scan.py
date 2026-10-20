"""Run pinned local Semgrep rules without logging in or sending source to a service."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "tools/security/config.json"
EXCEPTIONS = ROOT / "tools/security/exceptions.json"


def collect_rules(rules_dir, config):
    commit = subprocess.check_output(
        ["git", "-C", str(rules_dir), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != config["rules_commit"]:
        raise ValueError("Rules checkout does not match pinned commit")
    yaml = YAML(typ="safe")
    rules = []
    for language in config["languages"]:
        language_rules = []
        for path in sorted((rules_dir / language).rglob("*.yaml")):
            relative = path.relative_to(rules_dir)
            if "security" not in relative.parts:
                continue
            for rule in yaml.load(path.read_text())["rules"]:
                # Stable IDs independent of temporary checkout and output paths.
                rule["id"] = ".".join(relative.with_suffix("").parts) + "." + rule["id"]
                language_rules.append(rule)
        if not language_rules:
            raise ValueError(f"No security rules for {language}")
        rules.extend(language_rules)
    if len({rule["id"] for rule in rules}) != len(rules):
        raise ValueError("Duplicate rule IDs")
    return rules


def fingerprint(result, root):
    source = (root / result["path"]).read_bytes()
    matched = source[result["start"]["offset"] : result["end"]["offset"]]
    return result["check_id"], result["path"], hashlib.sha256(matched).hexdigest()


def classify(report, exceptions, root, today):
    if report.get("errors"):
        raise ValueError("Incomplete analysis: reproduce locally to inspect scanner errors")
    scanned = report.get("paths", {}).get("scanned", [])
    if not any(path.endswith(".py") for path in scanned):
        raise ValueError("No Python files analyzed")
    if not any(path.endswith((".ts", ".tsx")) for path in scanned):
        raise ValueError("No TypeScript files analyzed")
    allowed = {}
    for item in exceptions:
        if not item["reason"] or not item["owner"]:
            raise ValueError("Exception needs reason and owner")
        if date.fromisoformat(item["review_by"]) < today:
            raise ValueError("Expired exception")
        key = item["rule_id"], item["path"], item["match_sha256"]
        if key in allowed:
            raise ValueError("Duplicate exception")
        allowed[key] = item
    findings = []
    accepted = []
    for result in report["results"]:
        key = fingerprint(result, root)
        if key in allowed:
            allowed.pop(key)  # One exception cannot allow two identical occurrences.
            accepted.append(result)
        else:
            findings.append(result)
    if allowed:
        raise ValueError("Stale exception: remove or re-evaluate it")
    return findings, accepted


def analyze(args, config, rules):
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in ("semgrep.json", "semgrep.sarif", "scanner.log", "summary.json"):
        (output / name).unlink(missing_ok=True)
    rule_file = output / "rules.json"
    rule_file.write_text(json.dumps({"rules": rules}))
    command = [
        str(Path(sys.executable).parent / "semgrep"),
        "scan",
        "--config",
        str(rule_file),
        "--metrics",
        "off",
        "--disable-version-check",
        "--disable-nosem",
        "--strict",
        "--error",
        "--quiet",
        "--no-rewrite-rule-ids",
        "--json-output",
        str(output / "semgrep.json"),
        "--sarif-output",
        str(output / "semgrep.sarif"),
    ]
    for excluded in config["excluded_paths"]:
        command.extend(["--exclude", excluded])
    command.extend(["--exclude", str(output)])
    command.extend(args.targets or ["."])
    env = {
        **os.environ,
        "SEMGREP_SEND_METRICS": "off",
        "SEMGREP_ENABLE_VERSION_CHECK": "0",
    }
    # Do not inherit a developer's Semgrep platform credentials.
    env.pop("SEMGREP_APP_TOKEN", None)
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    (output / "scanner.log").write_text(result.stdout + "\n" + result.stderr)
    if result.returncode not in (0, 1):
        raise ValueError(
            f"Scanner failed with exit {result.returncode}; reproduce locally to inspect details"
        )
    report = json.loads((output / "semgrep.json").read_text())
    if result.returncode == 1 and not report.get("results"):
        raise ValueError("Scanner failed without findings; reproduce locally to inspect details")
    return report


def run(args):
    config = json.loads(CONFIG.read_text())
    if importlib.metadata.version("semgrep") != config["semgrep_version"]:
        raise ValueError("Install the pinned security requirements first")
    rules = collect_rules(args.rules_dir.resolve(), config)
    report = analyze(args, config, rules)
    exceptions = json.loads(EXCEPTIONS.read_text()) if not args.no_exceptions else []
    findings, accepted = classify(report, exceptions, ROOT, date.today())
    counts = {
        "python": sum(path.endswith(".py") for path in report["paths"]["scanned"]),
        "typescript": sum(
            path.endswith((".ts", ".tsx")) for path in report["paths"]["scanned"]
        ),
        "javascript": sum(
            path.endswith((".js", ".jsx", ".mjs", ".cjs"))
            for path in report["paths"]["scanned"]
        ),
    }
    summary = {
        "semgrep_version": config["semgrep_version"],
        "rules_commit": config["rules_commit"],
        "rule_count": len(rules),
        "scanned_files": counts,
        "unreviewed_findings": len(findings),
        "reviewed_exceptions": len(accepted),
        "analysis_errors": 0,
    }
    (args.output_dir.resolve() / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n"
    )
    print(json.dumps(summary, indent=2))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write(
                "## Code security scan\n\n```json\n"
                + json.dumps(summary, indent=2)
                + "\n```\n"
            )
    return 1 if findings else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--no-exceptions", action="store_true")
    parser.add_argument("targets", nargs="*")
    try:
        sys.exit(run(parser.parse_args()))
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print(f"Security scan failed: {error}", file=sys.stderr)
        sys.exit(2)
