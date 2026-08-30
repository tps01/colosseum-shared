"""U-SH: shared generic verify helpers."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import colosseum as col
from colosseum.config import load_config
from colosseum.context import get_context
from colosseum.database import MeasurementRow
from colosseum.decorators import VerificationResult, measurement, verification
from colosseum.runner.paths import ensure_runtime_ready

if TYPE_CHECKING:
    import pytest


@measurement
def _record_text(*, key: str, value: str) -> str:
    _ = key
    return value


@measurement
def _record_number(*, key: str, value: float) -> float:
    _ = key
    return value


@measurement
def _record_dict(*, key: str, value: dict[str, float]) -> dict[str, float]:
    _ = key
    return value


@verification
def _fail_verify(*, key: str, optional: bool = False) -> VerificationResult:
    _ = key
    return VerificationResult(status="FAIL", message="forced fail", optional=optional)


@verification
def _pass_verify(*, key: str, optional: bool = False) -> VerificationResult:
    _ = key
    return VerificationResult(status="PASS", message="", optional=optional)


def _load_shared_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "config.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    ensure_runtime_ready(get_context())


def _insert_measurement(
    *,
    key: str,
    timestamp: str,
    value: object = 1,
) -> None:
    get_context().db.insert_measurement(
        MeasurementRow(
            domain="test",
            command="fixture",
            key=key,
            value=value,
            timestamp=timestamp,
        ),
    )


def test_verify_field_string_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _record_text(key="version", value="v1.2.3")
    result = col.shared.verify.verify_field(key="version", expected_val="v1.2.3")
    assert result.status == "PASS"


def test_verify_field_string_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _record_text(key="version", value="v1.2.3")
    result = col.shared.verify.verify_field(key="version", expected_val="v9.9.9")
    assert result.status == "FAIL"


def test_verify_field_numeric_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _record_number(key="count", value=10.0)
    result = col.shared.verify.verify_field(key="count", expected_val=10.0, tolerance=0.5)
    assert result.status == "PASS"


def test_verify_field_numeric_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _record_number(key="count", value=10.0)
    result = col.shared.verify.verify_field(key="count", expected_val=5.0, tolerance=0.1)
    assert result.status == "FAIL"


def test_verify_field_nested_field(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _record_dict(key="summary", value={"max": 80.0, "avg": 40.0})
    result = col.shared.verify.verify_field(
        key="summary",
        field="max",
        expected_val=80.0,
        tolerance=1.0,
    )
    assert result.status == "PASS"


def test_verify_field_missing_measurement(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    result = col.shared.verify.verify_field(key="missing", expected_val=1)
    assert result.status == "ERROR"


def test_verify_field_missing_nested_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _record_dict(key="summary", value={"max": 80.0})
    result = col.shared.verify.verify_field(key="summary", field="min", expected_val=1.0)
    assert result.status == "ERROR"


def test_verify_measurement_exists_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _record_text(key="seen", value="ok")
    result = col.shared.verify.verify_measurement_exists(key="seen")
    assert result.status == "PASS"


def test_verify_measurement_exists_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    result = col.shared.verify.verify_measurement_exists(key="absent")
    assert result.status == "ERROR"


def test_verify_file_exists_with_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    ctx = get_context()
    assert ctx.output_dir is not None
    artifact = ctx.output_dir / "data" / "trace.csv"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("1,2,3", encoding="utf-8")
    result = col.shared.verify.verify_file_exists(key="trace", path="data/trace.csv")
    assert result.status == "PASS"


def test_verify_file_exists_from_measurement_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    ctx = get_context()
    assert ctx.output_dir is not None
    artifact = ctx.output_dir / "profile.json"
    artifact.write_text("{}", encoding="utf-8")
    _record_text(key="profile", value="profile.json")
    result = col.shared.verify.verify_file_exists(key="profile")
    assert result.status == "PASS"


def test_verify_file_exists_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    result = col.shared.verify.verify_file_exists(key="missing", path="no/such/file.txt")
    assert result.status == "FAIL"


def test_verify_time_delta_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _insert_measurement(key="power_on", timestamp="2026-01-01T00:00:00+00:00")
    _insert_measurement(key="ready", timestamp="2026-01-01T00:00:05+00:00")
    result = col.shared.verify.verify_time_delta(
        key="ready",
        other_key="power_on",
        expected_s=5.0,
        tolerance_s=0.5,
    )
    assert result.status == "PASS"


def test_verify_time_delta_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _insert_measurement(key="power_on", timestamp="2026-01-01T00:00:00+00:00")
    _insert_measurement(key="ready", timestamp="2026-01-01T00:00:10+00:00")
    result = col.shared.verify.verify_time_delta(
        key="ready",
        other_key="power_on",
        expected_s=5.0,
        tolerance_s=0.5,
    )
    assert result.status == "FAIL"


def test_verify_all_passed_after_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _pass_verify(key="a")
    _fail_verify(key="b")
    result = col.shared.verify.verify_all_passed(key="summary")
    assert result.status == "FAIL"


def test_verify_all_passed_when_all_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _pass_verify(key="a")
    _pass_verify(key="b")
    result = col.shared.verify.verify_all_passed(key="summary")
    assert result.status == "PASS"


def test_verify_m_of_n_pass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _pass_verify(key="a")
    _fail_verify(key="b")
    _pass_verify(key="c")
    result = col.shared.verify.verify_m_of_n(key="summary", m=2, n=3)
    assert result.status == "PASS"


def test_verify_m_of_n_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _pass_verify(key="a")
    _fail_verify(key="b")
    _fail_verify(key="c")
    result = col.shared.verify.verify_m_of_n(key="summary", m=2, n=3)
    assert result.status == "FAIL"


def test_verify_match_uses_latest_measurement_by_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    _insert_measurement(key="marker", timestamp="2026-01-01T00:00:00+00:00", value="first")
    get_context().db.insert_measurement(
        MeasurementRow(
            domain="other",
            command="fixture",
            key="marker",
            value="second",
            timestamp="2026-01-01T00:00:01+00:00",
        ),
    )
    result = col.shared.regex.verify_match(key="marker", pattern=r"^second$")
    assert result.status == "PASS"
