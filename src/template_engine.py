"""Tag-based template engine for email subject and body personalization.

Supports {{tag}} placeholders in any text. Tags are resolved from a
per-recipient data dict. Special built-in tags:
  {{date}}       — today's date (e.g. May 27, 2026)
  {{time}}       — current time (e.g. 14:30)
  {{index}}      — 1-based recipient index in the current send batch
  {{random_id}}  — short random hex string for tracking
"""

import re
import random
import string
from datetime import datetime

TAG_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def _builtin_tags(index: int) -> dict:
    now = datetime.now()
    return {
        "date": now.strftime("%B %d, %Y"),
        "time": now.strftime("%H:%M"),
        "index": str(index),
        "random_id": "".join(random.choices(string.hexdigits[:16], k=8)),
    }


def render(template: str, data: dict, index: int = 1) -> str:
    """Replace all {{tag}} occurrences with values from *data* or built-ins."""
    merged = {**_builtin_tags(index), **{k.lower(): str(v) for k, v in data.items()}}

    def replace(match):
        key = match.group(1).lower()
        return merged.get(key, match.group(0))  # keep original if tag not found

    return TAG_PATTERN.sub(replace, template)


def list_tags(template: str) -> list[str]:
    """Return all unique tag names found in *template*."""
    return list(dict.fromkeys(m.group(1) for m in TAG_PATTERN.finditer(template)))
