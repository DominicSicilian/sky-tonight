"""Offline tests for the location resolver (no network required)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sky_tonight.location import (  # noqa: E402
    estimate_limiting_magnitude,
    _match_state,
    resolve_location,
)


def test_limiting_magnitude_monotonic_with_population():
    big = estimate_limiting_magnitude(5_000_000)
    town = estimate_limiting_magnitude(20_000)
    rural = estimate_limiting_magnitude(500)
    assert big < town < rural  # darker (higher mag) as population falls
    assert estimate_limiting_magnitude(None) == 5.0


def test_state_matching_by_abbrev_and_name():
    results = [
        {"name": "Springfield", "admin1": "Illinois", "latitude": 1, "longitude": 1},
        {"name": "Springfield", "admin1": "Massachusetts", "latitude": 2, "longitude": 2},
    ]
    assert _match_state(results, "MA")["admin1"] == "Massachusetts"
    assert _match_state(results, "Illinois")["admin1"] == "Illinois"
    # Unknown state falls back to the first result rather than crashing.
    assert _match_state(results, "ZZ")["admin1"] == "Illinois"


def test_manual_coordinates_skip_network():
    # latitude/longitude present -> resolver must not hit the network.
    cfg = {
        "location_name": "Test Observatory",
        "latitude": 33.0,
        "longitude": -117.0,
        "timezone": "America/Los_Angeles",
        "email_to": "x@y.com",
    }
    out = resolve_location(cfg)
    assert out["latitude"] == 33.0
    assert out["timezone"] == "America/Los_Angeles"
    assert out["location_name"] == "Test Observatory"
    # No population known -> default limiting magnitude.
    assert out["limiting_magnitude"] == 5.0


def test_override_limiting_magnitude_wins():
    cfg = {
        "latitude": 33.0,
        "longitude": -117.0,
        "timezone": "UTC",
        "limiting_magnitude": 6.9,
        "email_to": "x@y.com",
    }
    assert resolve_location(cfg)["limiting_magnitude"] == 6.9
