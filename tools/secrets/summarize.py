"""Expose location metadata only; never publish raw scanner output or credentials."""

import json
import os
import sys
from pathlib import Path


def summarize(report_path, scanner_exit, mode):
    if scanner_exit not in (0, 10):
        print("Secret scan failed; scanner did not complete", file=sys.stderr)
        return 2
    findings = json.loads(report_path.read_text())
    if not isinstance(findings, list) or bool(findings) != (scanner_exit == 10):
        print("Secret scan failed; inconsistent scanner result", file=sys.stderr)
        return 2
    summary = {
        "scanner": "gitleaks",
        "version": json.loads(Path(__file__).with_name("version.json").read_text())[
            "version"
        ],
        "mode": mode,
        "findings_count": len(findings),
        "analysis_complete": True,
        "findings": [
            {key: finding[key] for key in ("RuleID", "File", "StartLine", "Commit")}
            for finding in findings
        ],
    }
    text = json.dumps(summary, indent=2) + "\n"
    print(text, end="")
    if os.environ.get("SECRET_SCAN_OUTPUT_DIR"):
        directory = Path(os.environ["SECRET_SCAN_OUTPUT_DIR"])
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        (directory / "summary.json").write_text(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as stream:
            stream.write("## Secret detection\n\n```json\n" + text + "```\n")
    return 1 if findings else 0


if __name__ == "__main__":
    try:
        sys.exit(summarize(Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3]))
    except (ValueError, KeyError, OSError):
        print("Secret scan failed; invalid or missing result", file=sys.stderr)
        sys.exit(2)
