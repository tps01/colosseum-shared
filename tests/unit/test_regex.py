"""U-SH: regex verify_match latest-key lookup."""

from __future__ import annotations

from pathlib import Path

import colosseum as col
import pytest
from colosseum.config import load_config
from colosseum.decorators import measurement


@measurement
def _record_text(*, key: str, value: str) -> str:
    _ = key
    return value


def test_verify_match_finds_measurement_by_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "bench.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    _record_text(key="marker", value="second")
    result = col.shared.regex.verify_match(key="marker", pattern=r"^second$")
    assert result.status == "PASS"
