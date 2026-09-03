"""Resolve a simple user config (city/state + optional zip) into full coordinates.

The user only writes city + state (+ optional zip). This module derives:
  - latitude / longitude   (Open-Meteo geocoding; refined by zip via Zippopotam)
  - timezone               (IANA, from the geocoder)
  - elevation_m            (from the geocoder)
  - limiting_magnitude     (estimated from the city's population as a light-pollution proxy)

Results are cached to .location_cache.json (gitignored) so daily/scheduled runs work
offline after the first resolve. Any field can be overridden by putting it directly
in config.json — an override always wins and skips the network for that field.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / ".location_cache.json"
USER_AGENT = "sky-tonight/0.1 (https://github.com/DominicSicilian/sky-tonight)"
TIMEOUT = 12

US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


class LocationError(RuntimeError):
    pass


def _get_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def estimate_limiting_magnitude(population: int | None) -> float:
    """Rough naked-eye limiting magnitude from a light-pollution proxy (city population).

    This is an ESTIMATE, not a measurement. Override `limiting_magnitude` in config.json
    if you know your site's true sky quality (e.g. from a Bortle/SQM reading).
    """
    if population is None:
        return 5.0  # unknown -> assume typical suburban skies
    if population >= 1_000_000:
        return 4.0   # inner big city, Bortle ~8-9
    if population >= 250_000:
        return 4.5   # large city, Bortle ~7
    if population >= 50_000:
        return 5.0   # small city / dense suburb, Bortle ~6
    if population >= 10_000:
        return 5.5   # town / suburb, Bortle ~5
    if population >= 2_000:
        return 6.0   # rural town, Bortle ~4
    return 6.3       # rural / dark, Bortle <=3


def _match_state(results: list[dict], state: str) -> dict | None:
    if not state:
        return results[0] if results else None
    state = state.strip()
    full = US_STATES.get(state.upper(), state)
    for r in results:
        a1 = (r.get("admin1") or "").strip()
        if a1.lower() in {state.lower(), full.lower()}:
            return r
    return results[0] if results else None


def _geocode_city(city: str, state: str, country: str) -> dict:
    q = urllib.parse.urlencode(
        {"name": city, "count": 10, "language": "en", "format": "json", "country_code": country}
    )
    data = _get_json(f"https://geocoding-api.open-meteo.com/v1/search?{q}")
    results = data.get("results") or []
    if not results:
        raise LocationError(
            f"Could not geocode city '{city}'. Check spelling, or set latitude/longitude "
            "directly in config.json."
        )
    r = _match_state(results, state)
    return {
        "latitude": float(r["latitude"]),
        "longitude": float(r["longitude"]),
        "elevation_m": float(r.get("elevation") or 0.0),
        "timezone": r.get("timezone") or "UTC",
        "population": r.get("population"),
        "resolved_name": f"{r.get('name', city)}, {r.get('admin1', state)}",
    }


def _refine_with_zip(zip_code: str, country: str, base: dict) -> dict:
    try:
        data = _get_json(f"https://api.zippopotam.us/{country.lower()}/{zip_code}")
        place = (data.get("places") or [None])[0]
        if place:
            base = dict(base)
            base["latitude"] = float(place["latitude"])
            base["longitude"] = float(place["longitude"])
            base["resolved_name"] = (
                f"{place.get('place name', '').strip()}, "
                f"{place.get('state abbreviation', '').strip()} {zip_code}".strip()
            )
    except Exception:
        pass  # zip refinement is best-effort; keep the city-level coordinates
    return base


def _cache_key(city, state, zip_code, country) -> str:
    return "|".join(str(x or "").strip().lower() for x in (city, state, zip_code, country))


def _load_cache() -> dict:
    if CACHE_PATH.exists():
        try:
            return json.loads(CACHE_PATH.read_text())
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, indent=2) + "\n")


def resolve_location(cfg: dict, refresh: bool = False) -> dict:
    """Return a fully-resolved config dict ready for SiteConfig.from_dict()."""
    # Full manual override: user supplied coordinates directly -> no network at all.
    manual_coords = cfg.get("latitude") is not None and cfg.get("longitude") is not None

    city = cfg.get("city", "")
    state = cfg.get("state", "")
    zip_code = str(cfg.get("zip", "") or "").strip()
    country = (cfg.get("country") or "US").strip()

    if not manual_coords and not city:
        raise LocationError(
            "config.json needs either 'city' (+ 'state'), or explicit 'latitude'/'longitude'."
        )

    resolved: dict = {}
    if manual_coords:
        resolved = {
            "latitude": float(cfg["latitude"]),
            "longitude": float(cfg["longitude"]),
            "elevation_m": float(cfg.get("elevation_m", 0.0)),
            "timezone": cfg.get("timezone", "UTC"),
            "population": None,
            "resolved_name": cfg.get("location_name", "Custom coordinates"),
        }
    else:
        key = _cache_key(city, state, zip_code, country)
        cache = _load_cache()
        if not refresh and key in cache:
            resolved = cache[key]
        else:
            try:
                resolved = _geocode_city(city, state, country)
                if zip_code:
                    resolved = _refine_with_zip(zip_code, country, resolved)
                cache[key] = resolved
                _save_cache(cache)
            except LocationError:
                raise
            except Exception as e:  # network/parse failure with no cache
                if key in cache:
                    resolved = cache[key]
                else:
                    raise LocationError(
                        f"Location lookup failed ({e}) and nothing is cached. Connect to the "
                        "internet once to resolve your city, or set latitude/longitude in config.json."
                    ) from e

    # Assemble the final config. Explicit values in config.json always override derived ones.
    lim = cfg.get("limiting_magnitude")
    if lim is None:
        lim = estimate_limiting_magnitude(resolved.get("population"))

    out = {
        "location_name": cfg.get("location_name") or resolved.get("resolved_name") or "Unknown",
        "latitude": cfg.get("latitude", resolved["latitude"]),
        "longitude": cfg.get("longitude", resolved["longitude"]),
        "elevation_m": cfg.get("elevation_m", resolved.get("elevation_m", 0.0)),
        "timezone": cfg.get("timezone") or resolved.get("timezone") or "UTC",
        "min_altitude_deg": cfg.get("min_altitude_deg", 15.0),
        "limiting_magnitude": lim,
        "twilight": cfg.get("twilight", "astronomical"),
        "email_to": cfg.get("email_to", ""),
        "weather": cfg.get("weather", True),
        "_derived": {
            "population": resolved.get("population"),
            "from_cache": None,
            "resolved_name": resolved.get("resolved_name"),
        },
    }
    return out
