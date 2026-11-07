"""Find jobs that have not succeeded within their expected schedule.

A job is on time if its last success is no older than `every + grace`.
This is the dead man's switch: the check itself runs on a schedule, and
any job that goes silent is reported, even if it never reported a failure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from .durations import format_seconds, parse_duration

DEFAULT_GRACE = "10m"


@dataclass
class JobSpec:
    name: str
    every: int   # seconds between expected successes
    grace: int   # extra seconds tolerated before alerting


@dataclass
class Problem:
    name: str
    reason: str


def load_jobs(config: Dict[str, Any]) -> List[JobSpec]:
    jobs = []
    for raw in config.get("jobs", []):
        jobs.append(JobSpec(
            name=raw["name"],
            every=parse_duration(raw["every"]),
            grace=parse_duration(raw.get("grace", DEFAULT_GRACE)),
        ))
    return jobs


def check(jobs: List[JobSpec], state: Dict[str, Any], now: float) -> List[Problem]:
    problems: List[Problem] = []
    recorded = state.get("jobs", {})
    for job in jobs:
        record = recorded.get(job.name, {})
        last_success = record.get("last_success")
        if last_success is None:
            problems.append(Problem(job.name, "has never succeeded"))
            continue
        age = now - last_success
        if age > job.every + job.grace:
            problems.append(Problem(
                job.name,
                f"last success was {format_seconds(age)} ago (expected every {format_seconds(job.every)})",
            ))
    return problems
