"""Session-based authentication helpers.

Lightweight auth on top of Flask's signed-cookie session — no extra deps.
Passwords are hashed with werkzeug. ``login_required`` guards dashboard routes;
``current_user`` loads the logged-in user row (or None).
"""

from __future__ import annotations

import functools
import re

from flask import g, redirect, session, url_for

from saas import models

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email.strip()))


def login_user(user_id: int) -> None:
    session.clear()
    session["user_id"] = user_id


def logout_user() -> None:
    session.clear()


def current_user():
    if "user" in g:
        return g.user
    uid = session.get("user_id")
    g.user = models.get_user(uid) if uid else None
    return g.user


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped
