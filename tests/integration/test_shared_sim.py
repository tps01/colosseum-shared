"""I-SH: shared SSH + regex on sim."""

from __future__ import annotations

from pathlib import Path

import colosseum as col
import pytest
from colosseum.config import load_config

_VERSION_PATTERN = r"v\d+\.\d+\.\d+"


def test_ssh_measure_and_regex_verify(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "bench.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    col.shared.ssh.measure_stdout(ssh_id=1, command="cat /etc/version", key="uut_version")
    v_result = col.shared.regex.verify_match(key="uut_version", pattern=_VERSION_PATTERN)
    assert v_result.status == "PASS"
    col.shared.ssh.measure_stdout(
        ssh_id=1, command="test -f /etc/os-release && echo present", key="os_release_marker"
    )
    o_result = col.shared.regex.verify_match(key="os_release_marker", pattern=r"present")
    assert o_result.status == "PASS"
    with pytest.raises(SystemExit) as exc_info:
        col.endex()
    assert exc_info.value.code in (None, 0)
