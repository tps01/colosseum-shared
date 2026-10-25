from __future__ import annotations

import re

from colosseum.decorators import (
    VerificationResult,
    missing_measurement_result,
    verification,
)
from colosseum.logging import get_logger

from colosseum_shared._evidence import latest_measurement_by_key

_logger = get_logger("colosseum.shared")


@verification
def verify_match(
    *,
    key: str,
    pattern: str,
    invert: bool = False,
    optional: bool = False,
) -> VerificationResult:
    """Verify a regex matches text from a prior measurement.

    ``invert=True`` passes when the pattern is absent.

    :param key: Measurement key shared with the source measurement.
    :type key: str
    :param pattern: Regular expression searched in the measured text.
    :type pattern: str
    :param invert: Pass when the pattern does not match.
    :type invert: bool, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    row = latest_measurement_by_key(key)
    if row is None or row.value is None:
        _logger.debug("verify_match key=%s missing measurement", key)
        return missing_measurement_result(key=key, optional=optional)
    actual = str(row.value)
    matched = re.search(pattern, actual) is not None
    passed = (not matched) if invert else matched
    _logger.debug(
        "verify_match key=%s pattern=%r invert=%s matched=%s", key, pattern, invert, matched,
    )
    if passed:
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    if invert:
        message = f"pattern {pattern!r} unexpectedly found in {actual!r}"
    else:
        message = f"pattern {pattern!r} not found in {actual!r}"
    return VerificationResult(
        status="FAIL",
        message=message,
        optional=optional,
        actual=actual,
    )
