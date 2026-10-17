"""Field and existence verifications (``col.shared.verify``)."""

from __future__ import annotations

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
