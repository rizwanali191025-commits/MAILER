"""Central path resolution.

Works in two modes:
  - Development  (python app.py / python main.py) — all paths are relative
    to the project root.
  - Frozen       (PyInstaller .exe / .app) — user-editable files live next
    to the executable; read-only bundled resources live in sys._MEIPASS.
"""

import sys
from pathlib import Path


def _frozen() -> bool:
    return getattr(sys, "frozen", False)


def get_data_dir() -> Path:
    """Root for user-editable files: config, data, templates."""
    if _frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def get_bundle_dir() -> Path:
    """Root for read-only bundled files: web UI templates + static assets."""
    if _frozen():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


DATA_DIR   = get_data_dir()
BUNDLE_DIR = get_bundle_dir()

# user-editable
CONFIG_PATH       = DATA_DIR / "config" / "settings.json"
CREDENTIALS_PATH  = DATA_DIR / "config" / "credentials.json"
TOKEN_PATH        = DATA_DIR / "config" / "token.json"
CREDS_SAMPLE_PATH = DATA_DIR / "config" / "credentials.sample.json"
RECIPIENTS_PATH   = DATA_DIR / "data"      / "recipients.csv"
SUBJECT_PATH      = DATA_DIR / "templates" / "subject.txt"
BODY_PATH         = DATA_DIR / "templates" / "body.html"

# bundled read-only
WEB_TEMPLATES_DIR = BUNDLE_DIR / "web" / "templates"
WEB_STATIC_DIR    = BUNDLE_DIR / "web" / "static"
