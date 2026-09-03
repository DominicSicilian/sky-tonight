# 🔭 Sky Tonight

An open-source astronomy companion for **Claude Cowork**. Every morning it
emails you a briefing of what's worth looking at in *tonight's* sky from your
location — ordered **most interesting first** by Claude.

- **Deterministic astronomy** in plain Python ([Skyfield](https://rhodesmill.org/skyfield/)):
  computes the darkness window, moon phase, and which planets, deep-sky showpieces,
  and bright stars clear your horizon during the night.
- **Claude does the judgement**: a Cowork skill hands the raw visibility data to
  **Claude Sonnet**, which ranks the objects by how notable they are *tonight* and
  writes a friendly, skimmable email.
- **Runs itself**: a Cowork `/schedule` job fires daily at 8am and emails you.

> It tells you what's *astronomically* visible, and overlays a **live hourly
> cloud/precip forecast** so you know *when* the sky is actually usable (and warns
> you in bold red when it's a washout). Always sanity-check your local sky before
> heading out.

## How it works

```
┌────────────┐   JSON facts   ┌─────────────────────┐   email   ┌──────────┐
│ tonight.py │ ─────────────▶ │ Claude Sonnet ranks │ ────────▶ │ your      │
│ (Skyfield) │  what's up,    │ + writes briefing   │           │ inbox 8am │
└────────────┘  when, where   └─────────────────────┘           └──────────┘
```

- `tonight.py` → prints a JSON report for the coming night (see `docs/HOW_IT_WORKS.md`).
- `skills/sky-report/SKILL.md` → the Cowork skill: run engine → rank on Sonnet → email.
- A scheduled task runs the skill every morning.

A real briefing, as delivered: [`docs/example_briefing.html`](docs/example_briefing.html).

## Quick start

1. **Install** (one time):
   ```bash
   bash scripts/setup.sh
   ```
   This creates `.venv`, installs deps, downloads the ephemeris, and creates
   `config.json`.

2. **Set your location** — edit `config.json`. Just your city and state (zip optional):
   ```json
   {
     "city": "Boulder",
     "state": "CO",
     "zip": "",
     "email_to": "you@example.com",
     "delivery": "connector"
   }
   ```
   On first run the code geocodes this to latitude/longitude, timezone, and
   elevation, and estimates your **limiting magnitude** from the area's population
   (a light-pollution proxy). Results are cached to `.location_cache.json` so later
   runs work offline. `config.json` and the cache are **gitignored** — your location
   never leaves your machine.

3. **Try the engine**:
   ```bash
   ./.venv/bin/python tonight.py --config config.json | head -40
   ```

4. **Wire it into Cowork** — see [`COWORK_SETUP.md`](COWORK_SETUP.md): install the
   skill, set up email delivery, and create the daily 8am schedule. Email works via
   a **Gmail connector** *or* plain **SMTP + a Gmail App Password** (no connector).

## Config reference

**Required:** `city`, `state`, `email_to`.

| Field | Required? | Meaning |
|-------|-----------|---------|
| `city` / `state` | ✅ | Your location. Geocoded to coordinates automatically. |
| `zip` | optional | Refines coordinates to your neighborhood (US). |
| `country` | optional | ISO-2 code, default `US`. |
| `email_to` | ✅ | Where the daily briefing is sent. |
| `delivery` | optional | `connector` (default) or `smtp`. See [`COWORK_SETUP.md`](COWORK_SETUP.md). |
| `weather` | optional | `true` (default) overlays a live hourly cloud/precip forecast; set `false` to skip that network call. |

**Everything below is auto-derived** — add any of them to `config.json` only if you
want to override the estimate:

| Field | Auto-derived from | Override when |
|-------|-------------------|---------------|
| `latitude` / `longitude` | geocoding city/zip | you want exact coordinates |
| `timezone` | geocoder (IANA) | rarely needed |
| `elevation_m` | geocoder | you know your true elevation |
| `limiting_magnitude` | area population (light-pollution proxy) | you have a real Bortle/SQM reading |
| `min_altitude_deg` | default `15` | your horizon is more/less obstructed |
| `twilight` | default `astronomical` | you prefer `civil` or `nautical` darkness |

## What it tracks (MVP)

Planets (Mercury–Neptune), the Moon (phase + illumination), and a curated catalog
of ~35 deep-sky showpieces plus ~17 of the brightest stars. The catalog lives in
`catalog/deep_sky.csv` — add your own targets by appending rows.

## Roadmap

- Meteor showers, comets, and ISS/satellite passes
- Full Messier + NGC catalog option
- Per-object finder links (Stellarium / SkySafari)

## License

MIT — see [LICENSE](LICENSE). Built to plug straight into Claude Cowork; PRs welcome.
