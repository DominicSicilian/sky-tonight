"""Compute what is visible in the local sky tonight.

Pure, deterministic astronomy. Produces a structured dict (JSON-serialisable)
describing the coming night and every object that clears the horizon during
darkness. It does NOT decide what is "interesting" -- that ranking is left to
Claude (Sonnet) in the Cowork skill, which reads this output.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from skyfield import almanac
from skyfield.api import Loader, Star, wgs84
from skyfield.magnitudelib import planetary_magnitude

from .catalog import PLANETS, FixedObject, load_fixed_objects
from .weather import fetch_weather

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# Sun-altitude threshold (degrees below horizon) that defines "dark enough".
TWILIGHT_THRESHOLDS = {"civil": 6.0, "nautical": 12.0, "astronomical": 18.0}

# Sampling resolution across the night.
STEP_MINUTES = 2


@dataclass
class SiteConfig:
    location_name: str
    latitude: float
    longitude: float
    elevation_m: float
    timezone: str
    min_altitude_deg: float = 15.0
    limiting_magnitude: float = 6.5
    twilight: str = "astronomical"
    email_to: str = ""
    weather: bool = True

    @classmethod
    def from_dict(cls, d: dict) -> "SiteConfig":
        return cls(
            location_name=d["location_name"],
            latitude=float(d["latitude"]),
            longitude=float(d["longitude"]),
            elevation_m=float(d.get("elevation_m", 0)),
            timezone=d["timezone"],
            min_altitude_deg=float(d.get("min_altitude_deg", 15.0)),
            limiting_magnitude=float(d.get("limiting_magnitude", 6.5)),
            twilight=str(d.get("twilight", "astronomical")).lower(),
            email_to=d.get("email_to", ""),
            weather=bool(d.get("weather", True)),
        )


def _fmt_local(t_utc: datetime | None, tz: ZoneInfo) -> str | None:
    if t_utc is None:
        return None
    return t_utc.astimezone(tz).strftime("%H:%M")


def _phase_name(illum: float, phase_angle_deg: float, waxing: bool) -> str:
    if illum < 0.02:
        return "New Moon"
    if illum > 0.98:
        return "Full Moon"
    quarter = abs(illum - 0.5) < 0.06
    if illum < 0.5:
        base = "Crescent"
    else:
        base = "Gibbous"
    if quarter:
        return "First Quarter" if waxing else "Last Quarter"
    return f"{'Waxing' if waxing else 'Waning'} {base}"


def _crossings(times_utc, alt_deg, level, rising: bool):
    """Return the first UTC time the altitude curve crosses `level` going up
    (rising=True) or down (rising=False), or None."""
    a = np.asarray(alt_deg)
    for i in range(1, len(a)):
        if rising and a[i - 1] < level <= a[i]:
            return _interp_time(times_utc, a, i, level)
        if not rising and a[i - 1] >= level > a[i]:
            return _interp_time(times_utc, a, i, level)
    return None


def _interp_time(times_utc, a, i, level):
    t0, t1 = times_utc[i - 1], times_utc[i]
    a0, a1 = a[i - 1], a[i]
    if a1 == a0:
        return t0
    frac = (level - a0) / (a1 - a0)
    return t0 + (t1 - t0) * float(frac)


def compute_night(cfg: SiteConfig, when: datetime | None = None) -> dict:
    tz = ZoneInfo(cfg.timezone)
    load = Loader(str(DATA_DIR))
    eph = load("de421.bsp")
    ts = load.timescale()

    earth = eph["earth"]
    site = earth + wgs84.latlon(cfg.latitude, cfg.longitude, elevation_m=cfg.elevation_m)
    sun, moon = eph["sun"], eph["moon"]

    now_local = (when or datetime.now(tz)).astimezone(tz)
    # "Tonight" = the coming night. Anchor the search window from local noon
    # today to local noon tomorrow, so it captures this evening's darkness
    # through tomorrow's dawn. This is what a morning (e.g. 8am) email wants:
    # the night ahead, not the one that just ended.
    start_local = now_local.replace(hour=12, minute=0, second=0, microsecond=0)
    end_local = start_local + timedelta(days=1)

    n_steps = int((end_local - start_local).total_seconds() // (STEP_MINUTES * 60)) + 1
    local_times = [start_local + timedelta(minutes=STEP_MINUTES * i) for i in range(n_steps)]
    utc_times = [t.astimezone(ZoneInfo("UTC")) for t in local_times]
    t = ts.from_datetimes(utc_times)

    # Sun altitude across the window -> darkness mask.
    sun_alt = site.at(t).observe(sun).apparent().altaz()[0].degrees
    thr = TWILIGHT_THRESHOLDS.get(cfg.twilight, 18.0)
    dark_mask = sun_alt < -thr
    day_mask = sun_alt > -0.833  # sun visibly up

    py_utc = [dt for dt in utc_times]

    def first_true_time(mask):
        idx = np.argmax(mask) if mask.any() else None
        return py_utc[idx] if (idx is not None and mask.any()) else None

    def last_true_time(mask):
        if not mask.any():
            return None
        idx = len(mask) - 1 - np.argmax(mask[::-1])
        return py_utc[idx]

    darkness_start = first_true_time(dark_mask)
    darkness_end = last_true_time(dark_mask)
    darkness_hours = float(dark_mask.sum()) * STEP_MINUTES / 60.0

    # Sunset/sunrise: transitions of day_mask around the night.
    sunset = _crossings(py_utc, sun_alt, -0.833, rising=False)
    sunrise = _crossings(py_utc, sun_alt, -0.833, rising=True)

    # Moon.
    moon_astro = site.at(t).observe(moon).apparent()
    moon_alt = moon_astro.altaz()[0].degrees
    illum_series = almanac.fraction_illuminated(eph, "moon", t)
    mid_idx = len(t) // 2
    illum = float(illum_series[mid_idx])
    # Waxing if illumination is increasing across the night.
    waxing = bool(illum_series[-1] >= illum_series[0])
    # Phase angle proxy for quarter detection handled inside _phase_name.
    moon_up_dark = bool((dark_mask & (moon_alt >= 0)).any())
    moon_max_alt_dark = float(moon_alt[dark_mask].max()) if dark_mask.any() and (moon_alt[dark_mask] > -90).any() else None

    moon_info = {
        "illumination_pct": round(illum * 100),
        "phase_name": _phase_name(illum, 0.0, waxing),
        "rise_local": _fmt_local(_crossings(py_utc, moon_alt, 0.0, rising=True), tz),
        "set_local": _fmt_local(_crossings(py_utc, moon_alt, 0.0, rising=False), tz),
        "up_during_darkness": moon_up_dark,
        "max_altitude_deg": round(moon_max_alt_dark, 1) if moon_max_alt_dark is not None else None,
    }

    objects: list[dict] = []

    def summarise(name, obj_id, otype, alt_deg, az_deg, magnitude, constellation, note):
        alt = np.asarray(alt_deg)
        dark_alt = np.where(dark_mask, alt, -90.0)
        max_i = int(np.argmax(dark_alt))
        max_alt = float(dark_alt[max_i])
        visible = max_alt >= cfg.min_altitude_deg
        hours_up = float(((alt >= cfg.min_altitude_deg) & dark_mask).sum()) * STEP_MINUTES / 60.0
        transit_i = int(np.argmax(alt))
        return {
            "id": obj_id,
            "name": name,
            "type": otype,
            "magnitude": round(magnitude, 1) if isinstance(magnitude, (int, float)) else magnitude,
            "constellation": constellation,
            "note": note,
            "visible": visible,
            "max_altitude_deg": round(max_alt, 1) if max_alt > -90 else None,
            "best_time_local": _fmt_local(py_utc[max_i], tz) if max_alt > -90 else None,
            "azimuth_at_best_deg": round(float(np.asarray(az_deg)[max_i]), 0) if max_alt > -90 else None,
            "transit_altitude_deg": round(float(alt[transit_i]), 1),
            "rise_local": _fmt_local(_crossings(py_utc, alt, 0.0, rising=True), tz),
            "set_local": _fmt_local(_crossings(py_utc, alt, 0.0, rising=False), tz),
            "hours_above_min_alt": round(hours_up, 1),
        }

    # Planets.
    for target, disp, otype in PLANETS:
        body = eph[target]
        astro = site.at(t).observe(body).apparent()
        alt, az, _ = astro.altaz()
        try:
            mag = float(np.median(planetary_magnitude(site.at(t).observe(body))))
        except Exception:
            mag = None
        rec = summarise(disp, disp, otype, alt.degrees, az.degrees, mag, None, "")
        objects.append(rec)

    # Fixed catalog objects (deep-sky + bright stars).
    fixed: list[FixedObject] = load_fixed_objects()
    for fo in fixed:
        if fo.magnitude is not None and fo.magnitude > cfg.limiting_magnitude and fo.type != "star":
            # Skip faint DSOs beyond the site's limiting magnitude; keep all stars.
            continue
        star = Star(ra_hours=fo.ra_hours, dec_degrees=fo.dec_deg)
        astro = site.at(t).observe(star).apparent()
        alt, az, _ = astro.altaz()
        rec = summarise(fo.name, fo.id, fo.type, alt.degrees, az.degrees, fo.magnitude, fo.constellation, fo.note)
        objects.append(rec)

    visible_objects = [o for o in objects if o["visible"]]

    # Live weather forecast for the darkness window (additive; never affects the
    # object list). Fetched fresh each run; degrades gracefully on any failure.
    if cfg.weather:
        weather = fetch_weather(
            cfg.latitude,
            cfg.longitude,
            cfg.timezone,
            darkness_start.astimezone(tz) if darkness_start else None,
            darkness_end.astimezone(tz) if darkness_end else None,
        )
    else:
        weather = {"fetched": False, "note": "weather disabled in config"}

    return {
        "generated_at_utc": (when or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo("UTC")).isoformat(),
        "location": {
            "name": cfg.location_name,
            "latitude": cfg.latitude,
            "longitude": cfg.longitude,
            "elevation_m": cfg.elevation_m,
            "timezone": cfg.timezone,
        },
        "settings": {
            "min_altitude_deg": cfg.min_altitude_deg,
            "limiting_magnitude": cfg.limiting_magnitude,
            "twilight": cfg.twilight,
        },
        "night": {
            "date_local": start_local.strftime("%Y-%m-%d"),
            "date_display": start_local.strftime("%A, %B %-d, %Y"),
            "subject_date": start_local.strftime("%a %b %-d"),
            "weekday": start_local.strftime("%A"),
            "sunset_local": _fmt_local(sunset, tz),
            "sunrise_local": _fmt_local(sunrise, tz),
            "darkness_start_local": _fmt_local(darkness_start, tz),
            "darkness_end_local": _fmt_local(darkness_end, tz),
            "darkness_hours": round(darkness_hours, 1),
            "twilight_type": cfg.twilight,
        },
        "moon": moon_info,
        "weather": weather,
        "counts": {
            "evaluated": len(objects),
            "visible": len(visible_objects),
        },
        "objects": sorted(
            visible_objects,
            key=lambda o: (o["max_altitude_deg"] is None, -(o["max_altitude_deg"] or -90)),
        ),
    }
