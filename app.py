"""Flask web UI for the bulk mailer.

Run with:
    python app.py

Then open http://localhost:5000 in your browser.
"""

import csv
import io
import json
import threading
from pathlib import Path

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

from src import template_engine, html_to_ppt
from src.mailer import send_bulk

CONFIG_PATH = Path("config/settings.json")
RECIPIENTS_PATH = Path("data/recipients.csv")
SUBJECT_PATH = Path("templates/subject.txt")
BODY_PATH = Path("templates/body.html")
CREDENTIALS_PATH = Path("config/credentials.json")
TOKEN_PATH = Path("config/token.json")

app = Flask(
    __name__,
    template_folder="web/templates",
    static_folder="web/static",
)
app.secret_key = "change-this-in-production"

# in-memory log of the last send run
LAST_RUN: dict = {"status": "idle", "results": [], "running": False}


def _read(path: Path, default: str = "") -> str:
    return path.read_text(encoding="utf-8") if path.exists() else default


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        "sender_email": "",
        "sender_names": [],
        "delay_seconds": 1.5,
        "max_per_run": 0,
    }


# ── routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    config = _load_config()
    return render_template(
        "index.html",
        config=config,
        sender_names_str=", ".join(config.get("sender_names", [])),
        recipients_csv=_read(RECIPIENTS_PATH),
        subject_tmpl=_read(SUBJECT_PATH),
        body_tmpl=_read(BODY_PATH),
        credentials_present=CREDENTIALS_PATH.exists(),
        token_present=TOKEN_PATH.exists(),
        last_run=LAST_RUN,
    )


@app.route("/save", methods=["POST"])
def save():
    """Save all editable fields back to disk."""
    config = {
        "sender_email": request.form.get("sender_email", "").strip(),
        "sender_names": [
            n.strip() for n in request.form.get("sender_names", "").split(",") if n.strip()
        ],
        "delay_seconds": float(request.form.get("delay_seconds", 1.5)),
        "max_per_run": int(request.form.get("max_per_run", 0)),
    }
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))

    _write(RECIPIENTS_PATH, request.form.get("recipients_csv", ""))
    _write(SUBJECT_PATH, request.form.get("subject_tmpl", ""))
    _write(BODY_PATH, request.form.get("body_tmpl", ""))

    flash("Saved.", "success")
    return redirect(url_for("index"))


@app.route("/preview", methods=["POST"])
def preview():
    """Render subject + body for one recipient row."""
    index = int(request.form.get("index", 1))
    subject_tmpl = request.form.get("subject_tmpl", "")
    body_tmpl = request.form.get("body_tmpl", "")
    recipients_csv = request.form.get("recipients_csv", "")

    rows = list(csv.DictReader(io.StringIO(recipients_csv)))
    if not rows:
        return jsonify({"error": "No recipients in CSV."}), 400
    if index < 1 or index > len(rows):
        return jsonify({"error": f"Index {index} out of range (1–{len(rows)})."}), 400

    row = rows[index - 1]
    subject = template_engine.render(subject_tmpl, row, index=index)
    body = template_engine.render(body_tmpl, row, index=index)
    tags_used = list(set(
        template_engine.list_tags(subject_tmpl)
        + template_engine.list_tags(body_tmpl)
    ))
    return jsonify({
        "subject": subject,
        "body": body,
        "recipient": row,
        "tags": tags_used,
    })


@app.route("/auth", methods=["POST"])
def auth():
    """Trigger the Gmail OAuth2 flow (opens browser on the server machine)."""
    try:
        from src.auth import get_gmail_service
        service = get_gmail_service()
        profile = service.users().getProfile(userId="me").execute()
        flash(f"Authenticated as {profile['emailAddress']}.", "success")
    except FileNotFoundError as e:
        flash(str(e), "error")
    except Exception as e:
        flash(f"Auth failed: {e}", "error")
    return redirect(url_for("index"))


@app.route("/send", methods=["POST"])
def send():
    """Kick off a send run (dry-run or real) in a background thread."""
    if LAST_RUN["running"]:
        return jsonify({"error": "A send is already running."}), 409

    dry_run = request.form.get("dry_run") == "1"
    attach_pptx = request.form.get("attach_pptx") == "1"

    config = _load_config()
    subject_tmpl = _read(SUBJECT_PATH)
    body_tmpl = _read(BODY_PATH)

    if not config.get("sender_email"):
        return jsonify({"error": "sender_email is empty. Save your config first."}), 400
    if not config.get("sender_names"):
        return jsonify({"error": "sender_names is empty. Save your config first."}), 400

    def worker():
        LAST_RUN["running"] = True
        LAST_RUN["status"] = "running"
        LAST_RUN["results"] = []
        try:
            if dry_run:
                service = None
            else:
                from src.auth import get_gmail_service
                service = get_gmail_service()

            results = send_bulk(
                service=service,
                config=config,
                recipients_csv=str(RECIPIENTS_PATH),
                subject_template=subject_tmpl,
                body_html_template=body_tmpl,
                attach_as_pptx=attach_pptx,
                dry_run=dry_run,
            )
            LAST_RUN["results"] = results
            LAST_RUN["status"] = "done"
        except Exception as e:
            LAST_RUN["status"] = f"error: {e}"
        finally:
            LAST_RUN["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"status": "started", "dry_run": dry_run})


@app.route("/status")
def status():
    return jsonify(LAST_RUN)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
