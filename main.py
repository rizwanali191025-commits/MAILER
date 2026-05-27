#!/usr/bin/env python3
"""Bulk Gmail Mailer — CLI entry point.

Usage examples:
  python main.py send
  python main.py send --dry-run
  python main.py send --no-pptx
  python main.py preview --recipient data/recipients.csv --index 1
  python main.py tags
  python main.py auth
"""

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()

CONFIG_PATH = Path("config/settings.json")
RECIPIENTS_PATH = Path("data/recipients.csv")
SUBJECT_TEMPLATE_PATH = Path("templates/subject.txt")
BODY_TEMPLATE_PATH = Path("templates/body.html")


def _load_config() -> dict:
    if not CONFIG_PATH.exists():
        console.print(
            f"[red]Config file not found:[/red] {CONFIG_PATH}\n"
            "Run [bold]python main.py init[/bold] to create a starter config."
        )
        sys.exit(1)
    with open(CONFIG_PATH) as f:
        return json.load(f)


def _load_template(path: Path) -> str:
    if not path.exists():
        console.print(f"[red]Template not found:[/red] {path}")
        sys.exit(1)
    return path.read_text(encoding="utf-8")


# ── commands ────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Bulk Gmail Mailer with HTML→PPT attachments and tag-based personalisation."""


@cli.command()
def auth():
    """Run the Gmail OAuth2 flow and save credentials."""
    from src.auth import get_gmail_service
    console.print("[bold]Authenticating with Gmail…[/bold]")
    service = get_gmail_service()
    profile = service.users().getProfile(userId="me").execute()
    console.print(f"[green]Authenticated as:[/green] {profile['emailAddress']}")


@cli.command()
@click.option("--dry-run", is_flag=True, help="Print what would be sent without sending.")
@click.option("--no-pptx", is_flag=True, help="Send HTML email only, no PPT attachment.")
@click.option("--recipients", default=str(RECIPIENTS_PATH), show_default=True)
@click.option("--subject", default=str(SUBJECT_TEMPLATE_PATH), show_default=True)
@click.option("--body", default=str(BODY_TEMPLATE_PATH), show_default=True)
def send(dry_run, no_pptx, recipients, subject, body):
    """Send bulk emails to all recipients in the CSV."""
    from src.auth import get_gmail_service
    from src.mailer import send_bulk

    config = _load_config()
    subject_tmpl = _load_template(Path(subject))
    body_tmpl = _load_template(Path(body))

    if dry_run:
        console.print(Panel("[bold yellow]DRY RUN MODE — no emails will be sent[/bold yellow]"))
        service = None
    else:
        service = get_gmail_service()

    send_bulk(
        service=service,
        config=config,
        recipients_csv=recipients,
        subject_template=subject_tmpl,
        body_html_template=body_tmpl,
        attach_as_pptx=not no_pptx,
        dry_run=dry_run,
    )


@cli.command()
@click.option("--recipient", default=str(RECIPIENTS_PATH), show_default=True)
@click.option("--index", default=1, show_default=True, help="Row number (1-based) to preview.")
def preview(recipient, index):
    """Render subject + body for a single recipient and display it."""
    import csv
    from src import template_engine

    subject_tmpl = _load_template(SUBJECT_TEMPLATE_PATH)
    body_tmpl = _load_template(BODY_TEMPLATE_PATH)

    with open(recipient, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if index < 1 or index > len(rows):
        console.print(f"[red]Index {index} out of range (1–{len(rows)}).[/red]")
        sys.exit(1)

    row = rows[index - 1]
    rendered_subject = template_engine.render(subject_tmpl, row, index=index)
    rendered_body = template_engine.render(body_tmpl, row, index=index)

    console.print(Panel(f"[bold]Subject:[/bold] {rendered_subject}", title="Preview"))
    console.print(Syntax(rendered_body, "html", theme="monokai", line_numbers=False))


@cli.command()
def tags():
    """List all {{tags}} found in the current subject and body templates."""
    from src import template_engine

    subject_tmpl = _load_template(SUBJECT_TEMPLATE_PATH)
    body_tmpl = _load_template(BODY_TEMPLATE_PATH)

    subject_tags = template_engine.list_tags(subject_tmpl)
    body_tags = template_engine.list_tags(body_tmpl)
    all_tags = list(dict.fromkeys(subject_tags + body_tags))

    builtin = {"date", "time", "index", "random_id"}

    table = Table(title="Template Tags", show_header=True, header_style="bold magenta")
    table.add_column("Tag", style="cyan")
    table.add_column("Source")
    table.add_column("Type")

    for tag in all_tags:
        sources = []
        if tag in subject_tags:
            sources.append("subject")
        if tag in body_tags:
            sources.append("body")
        kind = "[dim]built-in[/dim]" if tag in builtin else "[green]CSV column[/green]"
        table.add_row(f"{{{{{tag}}}}}", ", ".join(sources), kind)

    console.print(table)
    if not all_tags:
        console.print("[yellow]No tags found in templates.[/yellow]")


@cli.command()
def init():
    """Create starter config, templates, and sample CSV."""
    _create_starter_files()
    console.print("[green]Starter files created.[/green] Edit them before running [bold]send[/bold].")


def _create_starter_files():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    Path("templates").mkdir(exist_ok=True)

    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps({
            "sender_email": "you@gmail.com",
            "sender_names": ["Your Name", "Your Brand", "Your Team"],
            "delay_seconds": 1.5,
            "max_per_run": 0
        }, indent=2))
        console.print(f"[cyan]Created[/cyan] {CONFIG_PATH}")

    sample_csv = Path("data/recipients.csv")
    if not sample_csv.exists():
        sample_csv.write_text(
            "email,first_name,last_name,company,position\n"
            "alice@example.com,Alice,Smith,Acme Corp,CEO\n"
            "bob@example.com,Bob,Jones,Beta Ltd,CTO\n"
        )
        console.print(f"[cyan]Created[/cyan] {sample_csv}")

    subject_file = Path("templates/subject.txt")
    if not subject_file.exists():
        subject_file.write_text(
            "Hello {{first_name}}, exciting news from our team!"
        )
        console.print(f"[cyan]Created[/cyan] {subject_file}")

    body_file = Path("templates/body.html")
    if not body_file.exists():
        body_file.write_text("""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;">

<h1>Hello {{first_name}} {{last_name}}!</h1>

<p>We hope this message finds you well at <strong>{{company}}</strong>.</p>

<h2>Why we're reaching out</h2>
<p>
  As {{position}} at {{company}}, you understand how important it is to stay
  ahead of the curve. We wanted to share something special with you today
  on <em>{{date}}</em>.
</p>

<h2>Key Highlights</h2>
<ul>
  <li>Personalised just for you</li>
  <li>Delivered on {{date}} at {{time}}</li>
  <li>Reference: {{random_id}}</li>
</ul>

<p>Best regards,<br>The Team</p>

</body>
</html>
""")
        console.print(f"[cyan]Created[/cyan] {body_file}")

    creds_sample = Path("config/credentials.sample.json")
    if not creds_sample.exists():
        creds_sample.write_text(json.dumps({
            "installed": {
                "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
                "client_secret": "YOUR_CLIENT_SECRET",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        }, indent=2))
        console.print(f"[cyan]Created[/cyan] {creds_sample}  ← rename to credentials.json after filling in")


if __name__ == "__main__":
    cli()
