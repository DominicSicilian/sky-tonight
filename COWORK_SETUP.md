# Wiring Sky Tonight into Claude Cowork

This gets you a daily 8am email of tonight's sky, ranked by Claude.

## Prerequisites

1. Run the one-time setup so the engine works locally:
   ```bash
   bash scripts/setup.sh
   ```
2. Edit `config.json` with your location and your `email_to` address.
3. Confirm the engine runs:
   ```bash
   ./.venv/bin/python tonight.py --config config.json | head -20
   ```

## Step 1 — Make the skill available to Cowork

The skill is `skills/sky-report/SKILL.md`. Point Cowork at it one of two ways:

- **Folder instructions**: open this project folder in Cowork and tell Claude to
  "use the sky-report skill in `skills/sky-report/`", or
- **Install as a user skill**: copy the `skills/sky-report/` folder into your Cowork
  skills directory.

## Step 2 — Connect an email tool

The daily briefing is sent through a connected email connector (Gmail is the common
choice). In Cowork, add the **Gmail** connector (or another email connector) and
authorize it. Without an email connector, the skill will save the briefing to
`sky_report_latest.html` instead of emailing it.

> Note: entering credentials is something *you* do in the connector's own auth flow —
> Claude never handles your password.

## Step 3 — Create the daily 8am schedule

Ask Cowork:

> "Every morning at 8am, run the sky-report skill for my location and email me
> tonight's briefing."

Or invoke `/schedule` and confirm **`0 8 * * *`** (8am daily, local time).

Use this self-contained prompt for the scheduled task (edit the path if your repo
lives elsewhere):

```
Generate tonight's night-sky briefing and email it.

1. cd into the sky-tonight project at:
   /ABSOLUTE/PATH/TO/sky-tonight
2. Run: .venv/bin/python tonight.py --config config.json
   (If it fails because the ephemeris or venv is missing, run `bash scripts/setup.sh` once, then retry.)
3. Follow skills/sky-report/SKILL.md to rank the objects MOST INTERESTING FIRST.
   The interestingness ranking MUST run on Claude Sonnet (claude-sonnet-5) — delegate
   that step to a subagent with model "sonnet".
4. Compose the email exactly as SKILL.md describes and SEND it to the email_to
   address in config.json using the connected email tool. This is an unattended run,
   so send directly (no confirmation step). If no email tool is connected, save the
   briefing to sky_report_latest.html and note that email is not configured.

Do not invent objects, times, or magnitudes — use only the engine's JSON output.
```

## Notes

- **Scheduled tasks run while the Cowork app is open.** If the app is closed at 8am,
  the task runs the next time you open it.
- **Timezone**: cron for the schedule is evaluated in your local timezone; the
  engine uses the `timezone` in `config.json`. Keep them consistent.
- **Why Sonnet?** The ranking is a good fit for Sonnet's speed/cost, and this project
  pins that step to Sonnet on purpose. The rest of the run can be any model.
