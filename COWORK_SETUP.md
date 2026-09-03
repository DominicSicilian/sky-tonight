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

## Step 2 — Set up email delivery (pick one)

Choose how the briefing is sent with the `delivery` field in `config.json`:
`"connector"` (default) or `"smtp"`.

**Option A — Gmail connector (default; OAuth, no secret on disk).**
In Cowork, open **Settings → Connectors**, search **Gmail**, click **Connect**, and
authorize in Google's own sign-in flow. Entering credentials happens there — Claude
never handles your password.

**Option B — SMTP with a Gmail App Password (no connector).**
1. Enable 2-Step Verification on your Google account, then create an **App Password**
   at https://myaccount.google.com/apppasswords.
2. Save it locally (gitignored):
   ```bash
   echo "abcd efgh ijkl mnop" > .secrets/smtp_password
   ```
   (or `export SKY_TONIGHT_SMTP_PASSWORD="abcd efgh ijkl mnop"`).
3. Make sure `email_from` in `config.json` is your Gmail address. Test it:
   ```bash
   ./.venv/bin/python scripts/send_email.py --subject "Sky Tonight test" \
     --html sky_report_latest.html --dry-run
   ```

If neither is configured, the skill just writes `sky_report_latest.html` and tells
you email isn't set up yet — it never fails silently.

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
