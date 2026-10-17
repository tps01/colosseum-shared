"""U-SH-PARSE: text parsing helpers."""

from __future__ import annotations

import pytest
from colosseum_shared.parsing.text import first_match_group, parse_float


def test_parse_float_extracts_first_number() -> None:
    assert parse_float("gain = 12.5 dB") == pytest.approx(12.5)


def test_parse_float_raises_when_absent() -> None:
    with pytest.raises(ValueError, match="No numeric value"):
        parse_float("no numbers here")


def test_first_match_group() -> None:
    assert first_match_group(r"v\d+\.\d+", "fw v1.2.3") == "v1.2"
    assert first_match_group(r"zzz", "fw v1.2.3") is None
