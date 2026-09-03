#!/usr/bin/env bash
# One-time setup: create a virtualenv, install deps, download the ephemeris.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Creating virtualenv (.venv)"
python3 -m venv .venv
./.venv/bin/python -m pip install --quiet --upgrade pip
echo "==> Installing dependencies"
./.venv/bin/python -m pip install --quiet -r requirements.txt
echo "==> Downloading DE421 ephemeris (~17 MB)"
./.venv/bin/python scripts/fetch_ephemeris.py

if [ ! -f config.json ]; then
  cp config.example.json config.json
  echo "==> Created config.json from the example — EDIT IT: set your city + state (+ optional zip) and email_to."
fi

echo ""
echo "Setup complete. Try it:"
echo "    ./.venv/bin/python tonight.py --config config.json | head -40"
