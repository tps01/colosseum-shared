from __future__ import annotations

import re
from collections.abc import Sequence

from colosseum.context import require_context
from colosseum.decorators import (
    MeasurementSource,
    VerificationResult,
    missing_measurement_result,
    verification,
)


@verification()
def verify_match(
    *,
    key: str,
    pattern: str,
    optional: bool = False,
    sources: Sequence[MeasurementSource] | None = None,
) -> VerificationResult:
    """Verify a regex matches text from a prior measurement.

    :param key: Measurement key shared with the source measurement.
    :type key: str
    :param pattern: Regular expression searched in the measured text.
    :type pattern: str
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional
    :param sources: Optional measurement sources. When omitted, uses the latest
        measurement row with the same ``key``.
    :type sources: Sequence[MeasurementSource] | None, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    actual = None
    ctx = require_context()
    if sources:
        for source in sources:
            source_row = ctx.db.get_measurement(
                source.domain, source.command, key, row_index=0
            )
            if source_row is not None and source_row.value is not None:
                actual = str(source_row.value)
                break
    else:
        for recorded in ctx.db.fetch_all_measurements():
            if recorded.key == key and recorded.value is not None:
                actual = str(recorded.value)
    if actual is None:
        return missing_measurement_result(key=key, optional=optional)
    if re.search(pattern, actual):
        return VerificationResult(status="PASS", message="", optional=optional, actual=actual)
    return VerificationResult(
        status="FAIL",
        message=f"pattern {pattern!r} not found in {actual!r}",
        optional=optional,
        actual=actual,
    )
