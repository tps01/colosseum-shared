"""Shared measurement lookup helpers for verify and regex APIs."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from datetime import datetime
from math import isfinite
from pathlib import Path
from typing import TYPE_CHECKING

from colosseum.context import get_context
from colosseum.decorators import VerificationResult

if TYPE_CHECKING:
    from colosseum.database import MeasurementRecord, VerificationRecord

# ASCII digits only. ``"1.0"`` and ``"1e3"`` are not exact integer tokens.
_INTEGER_TEXT = re.compile(r"[+-]?[0-9]+")


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


def _exact_integer(value: object) -> int | None:
    """Return an exact int for an ``int`` or a base-10 integer string.

    Booleans are not integers here. Floats stay on the tolerance path, even
    when they are whole numbers, because a float may already have rounded.
    ``"9007199254740993"`` is exact; ``"1.5"`` and ``"1.0"`` are not.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if _INTEGER_TEXT.fullmatch(text):
            return int(text)
    return None


def _loose_float(value: object) -> float:
    """Convert with ``float``. Booleans go through ``str`` so ``True`` is not ``1``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return float(str(value))
    return float(value)


def _finite_number(value: object) -> float:
    """Return a finite float, or raise ``ValueError`` for non-numeric or non-finite evidence."""
    number = _loose_float(value)
    if not isfinite(number):
        raise ValueError("Bounded measurement must be finite")
    return number


def _tolerance_error(tolerance: object) -> str | None:
    message = f"tolerance must be a finite nonnegative number, got {tolerance!r}"
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)):
        return message
    if isinstance(tolerance, int):
        if tolerance < 0:
            return message
        return None
    if not isfinite(tolerance) or tolerance < 0:
        return message
    return None


def _at_least(actual: object, bound: float) -> bool:
    actual_int = _exact_integer(actual)
    bound_int = _exact_integer(bound)
    if actual_int is not None and bound_int is not None:
        return actual_int >= bound_int
    return _finite_number(actual) >= float(bound)


def _at_most(actual: object, bound: float) -> bool:
    actual_int = _exact_integer(actual)
    bound_int = _exact_integer(bound)
    if actual_int is not None and bound_int is not None:
        return actual_int <= bound_int
    return _finite_number(actual) <= float(bound)


def within_inclusive_bounds(
    actual: object,
    *,
    minimum: float | None,
    maximum: float | None,
) -> tuple[bool, int | float]:
    """Inclusive bounds. Exact ints stay exact; other numbers use finite floats.

    An integer string is exact when that bound is an int. Raises ``ValueError``
    when evidence is non-numeric or non-finite.
    """
    lower_ok = minimum is None or _at_least(actual, minimum)
    upper_ok = maximum is None or _at_most(actual, maximum)
    passed = lower_ok and upper_ok
    exact = _exact_integer(actual)
    if exact is not None:
        return passed, exact
    return passed, _finite_number(actual)


def _result(
    *,
    status: str,
    message: str = "",
    optional: bool,
    actual: object | None = None,
) -> VerificationResult:
    if actual is None:
        return VerificationResult(status=status, message=message, optional=optional)
    return VerificationResult(status=status, message=message, optional=optional, actual=actual)


def _compare_bool(
    *,
    actual: object,
    expected_val: object,
    tolerance: float,
    optional: bool,
) -> VerificationResult:
    _ = tolerance
    if not isinstance(actual, bool):
        return _result(
            status="ERROR",
            message=f"expected Boolean evidence, got {actual!r}",
            optional=optional,
            actual=actual,
        )
    passed = actual is expected_val
    return _result(
        status="PASS" if passed else "FAIL",
        message="" if passed else f"expected {expected_val!r}, got {actual!r}",
        optional=optional,
        actual=actual,
    )


def _compare_exact_int(
    *,
    actual: object,
    expected_val: object,
    tolerance: float,
    optional: bool,
) -> VerificationResult | None:
    actual_int = _exact_integer(actual)
    expected_int = _exact_integer(expected_val)
    if actual_int is None or expected_int is None:
        return None
    if tolerance == 0:
        matched = actual_int == expected_int
    else:
        matched = abs(actual_int - expected_int) <= tolerance
    if matched:
        return _result(status="PASS", optional=optional, actual=actual)
    return _result(
        status="FAIL",
        message=f"expected {expected_int} +/- {tolerance}, got {actual_int}",
        optional=optional,
        actual=actual,
    )


def _compare_float_tol(
    *,
    actual: object,
    expected_val: object,
    tolerance: float,
    optional: bool,
) -> VerificationResult:
    try:
        actual_num = _loose_float(actual)
    except (TypeError, ValueError):
        return _result(
            status="ERROR",
            message=f"cannot compare numeric expected {expected_val!r} to actual {actual!r}",
            optional=optional,
        )
    if not isfinite(actual_num):
        return _result(
            status="ERROR",
            message=f"numeric evidence must be finite, got {actual!r}",
            optional=optional,
            actual=actual,
        )
    expected_num = float(expected_val)  # type: ignore[arg-type]
    if abs(actual_num - expected_num) <= tolerance:
        return _result(status="PASS", optional=optional, actual=actual)
    return _result(
        status="FAIL",
        message=f"expected {expected_num} +/- {tolerance}, got {actual_num}",
        optional=optional,
        actual=actual,
    )


def _compare_numeric(
    *,
    actual: object,
    expected_val: object,
    tolerance: float,
    optional: bool,
) -> VerificationResult:
    tolerance_error = _tolerance_error(tolerance)
    if tolerance_error is not None:
        return _result(
            status="ERROR",
            message=tolerance_error,
            optional=optional,
            actual=actual,
        )
    if not isfinite(expected_val):  # type: ignore[arg-type]
        return _result(
            status="ERROR",
            message=f"numeric expected value must be finite, got {expected_val!r}",
            optional=optional,
            actual=actual,
        )
    exact = _compare_exact_int(
        actual=actual,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )
    if exact is not None:
        return exact
    return _compare_float_tol(
        actual=actual,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


def _compare_string(
    *,
    actual: object,
    expected_val: object,
    tolerance: float,
    optional: bool,
) -> VerificationResult:
    _ = tolerance
    if str(actual) == str(expected_val):
        return _result(status="PASS", optional=optional, actual=actual)
    return _result(
        status="FAIL",
        message=f"expected {expected_val!r}, got {actual!r}",
        optional=optional,
        actual=actual,
    )


_COMPARE_KIND_HANDLERS: tuple[
    tuple[Callable[[object], bool], Callable[..., VerificationResult]],
    ...,
] = (
    (lambda expected: isinstance(expected, bool), _compare_bool),
    (lambda expected: isinstance(expected, (int, float)), _compare_numeric),
)


def compare_expected(
    *,
    actual: object,
    expected_val: object,
    tolerance: float,
    optional: bool,
) -> VerificationResult:
    """Compare evidence to an expectation.

    Booleans are strict (``True`` is not ``1``). When both sides are integers,
    or one side is an integer and the other is an integer string, comparison
    uses exact integer arithmetic. A zero tolerance is equality. Floats and
    non-integer numeric strings (``"1.5"``, ``"1.0"``) use absolute tolerance.
    Any other expectation uses string equality. Non-finite numbers and a
    negative or non-finite tolerance are ERROR.
    """
    for matches, handler in _COMPARE_KIND_HANDLERS:
        if matches(expected_val):
            return handler(
                actual=actual,
                expected_val=expected_val,
                tolerance=tolerance,
                optional=optional,
            )
    return _compare_string(
        actual=actual,
        expected_val=expected_val,
        tolerance=tolerance,
        optional=optional,
    )


def prior_verifications(*, include_optional: bool) -> list[VerificationRecord]:
    rows = get_context().db.fetch_all_verifications()
    if include_optional:
        return rows
    return [row for row in rows if not row.optional]
