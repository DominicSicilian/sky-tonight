#!/usr/bin/env bash
# Stable entrypoint for the daily routine: prints tonight's sky report as JSON.
# One fixed command so a permission allow-rule matches every run.
set -euo pipefail
cd "$(dirname "$0")/.."
# Self-heal if the environment isn't set up yet (first run on a fresh machine).
if [ ! -x .venv/bin/python ] || [ ! -f data/de421.bsp ]; then
  bash scripts/setup.sh >&2
fi
exec .venv/bin/python tonight.py --config config.json
