from __future__ import annotations

import re

from colosseum.decorators import (
    VerificationResult,
    missing_measurement_result,
    verification,
)
from colosseum.logging import get_logger

from colosseum_shared.verify.api import _latest_measurement_by_key

_logger = get_logger("colosseum.shared")


@verification
def verify_match(
    *,
    key: str,
    pattern: str,
    optional: bool = False,
) -> VerificationResult:
    """Verify a regex matches text from a prior measurement.

    :param key: Measurement key shared with the source measurement.
    :type key: str
    :param pattern: Regular expression searched in the measured text.
    :type pattern: str
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    row = _latest_measurement_by_key(key)
    if row is None or row.value is None:
        _logger.debug("verify_match key=%s missing measurement", key)
        return missing_measurement_result(key=key, optional=optional)
    actual = str(row.value)
    matched = re.search(pattern, actual) is not None
    _logger.debug("verify_match key=%s pattern=%r matched=%s", key, pattern, matched)
    if matched:
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    return VerificationResult(
        status="FAIL",
        message=f"pattern {pattern!r} not found in {actual!r}",
        optional=optional,
        actual=actual,
    )
