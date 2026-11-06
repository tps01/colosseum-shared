"""verify_error_count meta verification."""

from __future__ import annotations

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


def test_verify_error_count_expected_and_bounds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    col.shared.meta.measure_fail(key="e1", optional=True)
    col.shared.meta.measure_fail(key="e2", optional=True)
    col.shared.meta.command_fail(key="c1", optional=True)

    exact = col.shared.verify.verify_error_count(key="err-exact", expected=2)
    assert exact.status == "PASS"
    assert exact.actual == 2

    # command_fail records FAIL, not ERROR — only the two measure_fail ERRORs count.
    too_high = col.shared.verify.verify_error_count(key="err-high", expected=3)
    assert too_high.status == "FAIL"

    within = col.shared.verify.verify_error_count(
        key="err-bounds", minimum=1, maximum=2,
    )
    assert within.status == "PASS"

    below = col.shared.verify.verify_error_count(key="err-min", minimum=5)
    assert below.status == "FAIL"


def test_verify_error_count_include_optional_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    # Force an ERROR verification via invalid verify_m_of_n args (optional so run continues).
    bad = col.shared.verify.verify_m_of_n(key="bad-window", m=0, n=1, optional=True)
    assert bad.status == "ERROR"

    excluded = col.shared.verify.verify_error_count(key="no-opt", expected=0)
    assert excluded.status == "PASS"

    included = col.shared.verify.verify_error_count(
        key="with-opt", expected=1, include_optional=True,
    )
    assert included.status == "PASS"


def test_verify_error_count_rejects_bad_args(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    missing = col.shared.verify.verify_error_count(key="missing")
    assert missing.status == "ERROR"
    both = col.shared.verify.verify_error_count(
        key="both", expected=0, minimum=0,
    )
    assert both.status == "ERROR"
