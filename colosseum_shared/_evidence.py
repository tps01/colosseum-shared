"""Shared measurement lookup helpers for verify and regex APIs."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from colosseum.context import get_context
from colosseum.decorators import VerificationResult

if TYPE_CHECKING:
    from colosseum.database import MeasurementRecord, VerificationRecord


def latest_measurement_by_key(key: str) -> MeasurementRecord | None:
    """Return the most recent measurement row for ``key`` across all domains."""
    latest: MeasurementRecord | None = None
    for recorded in get_context().db.fetch_all_measurements():
        if recorded.key != key:
            continue
        if latest is None or (recorded.id or 0) > (latest.id or 0):
            latest = recorded
    return latest


def measurement_exists(key: str) -> bool:
    return any(recorded.key == key for recorded in get_context().db.fetch_all_measurements())


def resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    ctx = get_context()
    if ctx.output_dir is None:
        return candidate
    return (ctx.output_dir / path).resolve()


def parse_timestamp(timestamp: str) -> datetime | None:
    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None


def extract_field(
    value: object, field: str | None,
) -> tuple[object | None, VerificationResult | None]:
    if field is None:
        return value, None
    if not isinstance(value, Mapping):
        return None, VerificationResult(
            status="ERROR",
            message=f"measurement value is not a mapping; cannot read field={field!r}",
        )
    if field not in value:
        return None, VerificationResult(
            status="ERROR",
            message=f"field {field!r} not found in measurement value",
        )
    return value[field], None


def compare_expected(
    *,
    actual: object,
    expected_val: object,
    tolerance: float,
    optional: bool,
) -> VerificationResult:
    if isinstance(expected_val, bool):
        if not isinstance(actual, bool):
            return VerificationResult(
                status="ERROR",
                message=f"expected Boolean evidence, got {actual!r}",
                optional=optional,
                actual=actual,
            )
        passed = actual is expected_val
        return VerificationResult(
            status="PASS" if passed else "FAIL",
            message="" if passed else f"expected {expected_val!r}, got {actual!r}",
            optional=optional,
            actual=actual,
        )
    if isinstance(expected_val, (int, float)):
        try:
            actual_num = float(str(actual))
        except (TypeError, ValueError):
            return VerificationResult(
                status="ERROR",
                message=f"cannot compare numeric expected {expected_val!r} to actual {actual!r}",
                optional=optional,
            )
        expected_num = float(expected_val)
        if abs(actual_num - expected_num) <= tolerance:
            return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
        return VerificationResult(
            status="FAIL",
            message=f"expected {expected_num} +/- {tolerance}, got {actual_num}",
            optional=optional,
            actual=actual,
        )
    if str(actual) == str(expected_val):
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    return VerificationResult(
        status="FAIL",
        message=f"expected {expected_val!r}, got {actual!r}",
        optional=optional,
        actual=actual,
    )


def prior_verifications(*, include_optional: bool) -> list[VerificationRecord]:
    rows = get_context().db.fetch_all_verifications()
    if include_optional:
        return rows
    return [row for row in rows if not row.optional]
