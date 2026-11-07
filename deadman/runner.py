"""Run a job, stream its output, and remember how it ended."""

from __future__ import annotations

import subprocess
import sys
import time
from collections import deque
from dataclasses import dataclass
from typing import List, Sequence

TAIL_LINES = 12


@dataclass
class RunResult:
    exit_code: int
    duration: float
    tail: List[str]

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def run_command(command: Sequence[str]) -> RunResult:
    start = time.time()
    tail: deque = deque(maxlen=TAIL_LINES)
    process = subprocess.Popen(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    for line in process.stdout:
        sys.stdout.write(line)
        sys.stdout.flush()
        tail.append(line.rstrip("\n"))
    exit_code = process.wait()
    return RunResult(exit_code=exit_code, duration=time.time() - start, tail=list(tail))
