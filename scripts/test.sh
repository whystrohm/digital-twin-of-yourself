#!/usr/bin/env bash
# Run every check CI runs. Offline. Needs only python3 (3.9 or newer).
#   scripts/test.sh
# Optional: FOUNDRKIT_LINT=/path/to/foundrkit-lint/bin/foundrkit-lint.js scripts/test.sh
# also compares twin_check against the real foundrkit-lint (needs node).
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PYTHON:-python3}"
"$PY" --version

echo "== unit tests"
"$PY" -m unittest discover -s tests -v 2>&1 | tail -n 60

echo "== end to end on the synthetic sample"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
"$PY" scripts/twin_scan.py --corpus examples/sample-corpus --out "$tmp/patterns.json"
"$PY" scripts/twin_report.py "$tmp/patterns.json" --out "$tmp/report.html"
"$PY" scripts/twin_check.py --rules twins/example/twin.rules.json tests/fixtures/drafts/good.md > /dev/null
if "$PY" scripts/twin_check.py --rules twins/example/twin.rules.json tests/fixtures/drafts/bad.md > /dev/null; then
  echo "expected bad.md to fail" >&2; exit 1
fi
"$PY" scripts/twin_diff.py propose examples/edit-pairs --rules twins/example/twin.rules.json --out "$tmp/proposals.md" > /dev/null
"$PY" scripts/twin_check.py --rules twins/example/twin.rules.json --export-foundrkit "$tmp/foundrkit.config.json" > /dev/null
if grep -Eiq 'https?://|@import|url\(' "$tmp/report.html"; then
  echo "report has an external reference" >&2; exit 1
fi
echo "end to end: ok"
