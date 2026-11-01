"""Intentional pass/fail markers (``col.shared.meta``).

Use these to force evidence outcomes in suites, scaffolding, and debug gates.
Measurements have no FAIL status in core: ``measure_fail`` records ERROR by
raising (unless ``optional=True``).
"""

from __future__ import annotations

from colosseum.decorators import (
    CommandResult,
    VerificationResult,
    command,
    measurement,
    verification,
)
from colosseum.logging import get_logger

_logger = get_logger("colosseum.shared")


@command(dry_run="call")
def command_pass(
    *,
    key: str = "",
    message: str = "",
    optional: bool = False,
) -> CommandResult:
    """Record an intentional PASS command.

    :param key: Optional command evidence key.
    :type key: str, optional
    :param message: Optional note stored with the result.
    :type message: str, optional
    :param optional: When ``True``, does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: CommandResult with PASS status.
    :rtype: CommandResult
    """
    _logger.debug("meta.command_pass key=%s", key)
    return CommandResult(status="PASS", message=message, optional=optional)


@command
def command_fail(
    *,
    key: str = "",
    message: str = "intentional FAIL",
    optional: bool = False,
) -> CommandResult:
    """Record an intentional FAIL command.

    :param key: Optional command evidence key.
    :type key: str, optional
    :param message: Failure message.
    :type message: str, optional
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: CommandResult with FAIL status.
    :rtype: CommandResult
    """
    _logger.debug("meta.command_fail key=%s", key)
    return CommandResult(status="FAIL", message=message, optional=optional)


@measurement(dry_run="call")
def measure_pass(*, key: str, value: object = True) -> object:
    """Record an intentional PASS measurement.

    :param key: Unique measurement key within domain ``shared``.
    :type key: str
    :param value: Value to store (default ``True``).
    :type value: object, optional

    :returns: The same ``value``.
    :rtype: object
    """
    _logger.debug("meta.measure_pass key=%s type=%s", key, type(value).__name__)
    return value


@measurement
def measure_fail(
    *,
    key: str,
    message: str = "intentional measurement FAIL",
    optional: bool = False,
) -> None:
    """Force a measurement ERROR (core has no measurement FAIL status).

    Raises ``RuntimeError`` so the measurement decorator records ERROR. With
    ``optional=True``, the error is recorded and the exception is suppressed.

    :param key: Unique measurement key within domain ``shared``.
    :type key: str
    :param message: Error message.
    :type message: str, optional
    :param optional: When ``True``, ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: ``None`` when ``optional=True``; otherwise raises.
    :rtype: None

    :raises RuntimeError: Always, unless ``optional=True`` (then still raised
        internally and swallowed by the measurement decorator).
    """
    _logger.debug("meta.measure_fail key=%s optional=%s", key, optional)
    raise RuntimeError(message)


@verification(dry_run="call")
def verify_pass(*, key: str, message: str = "", optional: bool = False) -> VerificationResult:
    """Record an intentional PASS verification.

    :param key: Verification evidence key.
    :type key: str
    :param message: Optional note stored in the result message.
    :type message: str, optional
    :param optional: When ``True``, does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS status.
    :rtype: VerificationResult
    """
    _logger.debug("meta.verify_pass key=%s", key)
    return VerificationResult(status="PASS", message=message, optional=optional)


@verification
def verify_fail(
    *,
    key: str,
    message: str = "intentional FAIL",
    optional: bool = False,
) -> VerificationResult:
    """Record an intentional FAIL verification.

    :param key: Verification evidence key.
    :type key: str
    :param message: Failure message.
    :type message: str, optional
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with FAIL status.
    :rtype: VerificationResult
    """
    _logger.debug("meta.verify_fail key=%s", key)
    return VerificationResult(status="FAIL", message=message, optional=optional)
