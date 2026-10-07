#!/bin/bash
# Compatibility entry point. All sending must pass the durable issue guard.
set -euo pipefail
BASE="$(cd "$(dirname "$0")" && pwd)"
case "${1:-}" in
  prepare) exec python3 "$BASE/report_jobs.py" collect ;;
  finalize) exec python3 "$BASE/report_jobs.py" daily ;;
  *) echo "usage: pipeline.sh {prepare|finalize}" >&2; exit 2 ;;
esac
