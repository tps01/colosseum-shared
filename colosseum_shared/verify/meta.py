"""Meta and intentional marker verifications (``col.shared.verify``)."""

from __future__ import annotations

from colosseum.decorators import VerificationResult, verification
from colosseum.logging import get_logger

from colosseum_shared._evidence import prior_verifications
from colosseum_shared.verify._command import with_verify_command

_logger = get_logger("colosseum.shared")


@verification
@with_verify_command("verify_all_passed")
def verify_all_passed(
    *,
    key: str,
    include_optional: bool = False,
    optional: bool = False,
) -> VerificationResult:
    """Verify every prior verification in this run has PASS status.

    :param key: Verification evidence key.
    :type key: str
    :param include_optional: When ``True``, optional verifications are included in the check.
    :type include_optional: bool, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    rows = prior_verifications(include_optional=include_optional)
    failures = [row for row in rows if row.status != "PASS"]
    _logger.debug(
        "verify_all_passed key=%s checked=%d failures=%d",
        key,
        len(rows),
        len(failures),
    )
    if not failures:
        return VerificationResult(status="PASS", message="", optional=optional)
    first = failures[0]
    return VerificationResult(
        status="FAIL",
        message=(
            f"{len(failures)} prior verification(s) not PASS "
            f"(first: {first.domain}.{first.command} key={first.key!r} status={first.status})"
        ),
        optional=optional,
        actual=len(failures),
    )


@verification
@with_verify_command("verify_m_of_n")
def verify_m_of_n(
    *,
    key: str,
    m: int,
    n: int,
    include_optional: bool = False,
    optional: bool = False,
) -> VerificationResult:
    """Verify at least ``m`` of the last ``n`` prior verifications have PASS status.

    ``m`` and ``n`` must be integers with ``0 < m <= n``. Any other window is
    ERROR and does not consult prior results. Zero required passes is not a
    policy.

    :param key: Verification evidence key.
    :type key: str
    :param m: Minimum number of PASS results required. Integer, ``0 < m <= n``.
    :type m: int
    :param n: Number of most recent prior verifications to consider. Positive integer.
    :type n: int
    :param include_optional: When ``True``, optional verifications are included in the window.
    :type include_optional: bool, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    if (
        isinstance(m, bool)
        or isinstance(n, bool)
        or not isinstance(m, int)
        or not isinstance(n, int)
        or m <= 0
        or n <= 0
        or m > n
    ):
        return VerificationResult(
            status="ERROR",
            message=f"m and n must be integers with 0 < m <= n, got m={m!r} n={n!r}",
            optional=optional,
        )
    rows = prior_verifications(include_optional=include_optional)
    if len(rows) < n:
        return VerificationResult(
            status="ERROR",
            message=f"need at least {n} prior verification(s), found {len(rows)}",
            optional=optional,
        )
    window = rows[-n:]
    passed = sum(1 for row in window if row.status == "PASS")
    _logger.debug("verify_m_of_n key=%s m=%d n=%d passed=%d", key, m, n, passed)
    if passed >= m:
        return VerificationResult(status="PASS", message="", optional=optional, actual=passed)
    return VerificationResult(
        status="FAIL",
        message=f"expected at least {m} of last {n} to PASS, got {passed}",
        optional=optional,
        actual=passed,
    )


@verification
@with_verify_command("verify_pass")
def verify_pass(*, key: str, message: str = "", optional: bool = False) -> VerificationResult:
    """Record an intentional PASS verification marker.

    :param key: Verification evidence key.
    :type key: str
    :param message: Optional note stored in the result message.
    :type message: str, optional
    :param optional: When ``True``, does not fail the run at ``col.endex()`` (always PASS).
    :type optional: bool, optional

    :returns: VerificationResult with PASS status.
    :rtype: VerificationResult
    """
    _ = key
    return VerificationResult(status="PASS", message=message, optional=optional)


@verification
@with_verify_command("verify_fail")
def verify_fail(
    *,
    key: str,
    message: str = "intentional FAIL",
    optional: bool = False,
) -> VerificationResult:
    """Record an intentional FAIL verification marker (scaffolding / debug gates).

    :param key: Verification evidence key.
    :type key: str
    :param message: Failure message.
    :type message: str, optional
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with FAIL status.
    :rtype: VerificationResult
    """
    _ = key
    return VerificationResult(status="FAIL", message=message, optional=optional)
