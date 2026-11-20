"""Cross-platform stdin helpers for operator prompts."""

from __future__ import annotations

import os
import sys
import time
from math import isfinite
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


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

    :returns: The line without a trailing newline, or ``None`` at EOF or timeout.
    """
    print(message, flush=True)
    limit = _timeout_seconds(timeout_s)
    if not sys.stdin.isatty():
        return _pipe_line(limit)
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
    if not sys.stdin.isatty():
        return _pipe_line(limit) is not None
    if sys.platform == "win32":
        return _windows_key(limit)
    return _posix_key(limit)


def _pipe_line(timeout_s: float | None) -> str | None:
    """Read a redirected line, including an unterminated line at EOF."""
    import codecs

    deadline = None if timeout_s is None else time.monotonic() + timeout_s
    decoder = codecs.getincrementaldecoder(sys.stdin.encoding or "utf-8")("replace")
    chars: list[str] = []
    fd = sys.stdin.fileno()
    if sys.platform == "win32":
        windows_ready = _windows_pipe_waiter(fd)
    else:
        import select

    while True:
        if sys.platform == "win32":
            ready = windows_ready(deadline)
        else:
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            ready = bool(select.select([fd], [], [], remaining)[0])
        if ready is None:
            break
        if not ready:
            return None
        data = os.read(fd, 1)
        if not data:
            break
        char = decoder.decode(data)
        if char == "\n":
            return "".join(chars).rstrip("\r")
        chars.append(char)

    line = "".join(chars) + decoder.decode(b"", final=True)
    return line.rstrip("\r") if line else None


def _windows_pipe_waiter(fd: int) -> Callable[[float | None], bool | None]:
    """Return a readiness check with ``None`` for a closed pipe."""
    if sys.platform != "win32":
        raise RuntimeError("Windows pipe polling is only available on Windows")
    import ctypes
    import msvcrt
    from ctypes import wintypes

    handle = msvcrt.get_osfhandle(fd)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_type = kernel32.GetFileType
    get_type.argtypes = [wintypes.HANDLE]
    get_type.restype = wintypes.DWORD
    if get_type(handle) == 1:  # Regular files are immediately readable.
        return lambda _deadline: True

    available = wintypes.DWORD()
    peek = kernel32.PeekNamedPipe
    peek.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                     wintypes.LPVOID, ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    peek.restype = wintypes.BOOL

    def ready(deadline: float | None) -> bool | None:
        while peek(handle, None, 0, None, ctypes.byref(available), None):
            if available.value:
                return True
            remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
            if remaining == 0:
                return False
            time.sleep(min(0.02, remaining) if remaining is not None else 0.02)
        return None if ctypes.get_last_error() == 109 else False  # ERROR_BROKEN_PIPE

    return ready


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
