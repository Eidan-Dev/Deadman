"""Send alerts to a webhook. Stdlib only.

The payload contains both "text" (Slack, most chat tools) and "content"
(Discord), so one URL works with either.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional


def send_webhook(url: str, message: str, timeout: int = 10) -> Optional[str]:
    """POST the message. Return None on success, or an error description."""
    body = json.dumps({"text": message, "content": message}).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", "User-Agent": "deadman"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout):
            return None
    except urllib.error.HTTPError as exc:
        return f"webhook returned HTTP {exc.code}"
    except urllib.error.URLError as exc:
        return f"webhook unreachable: {exc.reason}"
