"""U-SH-MEASURE: one-off measure helpers and related verifies."""

from __future__ import annotations

import time
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


@pytest.mark.parametrize(
    ("mark", "maximum_s"),
    [
        (float("inf"), 1.0),
        (float("nan"), 1.0),
        (0.0, float("inf")),
        (0.0, float("nan")),
        (0.0, -1.0),
    ],
)
def test_verify_elapsed_rejects_nonfinite_mark_or_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mark: float,
    maximum_s: float,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    col.shared.measure_value(key="mark", value=mark)
    result = col.shared.verify.verify_elapsed(
        key="elapsed", mark_key="mark", maximum_s=maximum_s,
    )
    assert result.status == "ERROR"
    assert "finite" in result.message or "nonnegative" in result.message


def test_measure_wall_time_delta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    stamp = col.shared.measure_wall_time(key="now")
    assert "T" in stamp
    col.shared.measure_value(key="log_time", value="2020-01-01T00:00:00+00:00")
    col.shared.measure_value(key="bench_time", value="2020-01-01T00:00:02+00:00")
    assert col.shared.verify.verify_wall_time_delta(
        key="bench_time", other_key="log_time", tolerance_s=3,
    ).status == "PASS"
    assert col.shared.verify.verify_wall_time_delta(
        key="bench_time", other_key="log_time", tolerance_s=0,
    ).status == "FAIL"
    assert col.shared.verify.verify_wall_time_delta(
        key="bench_time", expected="2020-01-01T00:00:02+00:00", tolerance_s=0,
    ).status == "PASS"
    assert col.shared.verify.verify_wall_time_delta(
        key="bench_time", tolerance_s=1,
    ).status == "ERROR"
    col.shared.measure_value(key="bad_time", value="not-a-time")
    assert col.shared.verify.verify_wall_time_delta(
        key="bad_time", expected="2020-01-01T00:00:00+00:00", tolerance_s=1,
    ).status == "ERROR"


def test_verify_pass_and_fail_markers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    assert col.shared.verify.verify_pass(key="ok", message="scaffold").status == "PASS"
    assert col.shared.verify.verify_fail(
        key="bad", message="debug", optional=True,
    ).status == "FAIL"
