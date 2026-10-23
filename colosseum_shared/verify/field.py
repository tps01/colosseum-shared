"""Field and existence verifications (``col.shared.verify``)."""

from __future__ import annotations

from math import isfinite
from typing import TYPE_CHECKING

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
    within_inclusive_bounds,
)
from colosseum_shared.verify._command import with_verify_command

if TYPE_CHECKING:
    from collections.abc import Sequence

_logger = get_logger("colosseum.shared")
_UNSET = object()


@verification
@with_verify_command("verify_field")
def verify_field(
    *,
    key: str,
    expected_val: object = _UNSET,
    field: str | None = None,
    tolerance: float = 0.0,
    tolerance_pct: float | None = None,
    minimum: float | None = None,
    maximum: float | None = None,
    optional: bool = False,
) -> VerificationResult:
    """Verify an expected field value or inclusive numeric bounds.

    Integer evidence compared with an integer expectation or limit uses exact
    arithmetic, including an integer string such as ``"9007199254740993"``.
    Floats and non-integer numeric strings keep absolute tolerance. Numeric
    comparisons require finite evidence, a finite expectation, and a finite
    nonnegative tolerance.

    :param key: Measurement key shared with a prior measurement in any domain.
    :type key: str
    :param expected_val: Expected value (strict Boolean, numeric with tolerance,
        otherwise string match).
    :type expected_val: object
    :param field: Optional key within a dict/JSON measurement value.
    :type field: str | None, optional
    :param tolerance: Finite nonnegative absolute difference for numeric ``expected_val``.
        Zero tolerance is exact equality for integers. Do not combine with ``tolerance_pct``.
    :type tolerance: float, optional
    :param tolerance_pct: Percent of ``expected_val`` allowed as absolute difference.
        ``10`` means 10 percent. Zero expected value allows only an exact match.
        Do not combine with ``tolerance`` or with bounds.
    :type tolerance_pct: float | None, optional
    :param minimum: Inclusive lower bound, mutually exclusive with expected_val/tolerance.
        Integers compare exactly.
    :type minimum: float | None, optional
    :param maximum: Inclusive upper bound; may be combined with minimum.
        Integers compare exactly.
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
        if expected_val is not _UNSET or tolerance != 0.0 or tolerance_pct is not None:
            raise ValueError("Use expected_val/tolerance or minimum/maximum, not both")
        for bound in (minimum, maximum):
            if bound is not None and (isinstance(bound, bool) or not isfinite(bound)):
                raise ValueError("Bounds must be finite numbers")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("minimum must not exceed maximum")
        passed, shown = within_inclusive_bounds(
            actual,
            minimum=minimum,
            maximum=maximum,
        )
        return VerificationResult(
            status="PASS" if passed else "FAIL",
            message=f"expected minimum={minimum}, maximum={maximum}; got {shown}",
            optional=optional,
            actual=actual,
        )
    if expected_val is _UNSET:
        raise ValueError("Supply expected_val or at least one numeric bound")
    if tolerance_pct is not None:
        if tolerance != 0.0:
            raise ValueError("Use tolerance or tolerance_pct, not both")
        if (
            isinstance(tolerance_pct, bool)
            or not isinstance(tolerance_pct, (int, float))
            or not isfinite(tolerance_pct)
            or tolerance_pct < 0
        ):
            raise ValueError(
                f"tolerance_pct must be a finite nonnegative number, got {tolerance_pct!r}",
            )
        if (
            isinstance(expected_val, bool)
            or not isinstance(expected_val, (int, float))
            or not isfinite(expected_val)
        ):
            raise ValueError("tolerance_pct requires a finite numeric expected_val")
        tolerance = abs(float(expected_val)) * float(tolerance_pct) / 100.0
    return compare_expected(
        actual=actual,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


@verification
@with_verify_command("verify_measurement_exists")
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


@verification
@with_verify_command("verify_env")
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


@verification
@with_verify_command("verify_equal")
def verify_equal(
    *,
    key: str,
    other_key: str,
    optional: bool = False,
) -> VerificationResult:
    """Verify two measurement values match.

    Comparison follows ``verify_field``: exact integers, absolute tolerance of
    zero for other numbers, and string equality otherwise.

    :param key: Measurement key for the value under test.
    :type key: str
    :param other_key: Measurement key for the expected value.
    :type other_key: str
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    row = latest_measurement_by_key(key)
    if row is None or row.value is None:
        return missing_measurement_result(key=key, optional=optional)
    other = latest_measurement_by_key(other_key)
    if other is None or other.value is None:
        return missing_measurement_result(key=other_key, optional=optional)
    return compare_expected(
        actual=row.value,
        expected_val=other.value,
        tolerance=0,
        optional=optional,
    )


@verification
@with_verify_command("verify_in")
def verify_in(
    *,
    key: str,
    choices: Sequence[object],
    optional: bool = False,
) -> VerificationResult:
    """Verify a measurement value matches one entry in ``choices``.

    :param key: Measurement key for the value under test.
    :type key: str
    :param choices: Allowed values. A bare string is not a sequence of choices.
    :type choices: Sequence[object]
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    if isinstance(choices, (str, bytes)) or len(choices) == 0:
        return VerificationResult(
            status="ERROR",
            message="choices must be a non-empty sequence of allowed values",
            optional=optional,
        )
    row = latest_measurement_by_key(key)
    if row is None or row.value is None:
        return missing_measurement_result(key=key, optional=optional)
    first_error: VerificationResult | None = None
    saw_fail = False
    for choice in choices:
        result = compare_expected(
            actual=row.value,
            expected_val=choice,
            tolerance=0,
            optional=optional,
        )
        if result.status == "PASS":
            return result
        if result.status == "ERROR":
            if first_error is None:
                first_error = result
        else:
            saw_fail = True
    if saw_fail or first_error is None:
        return VerificationResult(
            status="FAIL",
            message=f"expected one of {list(choices)!r}, got {row.value!r}",
            optional=optional,
            actual=row.value,
        )
    return first_error
