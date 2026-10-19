"""Field and existence verifications (``col.shared.verify``)."""

from __future__ import annotations

from math import isfinite

from colosseum.decorators import (
    VerificationResult,
    missing_measurement_result,
    verification,
)
from colosseum.logging import get_logger

from colosseum_shared._evidence import (
    compare_expected,
    extract_field,
    latest_measurement_by_key,
    measurement_exists,
)
from colosseum_shared.verify._command import with_verify_command

_logger = get_logger("colosseum.shared")
_UNSET = object()


@verification
def verify_field(
    *,
    key: str,
    expected_val: object = _UNSET,
    field: str | None = None,
    tolerance: float = 0.0,
    minimum: float | None = None,
    maximum: float | None = None,
    optional: bool = False,
) -> VerificationResult:
    """Verify an expected field value or inclusive numeric bounds.

    :param key: Measurement key shared with a prior measurement in any domain.
    :type key: str
    :param expected_val: Expected value (strict Boolean, numeric with tolerance,
        otherwise string match).
    :type expected_val: object
    :param field: Optional key within a dict/JSON measurement value.
    :type field: str | None, optional
    :param tolerance: Allowed absolute difference for numeric ``expected_val``.
    :type tolerance: float, optional
    :param minimum: Inclusive lower bound, mutually exclusive with expected_val/tolerance.
    :type minimum: float | None, optional
    :param maximum: Inclusive upper bound; may be combined with minimum.
    :type maximum: float | None, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    row = latest_measurement_by_key(key)
    if row is None:
        _logger.debug("verify_field key=%s missing measurement", key)
        return missing_measurement_result(key=key, optional=optional)
    actual, field_error = extract_field(row.value, field)
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
    if minimum is not None or maximum is not None:
        if expected_val is not _UNSET or tolerance != 0.0:
            raise ValueError("Use expected_val/tolerance or minimum/maximum, not both")
        for bound in (minimum, maximum):
            if bound is not None and (isinstance(bound, bool) or not isfinite(bound)):
                raise ValueError("Bounds must be finite numbers")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("minimum must not exceed maximum")
        actual_num = float(str(actual))
        if not isfinite(actual_num):
            raise ValueError("Bounded measurement must be finite")
        passed = (minimum is None or actual_num >= minimum) and (
            maximum is None or actual_num <= maximum
        )
        return VerificationResult(
            status="PASS" if passed else "FAIL",
            message=f"expected minimum={minimum}, maximum={maximum}; got {actual_num}",
            optional=optional,
            actual=actual,
        )
    if expected_val is _UNSET:
        raise ValueError("Supply expected_val or at least one numeric bound")
    return compare_expected(
        actual=actual,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


verify_field = with_verify_command(verify_field, "verify_field")


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
    exists = measurement_exists(key)
    _logger.debug("verify_measurement_exists key=%s exists=%s", key, exists)
    if exists:
        return VerificationResult(status="PASS", message="", optional=optional)
    return missing_measurement_result(key=key, optional=optional)


verify_measurement_exists = with_verify_command(
    verify_measurement_exists,
    "verify_measurement_exists",
)


@verification
def verify_env(
    *,
    key: str,
    expected: str,
    optional: bool = False,
) -> VerificationResult:
    """Verify a prior ``measure_env`` measurement matches ``expected``.

    :param key: Measurement key shared with ``col.shared.measure_env``.
    :type key: str
    :param expected: Expected environment variable value.
    :type expected: str
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    row = latest_measurement_by_key(key)
    if row is None or row.value is None:
        return missing_measurement_result(key=key, optional=optional)
    actual = str(row.value)
    if actual == expected:
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    return VerificationResult(
        status="FAIL",
        message=f"expected env {expected!r}, got {actual!r}",
        optional=optional,
        actual=actual,
    )


verify_env = with_verify_command(verify_env, "verify_env")
