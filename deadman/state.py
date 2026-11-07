"""Local state: when each job last ran and last succeeded.

Stored as JSON in $DEADMAN_HOME/state.json (default: ~/.deadman/state.json).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def default_state_path() -> Path:
    home = os.environ.get("DEADMAN_HOME")
    base = Path(home) if home else Path.home() / ".deadman"
    return base / "state.json"


def load(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"jobs": {}}
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    data.setdefault("jobs", {})
    return data


def save(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)  # atomic: a crash never leaves a half-written file


def record_run(data: Dict[str, Any], name: str, *, ok: bool, exit_code: int,
               duration: float, now: float) -> None:
    job = data["jobs"].setdefault(name, {})
    job["last_run"] = now
    job["last_exit"] = exit_code
    job["last_duration"] = round(duration, 2)
    if ok:
        job["last_success"] = now
