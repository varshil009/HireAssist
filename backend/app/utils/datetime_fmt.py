from __future__ import annotations

import re
from datetime import datetime, timezone

_ISO_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}")


def format_display_date(value) -> str:
    """Format as '22 September 2025' (day int, month word, year int)."""
    if value is None:
        return "—"
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        if not text:
            return "—"
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return f"{dt.day} {dt.strftime('%B')} {dt.year}"


def maybe_format_display_date(value):
    """Format ISO-like strings for UI; leave other values unchanged."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return format_display_date(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return value
        if "T" in text or _ISO_PREFIX.match(text):
            try:
                datetime.fromisoformat(text.replace("Z", "+00:00"))
                return format_display_date(text)
            except ValueError:
                return value
    return value
