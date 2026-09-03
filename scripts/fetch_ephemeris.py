#!/usr/bin/env python3
"""Download the JPL DE421 planetary ephemeris into data/de421.bsp (~17 MB).

Run once during setup. The file is used offline by the sky engine, so daily
scheduled runs never touch the network for ephemeris data.
"""
from __future__ import annotations

import sys
from pathlib import Path

from skyfield.api import Loader

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def main() -> int:
    DATA_DIR.mkdir(exist_ok=True)
    load = Loader(str(DATA_DIR))
    target = DATA_DIR / "de421.bsp"
    if target.exists():
        print(f"Ephemeris already present: {target}")
        return 0
    print("Downloading DE421 ephemeris (~17 MB) ...")
    load("de421.bsp")  # downloads into DATA_DIR
    print(f"Saved: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
