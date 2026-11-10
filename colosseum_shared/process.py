"""Run a local program and record its stdout and exit code."""

from __future__ import annotations

import subprocess
import threading
import time
from enum import Enum
from math import isfinite
from typing import TYPE_CHECKING

from colosseum.decorators import measurement
from colosseum.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Sequence

_logger = get_logger("colosseum.shared")


class _WaitEvent(Enum):
    TERMINATOR = "terminator"
    EXITED = "exited"
    TIMEOUT = "timeout"


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


def _validate_run_process(*, argv: Sequence[str], timeout_s: float) -> None:
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise ValueError(f"timeout_s must be a finite nonnegative number, got {timeout_s!r}")
    if not isfinite(timeout_s) or timeout_s < 0:
        raise ValueError(f"timeout_s must be a finite nonnegative number, got {timeout_s!r}")
    if not argv:
        raise ValueError("argv must not be empty")


def _spawn_process_readers(
    *,
    argv: Sequence[str],
    terminator: str | None,
) -> tuple[
    subprocess.Popen[str],
    tuple[threading.Thread, threading.Thread],
    threading.Event,
    threading.Event,
    list[str],
    list[str],
]:
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
    return process, threads, halt, found_terminator, stdout_parts, stderr_parts


def _write_stdin(process: subprocess.Popen[str], stdin_line: str | None) -> None:
    if process.stdin is None:
        return
    if stdin_line is not None:
        process.stdin.write(stdin_line + "\n")
        process.stdin.flush()
    process.stdin.close()


def _wait_for_process_event(
    *,
    process: subprocess.Popen[str],
    found_terminator: threading.Event,
    deadline: float,
) -> _WaitEvent:
    while True:
        if found_terminator.is_set():
            return _WaitEvent.TERMINATOR
        if process.poll() is not None:
            return _WaitEvent.EXITED
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return _WaitEvent.TIMEOUT
        time.sleep(min(0.05, remaining))


def _halt_and_join(
    *,
    process: subprocess.Popen[str],
    halt: threading.Event,
    threads: tuple[threading.Thread, threading.Thread],
) -> None:
    halt.set()
    if process.poll() is None:
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    for thread in threads:
        thread.join(timeout=1)


def _trim_stdout(stdout: str, terminator: str | None) -> str:
    if terminator is not None and terminator in stdout:
        return stdout[: stdout.index(terminator) + len(terminator)]
    return stdout


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
    _validate_run_process(argv=argv, timeout_s=timeout_s)
    _logger.info("Running %s for measurement %s", argv[0], key)
    process, threads, halt, found_terminator, stdout_parts, stderr_parts = _spawn_process_readers(
        argv=argv, terminator=terminator
    )
    _write_stdin(process, stdin_line)

    event = _wait_for_process_event(
        process=process,
        found_terminator=found_terminator,
        deadline=time.monotonic() + timeout_s,
    )
    timed_out = event is _WaitEvent.TIMEOUT

    _halt_and_join(process=process, halt=halt, threads=threads)
    stdout = _trim_stdout("".join(stdout_parts), terminator)
    exit_code = None if timed_out else process.returncode
    _logger.debug(
        "run_process key=%s timed_out=%s exit_code=%s",
        key,
        timed_out,
        exit_code,
    )
    return {
        "stdout": stdout,
        "stderr": "".join(stderr_parts),
        "exit_code": exit_code,
        "timed_out": timed_out,
    }
