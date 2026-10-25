"""Cross-platform stdin helpers for operator prompts."""

from __future__ import annotations

import sys
import time
from math import isfinite


def _timeout_seconds(timeout_s: float | None) -> float | None:
    if timeout_s is None:
        return None
    if isinstance(timeout_s, bool) or not isinstance(timeout_s, (int, float)):
        raise ValueError(f"timeout_s must be a finite nonnegative number, got {timeout_s!r}")
    number = float(timeout_s)
    if not isfinite(number) or number < 0:
        raise ValueError(f"timeout_s must be a finite nonnegative number, got {timeout_s!r}")
    return number


def read_line(*, message: str, timeout_s: float | None = None) -> str | None:
    """Print ``message`` and return one line from stdin.

    :returns: The line without a trailing newline, or ``None`` when ``timeout_s`` elapses.
    """
    print(message, flush=True)
    limit = _timeout_seconds(timeout_s)
    if limit is None:
        return input()
    if sys.platform == "win32":
        return _windows_line(limit)
    return _posix_line(limit)


def wait_any_key(*, message: str, timeout_s: float | None = None) -> bool:
    """Print ``message``, then block until the operator presses any key.

    :returns: ``True`` when a key arrives. ``False`` when ``timeout_s`` elapses.
    """
    print(message, flush=True)
    print("Press any key to continue...", flush=True)
    limit = _timeout_seconds(timeout_s)
    if sys.platform == "win32":
        return _windows_key(limit)
    return _posix_key(limit)


def _posix_line(timeout_s: float) -> str | None:
    import select

    ready, _, _ = select.select([sys.stdin], [], [], timeout_s)
    if not ready:
        return None
    line = sys.stdin.readline()
    if line == "":
        return None
    return line.rstrip("\r\n")


def _posix_key(timeout_s: float | None) -> bool:
    if sys.platform == "win32":
        raise RuntimeError("posix stdin is not used on Windows")
    import termios
    import tty

    if timeout_s is not None:
        import select

        ready, _, _ = select.select([sys.stdin], [], [], timeout_s)
        if not ready:
            return False
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return True


def _windows_line(timeout_s: float) -> str | None:
    import msvcrt

    deadline = time.monotonic() + timeout_s
    chars: list[str] = []
    while True:
        if msvcrt.kbhit():  # type: ignore[attr-defined]
            char = msvcrt.getwch()  # type: ignore[attr-defined]
            if char in ("\r", "\n"):
                print(flush=True)
                return "".join(chars)
            if char == "\x03":
                raise KeyboardInterrupt
            if char != "\x08":
                chars.append(char)
            elif chars:
                chars.pop()
            continue
        if time.monotonic() >= deadline:
            return None
        time.sleep(0.02)


def _windows_key(timeout_s: float | None) -> bool:
    import msvcrt

    if timeout_s is None:
        msvcrt.getch()  # type: ignore[attr-defined]
        return True
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if msvcrt.kbhit():  # type: ignore[attr-defined]
            msvcrt.getch()  # type: ignore[attr-defined]
            return True
        time.sleep(0.02)
    return False
