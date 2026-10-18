"""Time-delta and wall-clock elapsed verifications (``col.shared.verify``)."""

from __future__ import annotations

import time

from colosseum.decorators import (
    VerificationResult,
    missing_measurement_result,
    verification,
)
from colosseum.logging import get_logger

from colosseum_shared._evidence import latest_measurement_by_key, parse_timestamp
from colosseum_shared.verify._command import with_verify_command

_logger = get_logger("colosseum.shared")


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


verify_time_delta = with_verify_command(verify_time_delta, "verify_time_delta")


@verification
def verify_elapsed(
    *,
    key: str,
    mark_key: str,
    maximum_s: float,
    optional: bool = False,
) -> VerificationResult:
    """Verify wall-clock elapsed since a ``measure_mark`` is at most ``maximum_s``.

    Uses ``time.perf_counter()`` values stored by ``col.shared.measure_mark``, not
    database row timestamps (see ``verify_time_delta`` for those). Use a mark
    from the current timing session; imported values from another run or
    machine are not portable elapsed-time evidence.

    :param key: Verification evidence key.
    :type key: str
    :param mark_key: Measurement key from a prior ``measure_mark``.
    :type mark_key: str
    :param maximum_s: Maximum allowed elapsed seconds.
    :type maximum_s: float
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    _ = key
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


verify_elapsed = with_verify_command(verify_elapsed, "verify_elapsed")
