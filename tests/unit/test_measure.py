"""U-SH-MEASURE: one-off measure helpers and related verifies."""

from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING

import colosseum as col
from colosseum.config import load_config
from colosseum.context import get_context
from colosseum.runner.paths import ensure_runtime_ready

if TYPE_CHECKING:
    import pytest


def _load_shared_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "config.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    ensure_runtime_ready(get_context())


def test_measure_value_and_verify_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    col.shared.measure_value(key="literal", value="hello")
    assert col.shared.verify.verify_field(key="literal", expected_val="hello").status == "PASS"


def test_measure_env_and_verify_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setenv("COLOSSEUM_SHARED_TEST_ENV", "from-env")
    col.shared.measure_env(key="env_val", name="COLOSSEUM_SHARED_TEST_ENV")
    assert col.shared.verify.verify_env(
        key="env_val", expected="from-env",
    ).status == "PASS"
    assert col.shared.verify.verify_env(
        key="env_val", expected="wrong",
    ).status == "FAIL"


def test_measure_mark_and_verify_elapsed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    col.shared.measure_mark(key="t0")
    time.sleep(0.05)
    assert col.shared.verify.verify_elapsed(
        key="elapsed", mark_key="t0", maximum_s=5.0,
    ).status == "PASS"
    assert col.shared.verify.verify_elapsed(
        key="elapsed_fail", mark_key="t0", maximum_s=0.0,
    ).status == "FAIL"


def test_verify_pass_and_fail_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    assert col.shared.verify.verify_pass(key="ok", message="scaffold").status == "PASS"
    assert col.shared.verify.verify_fail(
        key="bad", message="debug", optional=True,
    ).status == "FAIL"
