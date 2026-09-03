---
name: sky-report
description: "Compute which astronomical objects are visible in the local sky tonight and email a ranked, most-interesting-first briefing. Use when the user asks what's up tonight, for a night-sky report, or when this runs as a scheduled morning task."
---

# Sky Tonight — daily visible-sky briefing

Produce a short, skimmable briefing of what is worth looking at in tonight's sky
from the user's configured location, ordered **most interesting first**, and email
it to them.

The astronomy is done by a deterministic Python engine. Your job is to (1) run it,
(2) judge and order the objects by how interesting/notable they are tonight, and
(3) write and send a friendly email. Do **not** invent objects, magnitudes, or
times — use only what the engine returns.

## 1. Locate the project and run the engine

The project lives at the repository root that contains `tonight.py` (the folder
this skill was installed from — typically `sky-tonight/`). From that directory:

```bash
.venv/bin/python tonight.py --config config.json
```

This prints a JSON report to stdout. If it errors:
- "Config not found" → the user hasn't set up `config.json`. Stop and tell them to
  copy `config.example.json` to `config.json` and set their location (see the
  project's `COWORK_SETUP.md`). Do not guess a location.
- Missing `de421.bsp` / import errors → run `bash scripts/setup.sh` once, then retry.

Read the JSON. Key fields: `night` (sunset/sunrise, darkness window, hours of
darkness), `moon` (illumination %, phase, whether it's up during darkness — bright
moonlight washes out faint deep-sky objects), and `objects` (only those above the
horizon during darkness), each with `type`, `magnitude`, `max_altitude_deg`,
`best_time_local`, `constellation`, `note`, and `hours_above_min_alt`.

## 2. Rank by interestingness — on Sonnet, not Opus

The interestingness judgement **must run on Claude Sonnet** (`claude-sonnet-5`),
not Opus. Delegate this step to a subagent with the model set to Sonnet (use the
Task/Agent tool with `model: "sonnet"`), passing it the JSON and the rubric below.
Have it return an ordered list. If no subagent tool is available in this run, state
in the email footer that ranking ran on the session model, but always prefer the
Sonnet subagent.

Ranking rubric — weigh these together, top = most worth a look tonight:
- **Rare / time-sensitive events** first: a planet near opposition or greatest
  elongation, a bright comet, a meteor shower near peak, close conjunctions, the
  ISS — anything that is unusually good *tonight* specifically.
- **Planets** that are well placed (high `max_altitude_deg`, up during darkness).
  Saturn's rings, Jupiter's moons, Venus/Mars phases and colour are crowd-pleasers.
- **Naked-eye and binocular showpieces**: bright, large, famous deep-sky objects
  (e.g. M31, M42, M45, M13, Double Cluster). Favour lower magnitude (brighter),
  higher altitude, and more `hours_above_min_alt`.
- **Moon**: if it's a thin crescent or the terminator is interesting, feature it;
  if it's bright and up all night, note that it will wash out faint targets and
  down-rank dim galaxies/nebulae accordingly.
- Bright named stars and constellations are context, not headliners — keep a few
  for orientation but rank them below the showpieces.
- Prefer objects near their `best_time_local` during comfortable evening hours over
  ones that only clear the horizon just before dawn.

Aim for a final list of about **6–10 headline objects**, each with a one-line,
plain-language reason it's worth seeing and *when/where* to look
(best time + rough altitude/direction). Group the rest briefly.

## 3. Compose the email

Subject: `Sky Tonight — {location}, {weekday Month D}` (e.g. "Sky Tonight — New York, NY, Thu Sep 3").

Body (short, scannable; HTML is fine, plain text also fine):
- One-line summary: hours of darkness, moon phase + illumination %, and the single
  best thing to see tonight.
- **Tonight's highlights** — the ranked list (numbered), each: name (type,
  constellation) — why it's notable — best time & where to look.
- **Also up** — a compact line or two naming the rest by category.
- A one-line footer: darkness window (`darkness_start`–`darkness_end` local),
  and "MVP ignores weather — check your local forecast before heading out."

Keep the whole thing readable in under a minute. No preamble, no restating these
instructions.

## 4. Send the email

Send to the `email_to` address in `config.json` using the user's connected email
tool (e.g. Gmail). Sending email is a real action:
- In an **interactive** session, confirm the recipient and show the draft before
  sending.
- In an **unattended scheduled run**, send directly to the configured `email_to`.
- If **no email tool is connected**, do not fail silently: write the briefing to
  `sky_report_latest.html` in the project folder and report that email delivery is
  not configured yet (the user needs to connect Gmail or another email connector).

## Notes
- The engine is offline and deterministic; two runs for the same night/location
  give the same facts. All interpretation lives here.
- Weather is intentionally out of scope for the MVP.
