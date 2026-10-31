"""U-SH-META: intentional pass/fail markers under ``col.shared.meta``."""

from __future__ import annotations

from pathlib import Path

import colosseum as col
import pytest
from colosseum.config import load_config
from colosseum.context import get_context
from colosseum.runner.paths import ensure_runtime_ready


def _load_shared_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "config.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    ensure_runtime_ready(get_context())


def test_meta_command_pass_and_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    passed = col.shared.meta.command_pass(key="ok", message="scaffold")
    assert passed.status == "PASS"
    failed = col.shared.meta.command_fail(key="bad", message="debug", optional=True)
    assert failed.status == "FAIL"
    assert failed.optional is True


def test_meta_measure_pass_and_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    assert col.shared.meta.measure_pass(key="ok", value=3.3) == 3.3
    row = get_context().db.get_measurement("shared", "meta.measure_pass", "ok")
    assert row is not None
    assert row.status == "PASS"
    assert row.value == 3.3

    assert col.shared.meta.measure_fail(key="bad", optional=True) is None
    err = get_context().db.get_measurement("shared", "meta.measure_fail", "bad")
    assert err is not None
    assert err.status == "ERROR"


def test_meta_verify_pass_and_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    assert col.shared.meta.verify_pass(key="ok", message="scaffold").status == "PASS"
    assert col.shared.meta.verify_fail(
        key="bad", message="debug", optional=True,
    ).status == "FAIL"
