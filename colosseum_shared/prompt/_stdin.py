"""Cross-platform stdin helpers for operator prompts."""

from __future__ import annotations

import sys


def read_line(*, message: str) -> str:
    """Print ``message`` and return one line from stdin."""
    print(message, flush=True)
    return input()


def wait_any_key(*, message: str) -> None:
    """Print ``message``, then block until the operator presses any key."""
    print(message, flush=True)
    print("Press any key to continue...", flush=True)
    if sys.platform == "win32":
        import msvcrt

        msvcrt.getch()
        return
    import termios
    import tty

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
