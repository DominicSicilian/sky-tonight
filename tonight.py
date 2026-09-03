#!/usr/bin/env python3
"""CLI: print tonight's visible-sky report as JSON.

Usage:
    .venv/bin/python tonight.py                 # uses ./config.json
    .venv/bin/python tonight.py --config path   # custom config
    .venv/bin/python tonight.py --date 2026-09-15   # simulate another night
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sky_tonight.compute import SiteConfig, compute_night  # noqa: E402

ROOT = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser(description="Tonight's visible-sky report (JSON).")
    ap.add_argument("--config", default=str(ROOT / "config.json"))
    ap.add_argument("--date", help="YYYY-MM-DD to simulate a specific night (optional).")
    args = ap.parse_args()

    cfg_path = Path(args.config)
    if not cfg_path.exists():
        sys.stderr.write(
            f"Config not found: {cfg_path}\n"
            "Copy config.example.json to config.json and set your location.\n"
        )
        return 2

    cfg = SiteConfig.from_dict(json.loads(cfg_path.read_text()))

    when = None
    if args.date:
        tz = ZoneInfo(cfg.timezone)
        d = datetime.strptime(args.date, "%Y-%m-%d")
        when = datetime(d.year, d.month, d.day, 20, 0, tzinfo=tz)  # evening anchor

    report = compute_night(cfg, when=when)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
