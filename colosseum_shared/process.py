"""Run a local program and record its stdout and exit code."""

from __future__ import annotations

import subprocess
import threading
import time
from math import isfinite
from typing import TYPE_CHECKING

from colosseum.decorators import measurement
from colosseum.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

_logger = get_logger("colosseum.shared")


def _read_stream(
    stream: object,
    sink: list[str],
    halt: threading.Event,
    terminator: str | None,
    found_terminator: threading.Event | None,
) -> None:
    reader = getattr(stream, "readline", None)
    if reader is None:
        return
    while not halt.is_set():
        line = reader()
        if not isinstance(line, str) or line == "":
            return
        sink.append(line)
        if terminator is not None and terminator in "".join(sink):
            if found_terminator is not None:
                found_terminator.set()
            return


@measurement
def run_process(
    *,
    key: str,
    argv: Sequence[str],
    stdin_line: str | None = None,
    terminator: str | None = None,
    timeout_s: float = 10.0,
) -> dict[str, object]:
    """Run a local program, send one stdin line, and record stdout and the exit code.

    Reading stops at ``terminator``, when the process exits, or at ``timeout_s``.
    Timeout kills the process. ``timed_out`` is false when ``terminator`` was seen.
    ``exit_code`` is ``None`` when the process is killed before it exits. This is
    not a terminal emulator and not a serial port.

    Closing one pipe (for example stderr) does not end the wait while the child
    is still alive; only terminator, process exit, or ``timeout_s`` complete it.

    :param key: Unique measurement key within domain ``shared``.
    :type key: str
    :param argv: Program and arguments. The program is not invoked through a shell.
    :type argv: Sequence[str]
    :param stdin_line: Optional line written to stdin, without a newline.
    :type stdin_line: str | None, optional
    :param terminator: Stop reading stdout once this text appears.
    :type terminator: str | None, optional
    :param timeout_s: Maximum wait in seconds. Finite and nonnegative.
    :type timeout_s: float, optional

    :returns: ``stdout``, ``stderr``, ``exit_code``, and ``timed_out``.
    :rtype: dict[str, object]
    """
    _ = key
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise ValueError(f"timeout_s must be a finite nonnegative number, got {timeout_s!r}")
    if not isfinite(timeout_s) or timeout_s < 0:
        raise ValueError(f"timeout_s must be a finite nonnegative number, got {timeout_s!r}")
    if not argv:
        raise ValueError("argv must not be empty")
    process = subprocess.Popen(
        list(argv),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout_parts: list[str] = []
    stderr_parts: list[str] = []
    halt = threading.Event()
    found_terminator = threading.Event()
    threads = (
        threading.Thread(
            target=_read_stream,
            args=(process.stdout, stdout_parts, halt, terminator, found_terminator),
            daemon=True,
        ),
        threading.Thread(
            target=_read_stream,
            args=(process.stderr, stderr_parts, halt, None, None),
            daemon=True,
        ),
    )
    for thread in threads:
        thread.start()
    if process.stdin is not None:
        if stdin_line is not None:
            process.stdin.write(stdin_line + "\n")
            process.stdin.flush()
        process.stdin.close()

    deadline = time.monotonic() + timeout_s
    timed_out = False
    while True:
        if found_terminator.is_set():
            break
        if process.poll() is not None:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        time.sleep(min(0.05, remaining))

    halt.set()
    if process.poll() is None:
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    for thread in threads:
        thread.join(timeout=1)
    stdout = "".join(stdout_parts)
    saw_terminator = terminator is not None and terminator in stdout
    if saw_terminator and terminator is not None:
        stdout = stdout[: stdout.index(terminator) + len(terminator)]
    exit_code = None if timed_out else process.returncode
    _logger.debug(
        "run_process key=%s timed_out=%s exit_code=%s", key, timed_out, exit_code,
    )
    return {
        "stdout": stdout,
        "stderr": "".join(stderr_parts),
        "exit_code": exit_code,
        "timed_out": timed_out,
    }
