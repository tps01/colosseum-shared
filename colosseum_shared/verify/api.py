from __future__ import annotations

import re
import time
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from colosseum.context import get_context
from colosseum.decorators import (
    VerificationResult,
    missing_measurement_result,
    verification,
)
from colosseum.logging import get_logger

if TYPE_CHECKING:
    from colosseum.database import MeasurementRecord, VerificationRecord

_logger = get_logger("colosseum.shared")


def _latest_measurement_by_key(key: str) -> MeasurementRecord | None:
    """Return the most recent measurement row for ``key`` across all domains."""
    latest: MeasurementRecord | None = None
    for recorded in get_context().db.fetch_all_measurements():
        if recorded.key != key:
            continue
        if latest is None or (recorded.id or 0) > (latest.id or 0):
            latest = recorded
    return latest


def _measurement_exists(key: str) -> bool:
    return any(recorded.key == key for recorded in get_context().db.fetch_all_measurements())


def _resolve_path(path: str) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    ctx = get_context()
    if ctx.output_dir is None:
        return candidate
    return (ctx.output_dir / path).resolve()


def _parse_timestamp(timestamp: str) -> datetime | None:
    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return None


def _extract_field(
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


def _compare_expected(
    *,
    actual: object,
    expected_val: object,
    tolerance: float,
    optional: bool,
) -> VerificationResult:
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


def _prior_verifications(*, include_optional: bool) -> list[VerificationRecord]:
    rows = get_context().db.fetch_all_verifications()
    if include_optional:
        return rows
    return [row for row in rows if not row.optional]


@verification
def verify_field(
    *,
    key: str,
    expected_val: object,
    field: str | None = None,
    tolerance: float = 0.0,
    optional: bool = False,
) -> VerificationResult:
    """Verify a measurement field matches an expected numeric or string value.

    :param key: Measurement key shared with a prior measurement in any domain.
    :type key: str
    :param expected_val: Expected value (numeric with tolerance, otherwise exact string match).
    :type expected_val: object
    :param field: Optional key within a dict/JSON measurement value.
    :type field: str | None, optional
    :param tolerance: Allowed absolute difference for numeric ``expected_val``.
    :type tolerance: float, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    row = _latest_measurement_by_key(key)
    if row is None:
        _logger.debug("verify_field key=%s missing measurement", key)
        return missing_measurement_result(key=key, optional=optional)
    actual, field_error = _extract_field(row.value, field)
    if field_error is not None:
        field_error.optional = optional
        return field_error
    _logger.debug(
        "verify_field key=%s field=%r expected=%r tolerance=%s actual=%r",
        key,
        field,
        expected_val,
        tolerance,
        actual,
    )
    return _compare_expected(
        actual=actual,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


@verification
def verify_measurement_exists(*, key: str, optional: bool = False) -> VerificationResult:
    """Verify a measurement row exists for ``key`` in any domain.

    :param key: Measurement key to look up.
    :type key: str
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    exists = _measurement_exists(key)
    _logger.debug("verify_measurement_exists key=%s exists=%s", key, exists)
    if exists:
        return VerificationResult(status="PASS", message="", optional=optional)
    return missing_measurement_result(key=key, optional=optional)


@verification
def verify_file_exists(
    *,
    key: str,
    path: str | None = None,
    optional: bool = False,
) -> VerificationResult:
    """Verify a file exists on disk, optionally using a prior measurement as the path.

    :param key: Verification evidence key (and measurement key when ``path`` is omitted).
    :type key: str
    :param path: Relative path under the run output directory, or an absolute path.
    :type path: str | None, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    file_path = path
    if file_path is None:
        row = _latest_measurement_by_key(key)
        if row is None or row.value is None:
            _logger.debug("verify_file_exists key=%s missing measurement for path", key)
            return missing_measurement_result(key=key, optional=optional)
        file_path = str(row.value)
    if not file_path:
        return VerificationResult(
            status="ERROR",
            message="no path provided and measurement value is empty",
            optional=optional,
        )
    resolved = _resolve_path(file_path)
    exists = resolved.exists()
    _logger.debug("verify_file_exists key=%s path=%s exists=%s", key, resolved, exists)
    if exists:
        return VerificationResult(
            status="PASS",
            message="",
            optional=optional,
            actual=str(resolved),
        )
    return VerificationResult(
        status="FAIL",
        message=f"file not found: {resolved}",
        optional=optional,
        actual=str(resolved),
    )


@verification
def verify_file_contents(
    *,
    key: str,
    pattern: str,
    path: str | None = None,
    count: int = 1,
    invert: bool = False,
    optional: bool = False,
) -> VerificationResult:
    """PASS when a regex appears in a file at least ``count`` times.

    With ``invert=True``, PASS when the pattern appears fewer than ``count`` times
    (so ``count=1`` means the pattern must be absent).

    :param key: Verification evidence key (and measurement key when ``path`` is omitted).
    :param pattern: Regular expression searched in the file text.
    :param path: Absolute path, or relative to the run output directory. When
        omitted, the latest measurement for ``key`` is used as the path.
    :param count: Required match count threshold (must be >= 1).
    :param invert: Invert the threshold comparison.
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    """
    if count < 1:
        return VerificationResult(
            status="ERROR",
            message=f"count must be >= 1, got {count}",
            optional=optional,
        )
    file_path = path
    if file_path is None:
        row = _latest_measurement_by_key(key)
        if row is None or row.value is None:
            _logger.debug("verify_file_contents key=%s missing measurement for path", key)
            return missing_measurement_result(key=key, optional=optional)
        file_path = str(row.value)
    if not file_path:
        return VerificationResult(
            status="ERROR",
            message="no path provided and measurement value is empty",
            optional=optional,
        )
    resolved = _resolve_path(file_path)
    if not resolved.is_file():
        return VerificationResult(
            status="FAIL",
            message=f"file not found: {resolved}",
            optional=optional,
            actual=str(resolved),
        )
    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        return VerificationResult(
            status="ERROR",
            message=f"could not read {resolved}: {exc}",
            optional=optional,
            actual=str(resolved),
        )
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        return VerificationResult(
            status="ERROR",
            message=f"invalid pattern {pattern!r}: {exc}",
            optional=optional,
        )
    hits = sum(1 for _ in compiled.finditer(text))
    _logger.debug(
        "verify_file_contents key=%s path=%s pattern=%r count=%s invert=%s hits=%s",
        key,
        resolved,
        pattern,
        count,
        invert,
        hits,
    )
    if invert:
        if hits < count:
            return VerificationResult(
                status="PASS",
                message=f"{hits} match(es) < {count}",
                optional=optional,
                actual=hits,
            )
        return VerificationResult(
            status="FAIL",
            message=f"expected fewer than {count} match(es) of {pattern!r}, found {hits}",
            optional=optional,
            actual=hits,
        )
    if hits >= count:
        return VerificationResult(
            status="PASS",
            message=f"{hits} match(es) >= {count}",
            optional=optional,
            actual=hits,
        )
    return VerificationResult(
        status="FAIL",
        message=f"expected at least {count} match(es) of {pattern!r}, found {hits}",
        optional=optional,
        actual=hits,
    )


def snapshot_files(directory: str, *, pattern: str = "*") -> set[str]:
    """Return basenames currently matching ``pattern`` under ``directory``.

    :param directory: Absolute directory, or relative to the run output directory.
    :param pattern: Glob relative to ``directory`` (for example ``*_screenshot.*``).
    """
    root = _resolve_path(directory)
    if not root.is_dir():
        return set()
    return {path.name for path in root.glob(pattern) if path.is_file()}


def wait_for_new_file(
    directory: str,
    *,
    before: set[str] | None = None,
    pattern: str = "*",
    timeout_s: float = 10.0,
    poll_s: float = 0.25,
) -> Path | None:
    """Poll until a new file matching ``pattern`` appears; return its path or ``None``.

    ``before`` is typically ``snapshot_files(...)`` taken before the action under test.
    When omitted, an empty set is used (any matching file counts as new).
    """
    root = _resolve_path(directory)
    seen = set() if before is None else set(before)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if root.is_dir():
            for path in root.glob(pattern):
                if path.is_file() and path.name not in seen:
                    return path
        time.sleep(poll_s)
    return None


@verification
def verify_new_file(
    *,
    key: str,
    directory: str,
    before: set[str] | None = None,
    pattern: str = "*",
    timeout_s: float = 10.0,
    optional: bool = False,
) -> VerificationResult:
    """PASS when a new file matching ``pattern`` appears under ``directory``.

    :param key: Verification evidence key.
    :param directory: Absolute directory, or relative to the run output directory.
    :param before: Basenames from ``snapshot_files`` before the triggering action.
    :param pattern: Glob relative to ``directory``.
    :param timeout_s: How long to wait for a new match.
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.
    """
    _ = key
    found = wait_for_new_file(
        directory,
        before=before,
        pattern=pattern,
        timeout_s=timeout_s,
    )
    if found is not None:
        return VerificationResult(
            status="PASS",
            message=f"new file {found.name}",
            optional=optional,
            actual=str(found),
        )
    return VerificationResult(
        status="FAIL",
        message=f"no new file matching {pattern!r} within {timeout_s:.0f}s",
        optional=optional,
    )


@verification
def verify_no_new_file(
    *,
    key: str,
    directory: str,
    before: set[str] | None = None,
    pattern: str = "*",
    settle_s: float = 2.0,
    optional: bool = False,
) -> VerificationResult:
    """PASS when no new file matching ``pattern`` appears during ``settle_s``.

    :param key: Verification evidence key.
    :param directory: Absolute directory, or relative to the run output directory.
    :param before: Basenames from ``snapshot_files`` before the quiet period.
    :param pattern: Glob relative to ``directory``.
    :param settle_s: How long the directory must stay quiet.
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.
    """
    _ = key
    found = wait_for_new_file(
        directory,
        before=before,
        pattern=pattern,
        timeout_s=settle_s,
    )
    if found is None:
        return VerificationResult(
            status="PASS",
            message=f"quiet for {settle_s:.1f}s",
            optional=optional,
        )
    return VerificationResult(
        status="FAIL",
        message=f"unexpected new file {found.name}",
        optional=optional,
        actual=str(found),
    )


@verification
def verify_time_delta(
    *,
    key: str,
    other_key: str,
    expected_s: float,
    tolerance_s: float = 0.0,
    optional: bool = False,
) -> VerificationResult:
    """Verify the signed time delta between two measurement timestamps.

    Delta is ``timestamp(key) - timestamp(other_key)`` in seconds.

    :param key: Measurement key for the later event.
    :type key: str
    :param other_key: Measurement key for the earlier reference event.
    :type other_key: str
    :param expected_s: Expected delta in seconds.
    :type expected_s: float
    :param tolerance_s: Allowed absolute difference from ``expected_s``.
    :type tolerance_s: float, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    row = _latest_measurement_by_key(key)
    if row is None:
        _logger.debug("verify_time_delta key=%s missing measurement", key)
        return missing_measurement_result(key=key, optional=optional)
    other_row = _latest_measurement_by_key(other_key)
    if other_row is None:
        _logger.debug("verify_time_delta other_key=%s missing measurement", other_key)
        return missing_measurement_result(key=other_key, optional=optional)
    start = _parse_timestamp(other_row.timestamp)
    end = _parse_timestamp(row.timestamp)
    if start is None or end is None:
        return VerificationResult(
            status="ERROR",
            message="could not parse measurement timestamp",
            optional=optional,
        )
    delta_s = (end - start).total_seconds()
    _logger.debug(
        "verify_time_delta key=%s other_key=%s expected=%s +/- %s actual=%s",
        key,
        other_key,
        expected_s,
        tolerance_s,
        delta_s,
    )
    if abs(delta_s - expected_s) <= tolerance_s:
        return VerificationResult(status="PASS", message="", optional=optional, actual=delta_s)
    return VerificationResult(
        status="FAIL",
        message=f"expected delta {expected_s} +/- {tolerance_s} s, got {delta_s} s",
        optional=optional,
        actual=delta_s,
    )


@verification
def verify_all_passed(
    *,
    key: str,
    include_optional: bool = False,
    optional: bool = False,
) -> VerificationResult:
    """Verify every prior verification in this run has PASS status.

    :param key: Verification evidence key.
    :type key: str
    :param include_optional: When ``True``, optional verifications are included in the check.
    :type include_optional: bool, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    rows = _prior_verifications(include_optional=include_optional)
    failures = [row for row in rows if row.status != "PASS"]
    _logger.debug(
        "verify_all_passed key=%s checked=%d failures=%d",
        key,
        len(rows),
        len(failures),
    )
    if not failures:
        return VerificationResult(status="PASS", message="", optional=optional)
    first = failures[0]
    return VerificationResult(
        status="FAIL",
        message=(
            f"{len(failures)} prior verification(s) not PASS "
            f"(first: {first.domain}.{first.command} key={first.key!r} status={first.status})"
        ),
        optional=optional,
        actual=len(failures),
    )


@verification
def verify_m_of_n(
    *,
    key: str,
    m: int,
    n: int,
    include_optional: bool = False,
    optional: bool = False,
) -> VerificationResult:
    """Verify at least ``m`` of the last ``n`` prior verifications have PASS status.

    :param key: Verification evidence key.
    :type key: str
    :param m: Minimum number of PASS results required.
    :type m: int
    :param n: Number of most recent prior verifications to consider.
    :type n: int
    :param include_optional: When ``True``, optional verifications are included in the window.
    :type include_optional: bool, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    rows = _prior_verifications(include_optional=include_optional)
    if len(rows) < n:
        return VerificationResult(
            status="ERROR",
            message=f"need at least {n} prior verification(s), found {len(rows)}",
            optional=optional,
        )
    window = rows[-n:]
    passed = sum(1 for row in window if row.status == "PASS")
    _logger.debug("verify_m_of_n key=%s m=%d n=%d passed=%d", key, m, n, passed)
    if passed >= m:
        return VerificationResult(status="PASS", message="", optional=optional, actual=passed)
    return VerificationResult(
        status="FAIL",
        message=f"expected at least {m} of last {n} to PASS, got {passed}",
        optional=optional,
        actual=passed,
    )
