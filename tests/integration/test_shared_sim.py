"""I-SH: shared regex against a prior measurement key."""

from __future__ import annotations

from pathlib import Path

import colosseum as col
import pytest
from colosseum.config import load_config
from colosseum.decorators import measurement

_VERSION_PATTERN = r"v\d+\.\d+\.\d+"


@measurement
def _record_text(*, key: str, value: str) -> str:
    _ = key
    return value


def test_regex_verify_latest_measurement_by_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "config.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    _record_text(key="uut_version", value="v1.2.3")
    result = col.shared.regex.verify_match(key="uut_version", pattern=_VERSION_PATTERN)
    assert result.status == "PASS"
    with pytest.raises(SystemExit) as exc_info:
        col.endex()
    assert exc_info.value.code in (None, 0)
