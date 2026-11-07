import json
from pathlib import Path

import pytest

from deadman.checker import check, load_jobs
from deadman.cli import main
from deadman.durations import format_seconds, parse_duration
from deadman.state import load, record_run, save


def test_parse_duration_units():
    assert parse_duration("30s") == 30
    assert parse_duration("5m") == 300
    assert parse_duration("24h") == 86400
    assert parse_duration("7d") == 604800


def test_parse_duration_rejects_garbage():
    with pytest.raises(ValueError):
        parse_duration("tomorrow")


def test_format_seconds():
    assert format_seconds(45) == "45s"
    assert format_seconds(3 * 3600) == "3h"
    assert format_seconds(2 * 86400) == "2d"


def test_never_succeeded_is_reported():
    jobs = load_jobs({"jobs": [{"name": "backup", "every": "1d"}]})
    problems = check(jobs, {"jobs": {}}, now=1_000_000)
    assert [p.name for p in problems] == ["backup"]
    assert "never succeeded" in problems[0].reason


def test_on_time_job_is_not_reported():
    jobs = load_jobs({"jobs": [{"name": "backup", "every": "1d", "grace": "1h"}]})
    now = 1_000_000
    state = {"jobs": {"backup": {"last_success": now - 3600}}}
    assert check(jobs, state, now) == []


def test_silent_job_is_reported_even_without_failure():
    """The core idea: a job that stops running is caught, not only one that fails."""
    jobs = load_jobs({"jobs": [{"name": "backup", "every": "1d", "grace": "1h"}]})
    now = 1_000_000
    state = {"jobs": {"backup": {"last_success": now - 2 * 86400}}}
    problems = check(jobs, state, now)
    assert len(problems) == 1
    assert "expected every 1d" in problems[0].reason


def test_failed_run_does_not_refresh_last_success(tmp_path: Path):
    data = {"jobs": {}}
    record_run(data, "backup", ok=True, exit_code=0, duration=1.0, now=100)
    record_run(data, "backup", ok=False, exit_code=3, duration=1.0, now=200)
    assert data["jobs"]["backup"]["last_success"] == 100
    assert data["jobs"]["backup"]["last_exit"] == 3


def test_state_roundtrip(tmp_path: Path):
    path = tmp_path / "state.json"
    data = {"jobs": {}}
    record_run(data, "sync", ok=True, exit_code=0, duration=2.5, now=50)
    save(path, data)
    assert load(path)["jobs"]["sync"]["last_duration"] == 2.5


def test_cli_run_records_success_and_failure(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DEADMAN_HOME", str(tmp_path))

    assert main(["run", "ok-job", "--", "python3", "-c", "print('hi')"]) == 0
    assert main(["run", "bad-job", "--", "python3", "-c", "import sys; sys.exit(4)"]) == 4

    recorded = json.loads((tmp_path / "state.json").read_text())["jobs"]
    assert "last_success" in recorded["ok-job"]
    assert "last_success" not in recorded["bad-job"]
    assert recorded["bad-job"]["last_exit"] == 4
    assert "FAILED with exit code 4" in capsys.readouterr().out


def test_cli_check_exit_codes(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DEADMAN_HOME", str(tmp_path))
    config = tmp_path / "deadman.json"
    config.write_text(json.dumps({"jobs": [{"name": "backup", "every": "1d"}]}))

    assert main(["check", "--config", str(config)]) == 1  # never ran
    assert "never succeeded" in capsys.readouterr().out
