"""U-SH-PARSE: text parsing helpers."""

from __future__ import annotations

import pytest
from colosseum_shared.parsing.text import (
    first_match_group,
    parse_float,
    parse_float_list,
    parse_key_value_lines,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("gain = 12.5 dB", 12.5),
        ("rail=1.e3 V", 1000.0),
        ("1.E+3", 1000.0),
        ("1.e-3", 0.001),
        ("1E3", 1000.0),
        ("1e-2", 0.01),
        (".5 V", 0.5),
        (".5e1", 5.0),
        ("x=-.25e+1 y", -2.5),
        ("1.", 1.0),
        ("+2.5e1", 25.0),
        ("2.5e-1 units", 0.25),
        ("pre 1.2.3 post", 1.2),
    ],
)
def test_parse_float_complete_numeric_tokens(text: str, expected: float) -> None:
    assert parse_float(text) == pytest.approx(expected)


def test_parse_float_raises_when_absent() -> None:
    with pytest.raises(ValueError, match="No numeric value"):
        parse_float("no numbers here")


def test_parse_float_list_default_and_custom_sep() -> None:
    assert parse_float_list("1, 2.5, 3") == [1.0, 2.5, 3.0]
    assert parse_float_list("1;2;3", sep=";") == [1.0, 2.0, 3.0]
    assert parse_float_list("1,,2") == [1.0, 2.0]
    assert parse_float_list("") == []
    assert parse_float_list("   ") == []


def test_parse_key_value_lines() -> None:
    assert parse_key_value_lines("") == {}
    assert parse_key_value_lines("a=1\nb=2\nskip\nc=x=y") == {
        "a": "1",
        "b": "2",
        "c": "x=y",
    }


def test_first_match_group() -> None:
    assert first_match_group(r"v\d+\.\d+", "fw v1.2.3") == "v1.2"
    assert first_match_group(r"zzz", "fw v1.2.3") is None
