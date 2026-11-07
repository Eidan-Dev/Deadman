"""Command-line interface.

  deadman run NAME -- COMMAND [ARGS...]   run a job and record the result
  deadman check [--config FILE]           report jobs that are late or silent
  deadman status [--config FILE]          show the last known state of each job
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from . import __version__
from .alert import send_webhook
from .checker import check, load_jobs
from .durations import format_seconds
from .runner import run_command
from .state import default_state_path, load, record_run, save

WEBHOOK_ENV = "DEADMAN_WEBHOOK"


def _alert(message: str) -> None:
    print(message)
    url = os.environ.get(WEBHOOK_ENV)
    if url:
        error = send_webhook(url, message)
        if error:
            print(f"  (could not send to webhook: {error})", file=sys.stderr)


def cmd_run(args: argparse.Namespace) -> int:
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("error: give a command after --, e.g. deadman run backup -- ./backup.sh", file=sys.stderr)
        return 2

    state_path = default_state_path()
    result = run_command(command)
    data = load(state_path)
    record_run(data, args.name, ok=result.ok, exit_code=result.exit_code,
               duration=result.duration, now=time.time())
    save(state_path, data)

    print("")
    if result.ok:
        print(f"✓ {args.name} succeeded in {result.duration:.1f}s")
    else:
        _alert(f"✗ {args.name} FAILED with exit code {result.exit_code} after {result.duration:.1f}s")
        if result.tail:
            print("  last output:")
            for line in result.tail[-5:]:
                print(f"    {line}")
    return result.exit_code


def _load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def cmd_check(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    jobs = load_jobs(config)
    problems = check(jobs, load(default_state_path()), time.time())

    if not problems:
        print(f"✓ all {len(jobs)} job(s) are on schedule")
        return 0

    for problem in problems:
        _alert(f"⚠ {problem.name} {problem.reason}")
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    jobs = load_jobs(config)
    recorded = load(default_state_path()).get("jobs", {})
    now = time.time()

    print(f"{'JOB':<16}{'STATUS':<12}{'LAST SUCCESS':<16}EXPECTED")
    for job in jobs:
        record = recorded.get(job.name, {})
        if not record:
            status, last = "never ran", "-"
        elif "last_success" not in record:
            status, last = f"FAILING ({record.get('last_exit')})", "-"
        else:
            on_time = now - record["last_success"] <= job.every + job.grace
            status = "ok" if on_time else "LATE"
            last = format_seconds(now - record["last_success"]) + " ago"
        print(f"{job.name:<16}{status:<12}{last:<16}every {format_seconds(job.every)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="deadman",
        description="Know the moment a scheduled job fails or silently stops running.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="run a job and record the result")
    run.add_argument("name", help="job name, e.g. backup")
    run.add_argument("command", nargs=argparse.REMAINDER, help="command to run, after --")
    run.set_defaults(func=cmd_run)

    for name, func, help_text in (
        ("check", cmd_check, "report jobs that failed or are late (run this from cron)"),
        ("status", cmd_status, "show the last known state of each job"),
    ):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--config", default="deadman.json", help="jobs file (default: deadman.json)")
        p.set_defaults(func=func)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
