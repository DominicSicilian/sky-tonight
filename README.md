# 🔭 Sky Tonight

A tiny, open-source astronomy companion for **Claude Cowork**. Every morning it
emails you a briefing of what's worth looking at in *tonight's* sky from your
location — ordered **most interesting first** by Claude.

- **Deterministic astronomy** in plain Python ([Skyfield](https://rhodesmill.org/skyfield/)):
  computes the darkness window, moon phase, and which planets, deep-sky showpieces,
  and bright stars clear your horizon during the night.
- **Claude does the judgement**: a Cowork skill hands the raw visibility data to
  **Claude Sonnet**, which ranks the objects by how notable they are *tonight* and
  writes a friendly, skimmable email.
- **Runs itself**: a Cowork `/schedule` job fires daily at 8am and emails you.

> MVP scope: no weather. It tells you what's *astronomically* visible; check your
> local forecast before heading out. Clouds are on the roadmap.

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

## Quick start

1. **Install** (one time):
   ```bash
   bash scripts/setup.sh
   ```
   This creates `.venv`, installs deps, downloads the ephemeris, and creates
   `config.json`.

2. **Set your location** — edit `config.json`:
   ```json
   {
     "location_name": "New York, NY",
     "latitude": 40.7128,
     "longitude": -74.0060,
     "elevation_m": 10,
     "timezone": "America/New_York",
     "min_altitude_deg": 15,
     "limiting_magnitude": 6.5,
     "twilight": "astronomical",
     "email_to": "you@example.com"
   }
   ```

3. **Try the engine**:
   ```bash
   ./.venv/bin/python tonight.py --config config.json | head -40
   ```

4. **Wire it into Cowork** — see [`COWORK_SETUP.md`](COWORK_SETUP.md): install the
   skill, connect an email tool (e.g. Gmail), and create the daily 8am schedule.

## Config reference

| Field | Meaning |
|-------|---------|
| `location_name` | Shown in the email subject/body. |
| `latitude` / `longitude` | Decimal degrees (N/E positive). |
| `elevation_m` | Site elevation in metres. |
| `timezone` | IANA name, e.g. `America/New_York`. |
| `min_altitude_deg` | Ignore objects that never get this high during darkness. |
| `limiting_magnitude` | Skip deep-sky objects fainter than this (bright stars always kept). |
| `twilight` | `civil` \| `nautical` \| `astronomical` — how dark counts as "dark". |
| `email_to` | Where the daily briefing is sent. |

## What it tracks (MVP)

Planets (Mercury–Neptune), the Moon (phase + illumination), and a curated catalog
of ~35 deep-sky showpieces plus ~17 of the brightest stars. The catalog lives in
`catalog/deep_sky.csv` — add your own targets by appending rows.

## Roadmap

- Weather / cloud-cover integration
- Meteor showers, comets, and ISS/satellite passes
- Full Messier + NGC catalog option
- Per-object finder links (Stellarium / SkySafari)

## License

MIT — see [LICENSE](LICENSE). Built to plug straight into Claude Cowork; PRs welcome.
