"""Offline unit tests for the weather classifier (synthetic data, no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sky_tonight.weather import _categorize, _windows  # noqa: E402


def test_categorize():
    assert _categorize(5, 0, 0) == "clear"
    assert _categorize(50, 0, 2) == "partly"
    assert _categorize(90, 0, 3) == "cloudy"
    assert _categorize(10, 0, 61) == "cloudy"   # rain code overrides low cloud
    assert _categorize(10, 0.5, 0) == "cloudy"  # measured precip overrides


def test_windows_contiguous_and_split():
    hrs = [
        {"time": "21:00", "cat": "clear"},
        {"time": "22:00", "cat": "clear"},
        {"time": "23:00", "cat": "cloudy"},
        {"time": "00:00", "cat": "clear"},
    ]
    w = _windows(hrs, {"clear"})
    assert w[0] == {"start": "21:00", "end": "23:00"}   # clear run ends where cloudy begins
    assert w[1] == {"start": "00:00", "end": "01:00"}   # trailing run -> next hour


def test_windows_empty_when_none_match():
    hrs = [{"time": "21:00", "cat": "cloudy"}, {"time": "22:00", "cat": "cloudy"}]
    assert _windows(hrs, {"clear"}) == []
