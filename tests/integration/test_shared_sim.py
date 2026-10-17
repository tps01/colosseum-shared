"""I-SH: shared measure/verify/wait smoke on sim config."""

from __future__ import annotations

from pathlib import Path

import colosseum as col
import colosseum.context as context_module
import pytest
from colosseum.config import load_config

_VERSION_PATTERN = r"v\d+\.\d+\.\d+"


def test_measure_value_wait_and_regex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "config.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    ctx = context_module.init_context(test_case_name="shared_sim")
    ctx.output_dir = tmp_path
    ctx.db.initialize(tmp_path / "execution.sqlite")
    load_config(config_path)
    col.shared.measure_value(key="uut_version", value="v1.2.3")
    col.shared.wait(duration="10ms")
    assert col.shared.verify.verify_field(key="uut_version", expected_val="v1.2.3").status == "PASS"
    result = col.shared.regex.verify_match(key="uut_version", pattern=_VERSION_PATTERN)
    assert result.status == "PASS"
    with pytest.raises(SystemExit) as exc_info:
        col.endex()
    assert exc_info.value.code in (None, 0)
