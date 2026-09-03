# How it works

## The engine (`tonight.py` → `src/sky_tonight/compute.py`)

Given your `config.json`, the engine:

1. **Anchors "tonight"** to the coming night: it samples from local noon today to
   local noon tomorrow, every 2 minutes. A morning (8am) run therefore describes the
   night *ahead*, not the one that just ended.
2. **Finds the darkness window** from the Sun's altitude. `twilight` chooses the
   threshold: civil (−6°), nautical (−12°), or astronomical (−18°).
3. **Evaluates every object** — the 7 planets (Skyfield/DE421), the Moon, and each
   entry in `catalog/deep_sky.csv` — computing altitude/azimuth across the whole
   window. For each it records: max altitude during darkness, the local time of that
   maximum, azimuth (direction) then, rise/set, transit altitude, and how many hours
   it stays above `min_altitude_deg` while dark.
4. **Keeps only what's visible** — above `min_altitude_deg` during darkness — and,
   for deep-sky objects, brighter than `limiting_magnitude` (bright stars are always
   kept for orientation). Output is JSON, sorted by peak altitude.

The Moon block reports illumination % and phase, and whether it's up during
darkness — bright moonlight washes out faint targets, which the ranking step uses.

### Accuracy notes
- Positions use the JPL **DE421** ephemeris and apparent (refracted-horizon)
  altaz. Catalog coordinates are J2000 to arcminute precision — ample for
  visibility. Rise/set/transit times are interpolated between 2-minute samples
  (≈sub-minute precision), which is plenty for a daily naked-eye/binocular briefing.
- Planet magnitudes come from Skyfield's `planetary_magnitude`.

## The judgement (Cowork skill, on Sonnet)

The engine deliberately does **not** decide what's "interesting" — it only reports
verifiable facts. `skills/sky-report/SKILL.md` hands the JSON to **Claude Sonnet**,
which applies a rubric (rare/time-sensitive events > well-placed planets >
naked-eye/binocular showpieces > stars/constellations for context, with the Moon
factored in) and writes the email.

This split keeps the science reproducible and offline, while the subjective ranking
and prose stay with the model.

## Extending the catalog

Append rows to `catalog/deep_sky.csv`:

```
id,name,type,ra_hours,dec_deg,magnitude,constellation,note
```

`ra_hours` is right ascension in decimal hours (0–24), `dec_deg` declination in
decimal degrees. Anything you add is picked up automatically on the next run.

## Location resolution

You only put `city` + `state` (+ optional `zip`) in `config.json`. On first run,
`src/sky_tonight/location.py`:

1. Geocodes the city via the **Open-Meteo geocoding API** → latitude, longitude,
   elevation, IANA timezone, and the place's population. If a `zip` is given, the
   coordinates are refined via **Zippopotam** to your neighborhood.
2. **Estimates limiting magnitude** from the population as a coarse light-pollution
   proxy (big city → ~4.0/Bortle 8–9; rural → ~6.3). This is an estimate, not a
   measurement — set `limiting_magnitude` in `config.json` to override it with a real
   Bortle/SQM value.
3. Caches everything to `.location_cache.json` (gitignored) so subsequent and
   scheduled runs need no network.

Any field can be overridden by writing it directly into `config.json`; an explicit
value always beats the derived one. Supplying `latitude` + `longitude` skips the
network entirely. Both `config.json` and `.location_cache.json` are gitignored, so
your resolved location is never committed.
