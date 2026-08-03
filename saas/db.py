"""SQLite connection management and schema bootstrap.

Uses the stdlib ``sqlite3`` (no extra dependencies). The connection is stored
on Flask's ``g`` per-request and closed on teardown. Rows come back as dict-like
``sqlite3.Row`` objects.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    email          TEXT    UNIQUE NOT NULL,
    password_hash  TEXT    NOT NULL,
    plan_id        TEXT    NOT NULL DEFAULT 'free',
    sender_email   TEXT    NOT NULL DEFAULT '',
    sender_names   TEXT    NOT NULL DEFAULT '',   -- comma-separated
    created_at     TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS campaigns (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    name           TEXT    NOT NULL,
    subject_tmpl   TEXT    NOT NULL DEFAULT '',
    body_tmpl      TEXT    NOT NULL DEFAULT '',
    recipients_csv TEXT    NOT NULL DEFAULT '',
    attach_pptx    INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at     TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS send_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    campaign_id   INTEGER NOT NULL,
    recipient     TEXT    NOT NULL,
    status        TEXT    NOT NULL,   -- sent | dry_run | error
    detail        TEXT    NOT NULL DEFAULT '',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_campaigns_user ON campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_send_events_user ON send_events(user_id, created_at);

-- Single shared sending account for the whole app (operator-configured).
-- One row (id = 1). All customers' real emails go out through this Gmail.
CREATE TABLE IF NOT EXISTS app_config (
    id            INTEGER PRIMARY KEY CHECK (id = 1),
    smtp_email    TEXT NOT NULL DEFAULT '',   -- the Gmail address that sends
    smtp_password TEXT NOT NULL DEFAULT '',    -- Gmail App Password (16 chars)
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
INSERT OR IGNORE INTO app_config (id) VALUES (1);
"""


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(app) -> None:
    db_path = Path(app.config["DATABASE"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    init_db(app)
