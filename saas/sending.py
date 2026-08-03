"""Per-campaign send orchestration for the SaaS layer.

Reuses the core engine (:mod:`src.template_engine`, :mod:`src.html_to_ppt`,
:mod:`src.mailer._build_message`) but drives it from campaign rows stored in
the database instead of files on disk, and enforces subscription quotas.

Two send modes:
  * ``dry_run=True``  — renders and validates every message without contacting
    Gmail. Always available; still counts toward monthly usage so the meter is
    honest during testing.
  * ``dry_run=False`` — sends through a Gmail service. Real delivery requires a
    connected Gmail account (see :func:`get_service_for_user`); when none is
    connected the caller should fall back to dry-run.
"""

from __future__ import annotations

import csv
import io
import os
from pathlib import Path

from src import template_engine, html_to_ppt
from src.mailer import _build_message, _send_one
from src.sender_rotator import SenderRotator

from saas.plans import get_plan


class QuotaExceeded(Exception):
    """Raised when a send would push the user past their monthly plan limit."""


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


def get_service_for_user(user):
    """Return a Gmail API service for real sends, or ``None`` if unavailable.

    Real multi-tenant delivery uses per-user OAuth. That flow isn't wired up in
    this environment, so we optionally fall back to a single shared mailbox when
    ``config/credentials.json`` + ``token.json`` exist (dev/self-host mode).
    Returns None otherwise, and the caller degrades to dry-run.
    """
    try:
        from src.paths import CREDENTIALS_PATH, TOKEN_PATH
        if not (CREDENTIALS_PATH.exists() and TOKEN_PATH.exists()):
            return None
        from src.auth import get_gmail_service
        return get_gmail_service()
    except Exception:
        return None


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
    sender_email = user["sender_email"] or "demo@localhost"

    service = None
    if not dry_run:
        service = get_service_for_user(user)
        if service is None:
            dry_run = True   # no mailbox connected → safe simulate

    results: list[dict] = []
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
                msg = _build_message(
                    sender_email=sender_email,
                    sender_name=sender_name,
                    to_email=to_email,
                    subject=subject,
                    html_body=html_body,
                    attachment_path=attachment_path,
                )
                res = _send_one(service, msg)
                results.append({"to": to_email, "status": "sent", "id": res.get("id", "")})
            except Exception as e:
                results.append({"to": to_email, "status": "error", "error": str(e)})

        if attachment_path and Path(attachment_path).exists():
            try:
                os.unlink(attachment_path)
            except OSError:
                pass

    return results
