"""Live hourly cloud/precip forecast for tonight's darkness window (Open-Meteo).

Purely additive: this never changes which objects are astronomically visible. It
annotates the night with when the sky is expected to be clear, and flags nights that
are likely a washout. Requires network at run time; failures degrade gracefully to
{"fetched": False} so the briefing still goes out.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime

USER_AGENT = "sky-tonight/0.1 (https://github.com/DominicSicilian/sky-tonight)"
TIMEOUT = 12

# Cloud-cover thresholds (percent).
CLEAR_MAX = 30      # below this = clear
PARTLY_MAX = 70     # below this = partly cloudy; at/above = cloudy

# WMO weather codes -> short human descriptions.
WMO = {
    0: "clear", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "freezing fog",
    51: "light drizzle", 53: "drizzle", 55: "heavy drizzle",
    56: "freezing drizzle", 57: "freezing drizzle",
    61: "light rain", 63: "rain", 65: "heavy rain",
    66: "freezing rain", 67: "freezing rain",
    71: "light snow", 73: "snow", 75: "heavy snow", 77: "snow grains",
    80: "rain showers", 81: "rain showers", 82: "violent rain showers",
    85: "snow showers", 86: "snow showers",
    95: "thunderstorm", 96: "thunderstorm with hail", 99: "thunderstorm with hail",
}
PRECIP_CODES = set(range(51, 100))   # drizzle/rain/snow/showers/thunderstorm
STORM_CODES = {95, 96, 99}
FOG_CODES = {45, 48}


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _categorize(cloud: float, precip: float, code: int) -> str:
    if code in PRECIP_CODES or precip and precip > 0.05:
        return "cloudy"
    if cloud < CLEAR_MAX:
        return "clear"
    if cloud < PARTLY_MAX:
        return "partly"
    return "cloudy"


def _windows(hours: list[dict], cats: set[str]) -> list[dict]:
    """Contiguous runs of hours whose category is in `cats`, as HH:MM ranges.
    The end is the start of the hour after the last matching hour (exclusive)."""
    out: list[dict] = []
    run_start = None
    for i, h in enumerate(hours):
        if h["cat"] in cats:
            if run_start is None:
                run_start = h["time"]
        else:
            if run_start is not None:
                out.append({"start": run_start, "end": hours[i]["time"]})
                run_start = None
    if run_start is not None:
        # Run extends to the end of the darkness window; label the final hour's end.
        last = hours[-1]
        end = f"{(int(last['time'][:2]) + 1) % 24:02d}:00"
        out.append({"start": run_start, "end": end})
    return out


def fetch_weather(latitude, longitude, timezone, dark_start_local, dark_end_local):
    """Return a weather dict for the darkness window, or a graceful failure dict.

    dark_start_local / dark_end_local are tz-aware local datetimes bounding darkness.
    """
    if dark_start_local is None or dark_end_local is None:
        return {"fetched": False, "note": "no darkness window"}
    q = urllib.parse.urlencode(
        {
            "latitude": round(float(latitude), 4),
            "longitude": round(float(longitude), 4),
            "hourly": "cloud_cover,precipitation,weather_code",
            "timezone": timezone,
            "forecast_days": 2,
        }
    )
    try:
        data = _get_json(f"https://api.open-meteo.com/v1/forecast?{q}")
        h = data["hourly"]
        times, clouds = h["time"], h["cloud_cover"]
        precs, codes = h["precipitation"], h["weather_code"]
    except Exception as e:
        return {"fetched": False, "note": f"weather unavailable ({type(e).__name__})"}

    # Floor the start to the hour so the hour that CONTAINS darkness-onset is included
    # (e.g. darkness at 21:02 should still count the 21:00–22:00 forecast hour).
    start_floor = dark_start_local.replace(minute=0, second=0, microsecond=0)

    hours: list[dict] = []
    for t, c, p, wc in zip(times, clouds, precs, codes):
        dt = datetime.strptime(t, "%Y-%m-%dT%H:%M").replace(tzinfo=dark_start_local.tzinfo)
        if start_floor <= dt <= dark_end_local:
            c = float(c if c is not None else 0)
            p = float(p if p is not None else 0)
            wc = int(wc if wc is not None else 0)
            hours.append(
                {
                    "time": dt.strftime("%H:%M"),
                    "cloud_cover": round(c),
                    "precip_mm": round(p, 2),
                    "code": wc,
                    "desc": WMO.get(wc, "unknown"),
                    "cat": _categorize(c, p, wc),
                }
            )

    if not hours:
        return {"fetched": False, "note": "no forecast hours in darkness window"}

    clear_windows = _windows(hours, {"clear"})
    good_windows = _windows(hours, {"clear", "partly"})
    n = len(hours)
    n_clear = sum(1 for x in hours if x["cat"] == "clear")
    n_cloudy = sum(1 for x in hours if x["cat"] == "cloudy")
    n_precip = sum(1 for x in hours if x["code"] in PRECIP_CODES or x["precip_mm"] > 0.05)
    clouds_only = [x["cloud_cover"] for x in hours]

    # Overall verdict.
    viewing_unlikely = (n_clear == 0) and (n_cloudy / n >= 0.6 or n_precip / n >= 0.3)

    # Dominant adverse condition for the reason string.
    storm = any(x["code"] in STORM_CODES for x in hours)
    fog = any(x["code"] in FOG_CODES for x in hours)
    reason = None
    if viewing_unlikely:
        lo, hi = min(clouds_only), max(clouds_only)
        if storm:
            reason = f"thunderstorms expected; {lo}–{hi}% cloud cover through the night"
        elif n_precip:
            first_precip = next(x["time"] for x in hours if x["code"] in PRECIP_CODES or x["precip_mm"] > 0.05)
            reason = f"precipitation (from ~{first_precip}) with {lo}–{hi}% cloud cover"
        elif fog:
            reason = f"fog with {lo}–{hi}% cloud cover"
        else:
            reason = f"overcast, {lo}–{hi}% cloud cover all night"

    if viewing_unlikely:
        summary = "viewing unlikely"
    elif not clear_windows and good_windows:
        summary = "mostly cloudy, brief breaks"
    elif len(clear_windows) == 1 and n_clear >= 0.7 * n:
        summary = "clear most of the night"
    elif clear_windows:
        summary = "clear at times"
    else:
        summary = "cloudy"

    return {
        "fetched": True,
        "source": "open-meteo",
        "summary": summary,
        "viewing_unlikely": viewing_unlikely,
        "reason": reason,
        "clear_windows": clear_windows,
        "good_windows": good_windows,
        "cloud_cover_min_pct": min(clouds_only),
        "cloud_cover_max_pct": max(clouds_only),
        "hours": hours,
    }
