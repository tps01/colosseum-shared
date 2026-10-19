"""U-SH: shared generic verify helpers."""

from __future__ import annotations

from pathlib import Path

import colosseum as col
import pytest
from colosseum.config import load_config
from colosseum.context import get_context
from colosseum.database import MeasurementRow
from colosseum.decorators import VerificationResult, measurement, verification
from colosseum.runner.paths import ensure_runtime_ready


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


def test_verify_file_contents_count_and_invert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    ctx = get_context()
    assert ctx.output_dir is not None
    log = ctx.output_dir / "uut.log"
    log.write_text("INFO ok\nERROR a\nERROR b\nINFO done\n", encoding="utf-8")

    assert col.shared.verify.verify_file_contents(
        key="errors", path="uut.log", pattern=r"ERROR", count=2,
    ).status == "PASS"
    assert col.shared.verify.verify_file_contents(
        key="errors_low", path="uut.log", pattern=r"ERROR", count=3,
    ).status == "FAIL"
    assert col.shared.verify.verify_file_contents(
        key="no_fatal", path="uut.log", pattern=r"FATAL", invert=True,
    ).status == "PASS"
    assert col.shared.verify.verify_file_contents(
        key="few_errors", path="uut.log", pattern=r"ERROR", count=3, invert=True,
    ).status == "PASS"
    assert col.shared.verify.verify_file_contents(
        key="too_many", path="uut.log", pattern=r"ERROR", count=2, invert=True,
    ).status == "FAIL"


def test_verify_file_contents_from_measurement_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    ctx = get_context()
    assert ctx.output_dir is not None
    (ctx.output_dir / "note.txt").write_text("alpha beta alpha\n", encoding="utf-8")
    _record_text(key="note", value="note.txt")
    result = col.shared.verify.verify_file_contents(
        key="note", pattern=r"alpha", count=2,
    )
    assert result.status == "PASS"


def test_verify_new_file_and_no_new_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    ctx = get_context()
    assert ctx.output_dir is not None
    captures = ctx.output_dir / "captures"
    captures.mkdir(parents=True, exist_ok=True)
    (captures / "old_screenshot.jpg").write_bytes(b"x")
    before = col.shared.verify.snapshot_files("captures", pattern="*_screenshot.*")
    assert "old_screenshot.jpg" in before

    quiet = col.shared.verify.verify_no_new_file(
        key="quiet",
        directory="captures",
        before=before,
        pattern="*_screenshot.*",
        settle_s=0.3,
    )
    assert quiet.status == "PASS"

    (captures / "new_screenshot.jpg").write_bytes(b"y")
    appeared = col.shared.verify.verify_new_file(
        key="shot",
        directory="captures",
        before=before,
        pattern="*_screenshot.*",
        timeout_s=1.0,
    )
    assert appeared.status == "PASS"


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


@pytest.mark.parametrize(
    "actual,limits,status",
    [
        (2.0, {"maximum": 5.0}, "PASS"),
        (5.0, {"maximum": 5.0}, "PASS"),
        (8.0, {"maximum": 5.0}, "FAIL"),
        (2.0, {"minimum": 5.0}, "FAIL"),
        (5.0, {"minimum": 5.0}, "PASS"),
        (8.0, {"minimum": 5.0}, "PASS"),
        (-60.0, {"maximum": -40.0}, "PASS"),
        (-20.0, {"maximum": -40.0}, "FAIL"),
        (-6.0, {"minimum": -5.0, "maximum": 5.0}, "FAIL"),
        (-5.0, {"minimum": -5.0, "maximum": 5.0}, "PASS"),
        (0.0, {"minimum": -5.0, "maximum": 5.0}, "PASS"),
        (5.0, {"minimum": -5.0, "maximum": 5.0}, "PASS"),
        (6.0, {"minimum": -5.0, "maximum": 5.0}, "FAIL"),
        (float("nan"), {"maximum": 5.0}, "ERROR"),
        (float("inf"), {"minimum": 5.0}, "ERROR"),
        (2.0, {"minimum": 5.0, "maximum": 1.0}, "ERROR"),
        (2.0, {"minimum": float("nan")}, "ERROR"),
        (2.0, {"maximum": float("inf")}, "ERROR"),
        (2.0, {"minimum": True}, "ERROR"),
        (2.0, {"minimum": 1.0, "expected_val": 2.0}, "ERROR"),
        (2.0, {"maximum": 5.0, "tolerance": 1.0}, "ERROR"),
        (2.0, {}, "ERROR"),
        ("not a number", {"maximum": 5.0}, "ERROR"),
        (None, {"expected_val": None}, "PASS"),
    ],
)
def test_verify_field_bounds(tmp_path, monkeypatch, actual, limits, status):
    _load_shared_config(tmp_path, monkeypatch)
    col.shared.measure_value(key="bounded", value={"value": actual})
    result = col.shared.verify.verify_field(key="bounded", field="value", **limits)
    assert result.status == status


def test_verify_field_optional_bound_failure_is_retained(tmp_path, monkeypatch):
    _load_shared_config(tmp_path, monkeypatch)
    col.shared.measure_value(key="bounded", value=8.0)
    result = col.shared.verify.verify_field(key="bounded", maximum=5.0, optional=True)
    assert result.status == "FAIL"
    assert result.optional is True
    assert get_context().db.fetch_all_verifications()[-1].optional is True


def test_verify_field_bounds_from_parameters(tmp_path, monkeypatch):
    _load_shared_config(tmp_path, monkeypatch)
    col.shared.measure_value(key="bounded", value=5.0)
    get_context().parameters_map = {"bounded": {"minimum": 0.0, "maximum": 5.0}}
    assert col.shared.verify.verify_field(key="bounded").status == "PASS"


@pytest.mark.parametrize(
    "actual,expected,status",
    [
        (True, True, "PASS"),
        (False, False, "PASS"),
        (True, False, "FAIL"),
        (False, True, "FAIL"),
        (1, True, "ERROR"),
        (0, False, "ERROR"),
        ("True", True, "ERROR"),
        ("False", False, "ERROR"),
    ],
)
def test_verify_field_boolean(tmp_path, monkeypatch, actual, expected, status):
    _load_shared_config(tmp_path, monkeypatch)
    col.shared.measure_value(key="pin", value={"level": actual})
    result = col.shared.verify.verify_field(key="pin", field="level", expected_val=expected)
    assert result.status == status
    assert result.actual == actual
