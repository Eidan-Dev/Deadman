"""Parse and format human durations: 30s, 5m, 24h, 7d."""

from __future__ import annotations

import re

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_PATTERN = re.compile(r"\s*(\d+)\s*([smhd])\s*")


def parse_duration(text: str) -> int:
    """Return the number of seconds for a string such as '24h'."""
    match = _PATTERN.fullmatch(str(text))
    if not match:
        raise ValueError(f"invalid duration {text!r}: use a number and s, m, h or d (e.g. 24h)")
    return int(match.group(1)) * _UNITS[match.group(2)]


def format_seconds(seconds: float) -> str:
    """Return a short human description: 45s, 12m, 3h, 2d."""
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"
