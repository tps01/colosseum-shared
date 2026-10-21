"""Timed wait command (``col.shared.wait``)."""

from __future__ import annotations

import sys
import time
from math import isfinite

from colosseum.decorators import command
from colosseum.logging import get_logger

from colosseum_shared.duration import parse_duration

_logger = get_logger("colosseum.shared")


def _sleep_with_progress(seconds: float) -> None:
    if not isfinite(seconds) or seconds < 0:
        raise ValueError(f"duration must be finite and non-negative, got {seconds!r}")
    if seconds == 0:
        return
    width = 40
    start = time.monotonic()
    while True:
        elapsed = time.monotonic() - start
        if elapsed >= seconds:
            break
        frac = min(1.0, elapsed / seconds)
        filled = int(width * frac)
        bar = "#" * filled + "-" * (width - filled)
        sys.stdout.write(f"\r[{bar}] {elapsed:5.1f}/{seconds:.1f}s")
        sys.stdout.flush()
        time.sleep(min(0.1, seconds - elapsed))
    sys.stdout.write(f"\r[{'#' * width}] {seconds:.1f}/{seconds:.1f}s\n")
    sys.stdout.flush()


@command
def wait(*, duration: float | int | str, progress_bar: bool = False) -> None:
    """Block for ``duration``, optionally showing a CLI progress bar.

    :param duration: Wait length. Bare numbers are seconds; strings may use
        ``us``/``µs``, ``ms``, ``s``, ``m``, ``h``, ``d``, ``w`` (e.g. ``500ms``,
        ``1h30m``). Must be finite and nonnegative; zero returns immediately.
    :param progress_bar: When ``True``, print a progress bar to stdout while waiting.
    """
    seconds = parse_duration(duration)
    _logger.info("wait duration=%rs (%.3fs) progress_bar=%s", duration, seconds, progress_bar)
    if progress_bar:
        _sleep_with_progress(seconds)
    else:
        time.sleep(seconds)
