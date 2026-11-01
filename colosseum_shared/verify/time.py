"""Wall-time and monotonic elapsed verifications (``col.shared.verify``)."""

from __future__ import annotations

import time
from math import isfinite
from typing import TYPE_CHECKING

from colosseum.decorators import (
    VerificationResult,
    missing_measurement_result,
    verification,
)
from colosseum.logging import get_logger

from colosseum_shared._evidence import latest_measurement_by_key, parse_timestamp
from colosseum_shared.verify._command import with_verify_command

if TYPE_CHECKING:
    from datetime import datetime

_logger = get_logger("colosseum.shared")


@verification
@with_verify_command("verify_time_delta")
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
    :param tolerance_s: Finite and nonnegative absolute difference from ``expected_s``.
    :type tolerance_s: float, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    if not isfinite(tolerance_s) or tolerance_s < 0:
        return VerificationResult(
            status="ERROR",
            message=f"tolerance_s must be finite and nonnegative, got {tolerance_s!r}",
            optional=optional,
        )
    row = latest_measurement_by_key(key)
    if row is None:
        _logger.debug("verify_time_delta key=%s missing measurement", key)
        return missing_measurement_result(key=key, optional=optional)
    other_row = latest_measurement_by_key(other_key)
    if other_row is None:
        _logger.debug("verify_time_delta other_key=%s missing measurement", other_key)
        return missing_measurement_result(key=other_key, optional=optional)
    start = parse_timestamp(other_row.timestamp)
    end = parse_timestamp(row.timestamp)
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
@with_verify_command("verify_elapsed")
def verify_elapsed(
    *,
    key: str,
    mark_key: str,
    maximum_s: float,
    optional: bool = False,
) -> VerificationResult:
    """Verify monotonic elapsed time since a ``measure_mark`` is at most ``maximum_s``.

    Uses ``time.perf_counter()`` values stored by ``col.shared.measure_mark``.
    This clock does not move backward when the wall clock is stepped, and the
    stored mark is meaningless in another run or on another machine. Database
    row timestamps are a different clock; use ``verify_time_delta`` for those.
    Use ``measure_wall_time`` and ``verify_wall_time_delta`` to compare UTC
    readings, including a timestamp copied from a product log.

    The stored mark must be finite. ``maximum_s`` must be finite and nonnegative;
    zero is allowed. A non-finite mark or limit is ERROR and is not compared.

    :param key: Verification evidence key.
    :type key: str
    :param mark_key: Measurement key from a prior ``measure_mark``.
    :type mark_key: str
    :param maximum_s: Maximum allowed elapsed seconds. Finite and nonnegative.
    :type maximum_s: float
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    _ = key
    if not isfinite(maximum_s) or maximum_s < 0:
        return VerificationResult(
            status="ERROR",
            message=f"maximum_s must be finite and nonnegative, got {maximum_s!r}",
            optional=optional,
        )
    row = latest_measurement_by_key(mark_key)
    if row is None or row.value is None:
        return missing_measurement_result(key=mark_key, optional=optional)
    try:
        mark = float(str(row.value))
    except (TypeError, ValueError):
        return VerificationResult(
            status="ERROR",
            message=f"mark measurement {mark_key!r} is not numeric",
            optional=optional,
            actual=row.value,
        )
    if not isfinite(mark):
        return VerificationResult(
            status="ERROR",
            message=f"mark measurement {mark_key!r} must be finite, got {mark!r}",
            optional=optional,
            actual=row.value,
        )
    elapsed = time.perf_counter() - mark
    _logger.debug(
        "verify_elapsed mark_key=%s maximum_s=%s elapsed=%s",
        mark_key,
        maximum_s,
        elapsed,
    )
    if elapsed <= maximum_s:
        return VerificationResult(status="PASS", message="", optional=optional, actual=elapsed)
    return VerificationResult(
        status="FAIL",
        message=f"expected elapsed <= {maximum_s} s, got {elapsed} s",
        optional=optional,
        actual=elapsed,
    )


def _wall_instant(
    *,
    key: str,
    literal: str | None,
    optional: bool,
) -> tuple[datetime | None, VerificationResult | None]:
    """Return a parsed UTC instant from a measurement value or a literal string."""
    if literal is not None:
        parsed = parse_timestamp(literal)
        if parsed is None:
            return None, VerificationResult(
                status="ERROR",
                message=f"could not parse wall time {literal!r}",
                optional=optional,
            )
        return parsed, None
    row = latest_measurement_by_key(key)
    if row is None or row.value is None:
        return None, missing_measurement_result(key=key, optional=optional)
    text = str(row.value)
    parsed = parse_timestamp(text)
    if parsed is None:
        return None, VerificationResult(
            status="ERROR",
            message=f"could not parse wall time {text!r}",
            optional=optional,
            actual=row.value,
        )
    return parsed, None


@verification
@with_verify_command("verify_wall_time_delta")
def verify_wall_time_delta(
    *,
    key: str,
    other_key: str | None = None,
    expected: str | None = None,
    tolerance_s: float = 0.0,
    optional: bool = False,
) -> VerificationResult:
    """Verify the signed difference between two UTC wall-time readings.

    Delta is the ``key`` value minus the other instant, in seconds. The other
    instant is ``other_key``'s measurement value or the literal ``expected``
    string, and exactly one of those must be set. Values are ISO-8601 strings
    from ``measure_wall_time`` or from a product log. This is not a monotonic
    budget; use ``verify_elapsed`` for that. An unparseable string is ERROR.

    :param key: Measurement key whose value is the later (or left-hand) instant.
    :type key: str
    :param other_key: Measurement key whose value is the reference instant.
    :type other_key: str | None, optional
    :param expected: Literal ISO-8601 reference instant.
    :type expected: str | None, optional
    :param tolerance_s: Allowed absolute difference from zero. Finite and nonnegative.
    :type tolerance_s: float, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    if (other_key is None) == (expected is None):
        return VerificationResult(
            status="ERROR",
            message="supply exactly one of other_key or expected",
            optional=optional,
        )
    if not isfinite(tolerance_s) or tolerance_s < 0:
        return VerificationResult(
            status="ERROR",
            message=f"tolerance_s must be finite and nonnegative, got {tolerance_s!r}",
            optional=optional,
        )
    end, end_error = _wall_instant(key=key, literal=None, optional=optional)
    if end_error is not None or end is None:
        return end_error or VerificationResult(
            status="ERROR", message="missing wall time", optional=optional,
        )
    start, start_error = _wall_instant(
        key=other_key or "",
        literal=expected,
        optional=optional,
    )
    if start_error is not None or start is None:
        return start_error or VerificationResult(
            status="ERROR", message="missing wall time", optional=optional,
        )
    delta_s = (end - start).total_seconds()
    _logger.debug(
        "verify_wall_time_delta key=%s other_key=%s expected=%s tolerance=%s actual=%s",
        key,
        other_key,
        expected,
        tolerance_s,
        delta_s,
    )
    if abs(delta_s) <= tolerance_s:
        return VerificationResult(status="PASS", message="", optional=optional, actual=delta_s)
    return VerificationResult(
        status="FAIL",
        message=f"expected wall-time delta within +/- {tolerance_s} s, got {delta_s} s",
        optional=optional,
        actual=delta_s,
    )
