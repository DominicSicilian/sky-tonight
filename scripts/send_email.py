#!/usr/bin/env python3
"""Send the briefing by email over SMTP — no Cowork connector required.

Credentials are NEVER stored in the repo. The app password is read from, in order:
  1. env var  SKY_TONIGHT_SMTP_PASSWORD
  2. file     .secrets/smtp_password   (gitignored)

SMTP settings and the from/to addresses come from config.json:
  "email_to":    where to send (required)
  "email_from":  the sending Gmail address (defaults to email_to)
  "smtp_host":   defaults to smtp.gmail.com
  "smtp_port":   defaults to 465 (implicit TLS)

Usage:
    .venv/bin/python scripts/send_email.py --subject "Sky Tonight ..." --html report.html
    .venv/bin/python scripts/send_email.py --subject "..." --html report.html --dry-run
"""
from __future__ import annotations

import argparse
import json
import smtplib
import ssl
import sys
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_password() -> str | None:
    import os

    env = os.environ.get("SKY_TONIGHT_SMTP_PASSWORD")
    if env:
        return env.strip()
    f = ROOT / ".secrets" / "smtp_password"
    if f.exists():
        return f.read_text().strip()
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Send the sky briefing via SMTP.")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--html", help="Path to an HTML file to send as the body.")
    ap.add_argument("--text", help="Path to a plain-text file (used as fallback/body).")
    ap.add_argument("--config", default=str(ROOT / "config.json"))
    ap.add_argument("--dry-run", action="store_true", help="Print the message; do not send.")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    to_addr = cfg.get("email_to")
    if not to_addr:
        sys.stderr.write("config.json has no email_to.\n")
        return 2
    from_addr = cfg.get("email_from", to_addr)
    host = cfg.get("smtp_host", "smtp.gmail.com")
    port = int(cfg.get("smtp_port", 465))

    html = Path(args.html).read_text() if args.html else None
    text = Path(args.text).read_text() if args.text else None
    if not html and not text:
        sys.stderr.write("Provide --html and/or --text.\n")
        return 2

    msg = EmailMessage()
    msg["Subject"] = args.subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(text or "Your mail client does not support HTML. See the HTML part.")
    if html:
        msg.add_alternative(html, subtype="html")

    if args.dry_run:
        print(f"[dry-run] would send via {host}:{port}")
        print(f"[dry-run] From: {from_addr}  To: {to_addr}")
        print(f"[dry-run] Subject: {args.subject}")
        print(f"[dry-run] html={bool(html)} text={bool(text)}")
        return 0

    password = read_password()
    if not password:
        sys.stderr.write(
            "No SMTP password found. Set SKY_TONIGHT_SMTP_PASSWORD or create "
            ".secrets/smtp_password with a Gmail App Password.\n"
        )
        return 3

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=ctx) as server:
        server.login(from_addr, password)
        server.send_message(msg)
    print(f"Sent to {to_addr} via {host}:{port}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
