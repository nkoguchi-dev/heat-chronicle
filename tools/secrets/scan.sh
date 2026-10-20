#!/usr/bin/env bash
set -euo pipefail
umask 077
script_root=$(cd -- "$(dirname -- "$0")/../.." && pwd)
mode=${1:-history}
version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$script_root/tools/secrets/version.json")
secret_cache_root=${XDG_CACHE_HOME:-$HOME/.cache}
binary=${GITLEAKS_BIN:-$secret_cache_root/heat-chronicle-tools/gitleaks-$version/gitleaks}
if [ "$("$binary" version)" != "$version" ]; then
  echo 'Secret scan failed: install the reviewed Gitleaks version' >&2
  exit 2
fi
repo_root=$(git rev-parse --show-toplevel)
case "$mode" in
  history)
    if [ "$(git rev-parse --is-shallow-repository)" != false ]; then
      echo 'Secret scan failed: fetch complete Git history first' >&2
      exit 2
    fi
    options=(git '--log-opts=--all --full-history')
    ;;
  staged) options=(git --pre-commit --staged) ;;
  *) echo 'Usage: scan.sh [history|staged]' >&2; exit 2 ;;
esac
private_dir=$(mktemp -d)
trap 'rm -rf -- "$private_dir"' EXIT
# No baseline, inline allow comment, or repository .gitleaksignore may hide a result.
if "$binary" "${options[@]}" "$repo_root" --config "$script_root/.gitleaks.toml" \
  --gitleaks-ignore-path "$private_dir" --ignore-gitleaks-allow \
  --redact=100 --no-banner --no-color --log-level error --exit-code 10 \
  --report-format json --report-path "$private_dir/report.json" \
  >"$private_dir/scanner.log" 2>&1; then
  scanner_exit=0
else
  scanner_exit=$?
fi
# The raw redacted report can still contain author details; publish an allowlisted summary.
python3 "$script_root/tools/secrets/summarize.py" "$private_dir/report.json" "$scanner_exit" "$mode"
