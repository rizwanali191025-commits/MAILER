"""Data-access helpers for users, campaigns, and send events.

Thin functions over the sqlite connection returned by :func:`saas.db.get_db`.
Keeping SQL in one place makes the route handlers read like business logic.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from werkzeug.security import check_password_hash, generate_password_hash

from saas.db import get_db
from saas.plans import get_plan


# ── users ───────────────────────────────────────────────────────────────────

def create_user(email: str, password: str) -> int:
    db = get_db()
    cur = db.execute(
        "INSERT INTO users (email, password_hash) VALUES (?, ?)",
        (email.strip().lower(), generate_password_hash(password)),
    )
    db.commit()
    return cur.lastrowid


def get_user_by_email(email: str) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
    ).fetchone()


def get_user(user_id: int) -> sqlite3.Row | None:
    return get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def verify_credentials(email: str, password: str) -> sqlite3.Row | None:
    user = get_user_by_email(email)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None


def update_user_plan(user_id: int, plan_id: str) -> None:
    db = get_db()
    db.execute("UPDATE users SET plan_id = ? WHERE id = ?", (plan_id, user_id))
    db.commit()


def update_sender_settings(user_id: int, sender_email: str, sender_names: str) -> None:
    db = get_db()
    db.execute(
        "UPDATE users SET sender_email = ?, sender_names = ? WHERE id = ?",
        (sender_email.strip(), sender_names.strip(), user_id),
    )
    db.commit()


# ── campaigns ────────────────────────────────────────────────────────────────

STARTER_SUBJECT = "Hi {{first_name}}, a quick note from {{sender}}"
STARTER_BODY = (
    "<h1>Hello {{first_name}}!</h1>\n"
    "<p>Thanks for being part of {{company}}. We wanted to reach out "
    "personally on {{date}}.</p>\n"
    "<p>Best,<br>The Team</p>"
)
STARTER_CSV = "email,first_name,last_name,company,position\n"


def list_campaigns(user_id: int) -> list[sqlite3.Row]:
    return get_db().execute(
        "SELECT * FROM campaigns WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    ).fetchall()


def count_campaigns(user_id: int) -> int:
    return get_db().execute(
        "SELECT COUNT(*) AS n FROM campaigns WHERE user_id = ?", (user_id,)
    ).fetchone()["n"]


def get_campaign(user_id: int, campaign_id: int) -> sqlite3.Row | None:
    return get_db().execute(
        "SELECT * FROM campaigns WHERE id = ? AND user_id = ?",
        (campaign_id, user_id),
    ).fetchone()


def create_campaign(user_id: int, name: str) -> int:
    db = get_db()
    cur = db.execute(
        """INSERT INTO campaigns (user_id, name, subject_tmpl, body_tmpl, recipients_csv)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, name.strip() or "Untitled campaign",
         STARTER_SUBJECT, STARTER_BODY, STARTER_CSV),
    )
    db.commit()
    return cur.lastrowid


def update_campaign(
    user_id: int,
    campaign_id: int,
    *,
    name: str,
    subject_tmpl: str,
    body_tmpl: str,
    recipients_csv: str,
    attach_pptx: bool,
) -> None:
    db = get_db()
    db.execute(
        """UPDATE campaigns
              SET name = ?, subject_tmpl = ?, body_tmpl = ?, recipients_csv = ?,
                  attach_pptx = ?, updated_at = datetime('now')
            WHERE id = ? AND user_id = ?""",
        (name.strip() or "Untitled campaign", subject_tmpl, body_tmpl,
         recipients_csv, 1 if attach_pptx else 0, campaign_id, user_id),
    )
    db.commit()


def delete_campaign(user_id: int, campaign_id: int) -> None:
    db = get_db()
    db.execute(
        "DELETE FROM campaigns WHERE id = ? AND user_id = ?", (campaign_id, user_id)
    )
    db.commit()


# ── send events / usage ──────────────────────────────────────────────────────

def _month_key(when: datetime | None = None) -> str:
    return (when or datetime.utcnow()).strftime("%Y-%m")


def record_send_events(user_id: int, campaign_id: int, results: list[dict]) -> None:
    db = get_db()
    db.executemany(
        """INSERT INTO send_events (user_id, campaign_id, recipient, status, detail)
           VALUES (?, ?, ?, ?, ?)""",
        [
            (user_id, campaign_id, r.get("to", ""), r.get("status", "error"),
             str(r.get("error", r.get("id", ""))))
            for r in results
        ],
    )
    db.commit()


def sends_this_month(user_id: int) -> int:
    """Count real + dry-run sends in the current calendar month (usage meter)."""
    return get_db().execute(
        """SELECT COUNT(*) AS n FROM send_events
            WHERE user_id = ? AND strftime('%Y-%m', created_at) = ?""",
        (user_id, _month_key()),
    ).fetchone()["n"]


def recent_send_events(user_id: int, limit: int = 20) -> list[sqlite3.Row]:
    return get_db().execute(
        """SELECT e.*, c.name AS campaign_name
             FROM send_events e JOIN campaigns c ON c.id = e.campaign_id
            WHERE e.user_id = ?
            ORDER BY e.created_at DESC LIMIT ?""",
        (user_id, limit),
    ).fetchall()


# ── quota helpers ────────────────────────────────────────────────────────────

def remaining_quota(user: sqlite3.Row) -> int:
    plan = get_plan(user["plan_id"])
    used = sends_this_month(user["id"])
    return max(plan.monthly_send_limit - used, 0)


def can_create_campaign(user: sqlite3.Row) -> bool:
    plan = get_plan(user["plan_id"])
    if plan.campaign_limit < 0:
        return True
    return count_campaigns(user["id"]) < plan.campaign_limit


# ── app-wide sending account (operator) ──────────────────────────────────────

def get_app_config() -> sqlite3.Row:
    return get_db().execute("SELECT * FROM app_config WHERE id = 1").fetchone()


def save_app_config(smtp_email: str, smtp_password: str) -> None:
    db = get_db()
    db.execute(
        """UPDATE app_config
              SET smtp_email = ?, smtp_password = ?, updated_at = datetime('now')
            WHERE id = 1""",
        (smtp_email.strip(), smtp_password.replace(" ", "").strip()),
    )
    db.commit()


def sending_configured() -> bool:
    cfg = get_app_config()
    return bool(cfg["smtp_email"] and cfg["smtp_password"])
