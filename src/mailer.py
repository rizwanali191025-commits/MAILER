"""Core bulk-mailer logic.

Flow:
  1. Load recipients from a CSV file.
  2. For each recipient, render subject + HTML body through the template engine.
  3. Optionally convert the rendered HTML body to a .pptx and attach it.
  4. Rotate the sender display name.
  5. Send via Gmail API with configurable rate limiting.
"""

import base64
import csv
import json
import os
import time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Generator

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from src import template_engine, html_to_ppt
from src.sender_rotator import SenderRotator

console = Console()


# ── helpers ────────────────────────────────────────────────────────────────

def _load_recipients(csv_path: str) -> list[dict]:
    with open(csv_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _build_message(
    sender_email: str,
    sender_name: str,
    to_email: str,
    subject: str,
    html_body: str,
    attachment_path: str | None = None,
) -> dict:
    """Return a base64url-encoded Gmail API raw message dict."""
    msg = MIMEMultipart("mixed")
    msg["From"] = f"{sender_name} <{sender_email}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    # HTML body
    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(html_body, "html", "utf-8"))
    msg.attach(alt)

    # PPTX attachment
    if attachment_path and Path(attachment_path).exists():
        with open(attachment_path, "rb") as f:
            pptx_data = f.read()
        pptx_part = MIMEApplication(pptx_data,
            "vnd.openxmlformats-officedocument.presentationml.presentation")
        filename = Path(attachment_path).name
        pptx_part.add_header("Content-Disposition", "attachment", filename=filename)
        msg.attach(pptx_part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


def _send_one(service, message_body: dict) -> dict:
    return service.users().messages().send(userId="me", body=message_body).execute()


# ── public API ──────────────────────────────────────────────────────────────

def send_bulk(
    service,
    config: dict,
    recipients_csv: str,
    subject_template: str,
    body_html_template: str,
    attach_as_pptx: bool = True,
    dry_run: bool = False,
) -> list[dict]:
    """Send bulk emails and return a list of result dicts.

    config keys:
      sender_email     — authenticated Gmail address
      sender_names     — list[str] or comma-separated str of display names
      delay_seconds    — float, pause between sends (default 1.0)
      max_per_run      — int, cap total sends (0 = unlimited)
    """
    sender_email: str = config["sender_email"]
    delay: float = float(config.get("delay_seconds", 1.0))
    max_sends: int = int(config.get("max_per_run", 0))

    rotator = SenderRotator.from_config(config)
    recipients = _load_recipients(recipients_csv)

    if max_sends > 0:
        recipients = recipients[:max_sends]

    results = []
    errors = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Sending emails…", total=len(recipients))

        for idx, recipient in enumerate(recipients, start=1):
            to_email = recipient.get("email", "").strip()
            if not to_email:
                console.print(f"[yellow]Row {idx}: missing email, skipping.[/yellow]")
                progress.advance(task)
                continue

            sender_name = rotator.next()
            subject = template_engine.render(subject_template, recipient, index=idx)
            html_body = template_engine.render(body_html_template, recipient, index=idx)

            attachment_path = None
            if attach_as_pptx:
                try:
                    attachment_path = html_to_ppt.html_to_pptx(html_body)
                except Exception as e:
                    console.print(f"[yellow]Row {idx}: PPT generation failed: {e}[/yellow]")

            msg = _build_message(
                sender_email=sender_email,
                sender_name=sender_name,
                to_email=to_email,
                subject=subject,
                html_body=html_body,
                attachment_path=attachment_path,
            )

            if dry_run:
                console.print(
                    f"[cyan]DRY RUN[/cyan] → {to_email} | From: {sender_name} | Subject: {subject}"
                )
                results.append({"to": to_email, "status": "dry_run"})
            else:
                try:
                    result = _send_one(service, msg)
                    results.append({"to": to_email, "status": "sent", "id": result.get("id")})
                    console.print(f"[green]✓[/green] {to_email} — {sender_name}")
                except Exception as e:
                    errors.append({"to": to_email, "error": str(e)})
                    console.print(f"[red]✗[/red] {to_email}: {e}")

            # clean up temp pptx
            if attachment_path and Path(attachment_path).exists():
                try:
                    os.unlink(attachment_path)
                except OSError:
                    pass

            progress.advance(task)

            if idx < len(recipients):
                time.sleep(delay)

    console.print(f"\n[bold]Done.[/bold] Sent: {len(results)}  Errors: {len(errors)}")
    if errors:
        console.print("[red]Failed recipients:[/red]")
        for e in errors:
            console.print(f"  {e['to']}: {e['error']}")

    return results + errors
