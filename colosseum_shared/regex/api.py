from __future__ import annotations

import re

from colosseum.context import require_context
from colosseum.decorators import (
    VerificationResult,
    missing_measurement_result,
    verification,
)
from colosseum.logging import get_logger

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
    actual = None
    ctx = require_context()
    for recorded in ctx.db.fetch_all_measurements():
        if recorded.key == key and recorded.value is not None:
            actual = str(recorded.value)
            break
    if actual is None:
        _logger.debug("verify_match key=%s missing measurement", key)
        return missing_measurement_result(key=key, optional=optional)
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
