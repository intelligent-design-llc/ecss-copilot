#!/usr/bin/env bash
# One-command start: creates a local venv on first run, installs deps, starts the app on http://127.0.0.1:8000
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements-dev.txt
fi
exec .venv/bin/python -m ecss_copilot
