"""Parse human duration strings for ``col.shared.wait``."""

from __future__ import annotations

import re
from math import isfinite

_TOKEN_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)(?P<unit>w|d|h|ms|us|µs|m|s)",
    re.IGNORECASE,
)
_BARE_NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")

_UNIT_SECONDS = {
    "w": 604800.0,
    "d": 86400.0,
    "h": 3600.0,
    "m": 60.0,
    "s": 1.0,
    "ms": 0.001,
    "us": 1e-6,
    "µs": 1e-6,
}


def _finite_nonnegative_seconds(seconds: float, original: object) -> float:
    if not isfinite(seconds):
        raise ValueError(f"duration must be finite, got {original!r}")
    if seconds < 0:
        raise ValueError(f"duration must be non-negative, got {original!r}")
    return seconds


def parse_duration(duration: float | int | str) -> float:
    """Return a finite, non-negative duration in seconds.

    Bare numbers (``int``, ``float``, or numeric strings) are seconds.
    Unit suffixes follow common Python/timedelta style: ``us``/``µs``, ``ms``,
    ``s``, ``m``, ``h``, ``d``, ``w`` (combinable, e.g. ``1h30m``).
    Zero is allowed. Negative and non-finite values are rejected.
    """
    if isinstance(duration, (int, float)):
        return _finite_nonnegative_seconds(float(duration), duration)

    text = str(duration).strip()
    if not text:
        raise ValueError("duration must not be empty")
    if _BARE_NUMBER_RE.fullmatch(text):
        return _finite_nonnegative_seconds(float(text), duration)

    pos = 0
    total = 0.0
    for match in _TOKEN_RE.finditer(text):
        if match.start() != pos:
            break
        unit = match.group("unit").lower()
        total += float(match.group("value")) * _UNIT_SECONDS[unit]
        pos = match.end()
    else:
        if pos == len(text) and pos > 0:
            return _finite_nonnegative_seconds(total, duration)

    raise ValueError(
        f"Invalid duration {duration!r}; use a number of seconds or "
        "suffixes us/ms/s/m/h/d/w (e.g. 30, 500ms, 1h30m)",
    )
