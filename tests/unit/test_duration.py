"""Unit tests for duration parsing."""

from __future__ import annotations

import pytest
from colosseum_shared.duration import parse_duration


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2, 2.0),
        (2.5, 2.5),
        ("30", 30.0),
        ("1.5", 1.5),
        ("500ms", 0.5),
        ("2s", 2.0),
        ("1m", 60.0),
        ("1h30m", 5400.0),
        ("1d", 86400.0),
        ("1w", 604800.0),
        ("100us", 0.0001),
        ("1ms", 0.001),
    ],
)
def test_parse_duration(value: float | int | str, expected: float) -> None:
    assert parse_duration(value) == pytest.approx(expected)


def test_parse_duration_rejects_empty() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_duration("  ")


def test_parse_duration_rejects_negative() -> None:
    with pytest.raises(ValueError, match="non-negative"):
        parse_duration(-1)


def test_parse_duration_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="Invalid duration"):
        parse_duration("forever")
