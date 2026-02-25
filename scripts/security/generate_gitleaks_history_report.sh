#!/usr/bin/env bash
set -euo pipefail

REPORT_PATH="/tmp/gitleaks-history.json"

echo "Running full-history gitleaks scan..."
gitleaks git . --log-opts="--all" \
  --report-format json \
  --report-path "${REPORT_PATH}"

echo
echo "Scan complete."
echo "Report written to: ${REPORT_PATH}"
echo

if ! command -v jq >/dev/null 2>&1; then
  echo "jq not found. Install jq to extract unique literals."
  exit 0
fi

echo "Extracting unique secret literals..."
jq -r '.[] | .Secret' "${REPORT_PATH}" \
  | sort \
  | uniq > /tmp/gitleaks-unique-secrets.txt

echo
echo "Unique literals written to:"
echo "  /tmp/gitleaks-unique-secrets.txt"
echo
echo "Sample output:"
head -n 10 /tmp/gitleaks-unique-secrets.txt || true
