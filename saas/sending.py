"""Per-campaign send orchestration for the SaaS layer.

Renders each recipient with the core template engine and sends real email
through the operator's single shared Gmail account via SMTP (Gmail App
Password). Enforces subscription quotas before anything is sent.

Send modes:
  * ``dry_run=True``  — renders and validates every message without sending.
    Always available; still counts toward monthly usage so the meter is honest.
  * ``dry_run=False`` — sends for real via Gmail SMTP, but only if the operator
    has connected a sending account (see :mod:`saas.models.get_app_config`).
    If none is connected, the send safely degrades to a simulate.
"""

from __future__ import annotations

import csv
import io
import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from src import template_engine, html_to_ppt
from src.sender_rotator import SenderRotator

from saas import models
from saas.plans import get_plan

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


class QuotaExceeded(Exception):
    """Raised when a send would push the user past their monthly plan limit."""


class SendingNotConfigured(Exception):
    """Raised on a real send when no shared Gmail account is connected."""


def parse_recipients(recipients_csv: str) -> list[dict]:
    return [
        {k: (v or "").strip() for k, v in row.items() if k}
        for row in csv.DictReader(io.StringIO(recipients_csv))
    ]


def sender_names_for(user, plan) -> list[str]:
    """Sender display names, respecting the plan's rotation feature gate."""
    raw = [n.strip() for n in (user["sender_names"] or "").split(",") if n.strip()]
    if not raw:
        raw = [user["sender_email"] or "The Team"]
    if not plan.sender_rotation:
        raw = raw[:1]          # free tier: single fixed name, no rotation
    return raw


def render_preview(campaign, user, index: int = 1) -> dict:
    """Render one recipient for the live preview pane."""
    rows = parse_recipients(campaign["recipients_csv"])
    if not rows:
        return {"error": "No recipients in the CSV yet."}
    if index < 1 or index > len(rows):
        return {"error": f"Row {index} is out of range (1–{len(rows)})."}

    row = dict(rows[index - 1])
    row.setdefault("sender", (user["sender_names"] or user["sender_email"] or "The Team").split(",")[0].strip())
    return {
        "subject": template_engine.render(campaign["subject_tmpl"], row, index=index),
        "body": template_engine.render(campaign["body_tmpl"], row, index=index),
        "recipient": row,
        "tags": list(dict.fromkeys(
            template_engine.list_tags(campaign["subject_tmpl"])
            + template_engine.list_tags(campaign["body_tmpl"])
        )),
        "total": len(rows),
    }


# ── message building & SMTP ──────────────────────────────────────────────────

def _build_mime(
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    html_body: str,
    attachment_path: str | None = None,
) -> MIMEMultipart:
    msg = MIMEMultipart("mixed")
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            data = f.read()
        part = MIMEApplication(
            data, "vnd.openxmlformats-officedocument.presentationml.presentation")
        part.add_header("Content-Disposition", "attachment",
                        filename=Path(attachment_path).name)
        msg.attach(part)
    return msg


def open_smtp(smtp_email: str, smtp_password: str) -> smtplib.SMTP:
    """Open an authenticated Gmail SMTP connection (STARTTLS)."""
    server = smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT, timeout=30)
    server.ehlo()
    server.starttls(context=ssl.create_default_context())
    server.ehlo()
    server.login(smtp_email, smtp_password)
    return server


def send_test_email(smtp_email: str, smtp_password: str, to_email: str) -> None:
    """Send a single verification email. Raises on failure (bad password, etc.)."""
    msg = _build_mime(
        smtp_email, "MailPilot", to_email,
        "MailPilot — your sending account works ✅",
        "<h2>You're connected!</h2><p>This test confirms MailPilot can send "
        "email through your Gmail account. You're ready to run campaigns.</p>",
    )
    server = open_smtp(smtp_email, smtp_password)
    try:
        server.send_message(msg)
    finally:
        server.quit()


# ── campaign send ────────────────────────────────────────────────────────────

def send_campaign(
    campaign,
    user,
    *,
    dry_run: bool,
    remaining_quota: int,
) -> list[dict]:
    """Render and (optionally) send a campaign. Returns per-recipient results.

    Enforces the monthly quota *before* sending: if the recipient count exceeds
    the remaining quota, raises :class:`QuotaExceeded` so nothing is sent.
    """
    plan = get_plan(user["plan_id"])
    rows = parse_recipients(campaign["recipients_csv"])
    valid = [r for r in rows if r.get("email")]
    if not valid:
        return []

    if len(valid) > remaining_quota:
        raise QuotaExceeded(
            f"This send needs {len(valid)} emails but only {remaining_quota} "
            f"remain on your {plan.name} plan this month."
        )

    attach_pptx = bool(campaign["attach_pptx"]) and plan.pptx_attachments
    rotator = SenderRotator(sender_names_for(user, plan))

    # Real sends go through the operator's shared Gmail account.
    cfg = models.get_app_config()
    smtp_email = (cfg["smtp_email"] or "").strip()
    smtp_password = (cfg["smtp_password"] or "").strip()
    server = None
    if not dry_run:
        if not (smtp_email and smtp_password):
            dry_run = True   # nothing connected → safe simulate
        else:
            server = open_smtp(smtp_email, smtp_password)

    results: list[dict] = []
    try:
        for idx, row in enumerate(valid, start=1):
            to_email = row["email"]
            sender_name = rotator.next()
            data = dict(row)
            data.setdefault("sender", sender_name)
            subject = template_engine.render(campaign["subject_tmpl"], data, index=idx)
            html_body = template_engine.render(campaign["body_tmpl"], data, index=idx)

            attachment_path = None
            if attach_pptx:
                try:
                    attachment_path = html_to_ppt.html_to_pptx(html_body)
                except Exception:
                    attachment_path = None

            if dry_run:
                results.append({"to": to_email, "status": "dry_run", "id": ""})
            else:
                try:
                    msg = _build_mime(
                        smtp_email, sender_name, to_email, subject,
                        html_body, attachment_path,
                    )
                    server.send_message(msg)
                    results.append({"to": to_email, "status": "sent", "id": ""})
                except Exception as e:
                    results.append({"to": to_email, "status": "error", "error": str(e)})

            if attachment_path and Path(attachment_path).exists():
                try:
                    os.unlink(attachment_path)
                except OSError:
                    pass
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                pass

    return results
