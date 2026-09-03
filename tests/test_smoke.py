"""Smoke tests: the engine runs and returns a well-formed report.

Requires data/de421.bsp (run scripts/fetch_ephemeris.py first).
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sky_tonight.compute import SiteConfig, compute_night  # noqa: E402

pytestmark = pytest.mark.skipif(
    not (ROOT / "data" / "de421.bsp").exists(),
    reason="ephemeris not downloaded; run scripts/fetch_ephemeris.py",
)

CFG = SiteConfig.from_dict(
    {
        "location_name": "Test City",
        "latitude": 40.0,
        "longitude": -75.0,
        "elevation_m": 0,
        "timezone": "America/New_York",
    }
)


def test_report_shape():
    r = compute_night(CFG)
    assert set(["night", "moon", "objects", "counts", "location"]) <= set(r)
    assert r["counts"]["visible"] <= r["counts"]["evaluated"]
    assert 0 <= r["moon"]["illumination_pct"] <= 100
    assert r["night"]["darkness_hours"] >= 0


def test_objects_are_above_horizon():
    r = compute_night(CFG)
    for o in r["objects"]:
        assert o["visible"] is True
        assert o["max_altitude_deg"] >= CFG.min_altitude_deg


def test_transit_altitude_matches_geometry():
    # A high-declination object near the meridian should transit near 90-|lat-dec|.
    r = compute_night(CFG)
    by_id = {o["id"]: o for o in r["objects"]}
    if "M31" in by_id:  # dec +41.27, at lat 40 -> transit ~89
        assert by_id["M31"]["transit_altitude_deg"] > 85


def test_json_serialisable():
    r = compute_night(CFG)
    json.dumps(r)  # must not raise
