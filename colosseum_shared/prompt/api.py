"""Operator prompts and manual test annotations (``col.shared.prompt``)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, cast

from colosseum.context import get_context
from colosseum.database import CommandRow
from colosseum.decorators import (
    CommandResult,
    VerificationResult,
    command,
    measurement,
    verification,
)
from colosseum.logging import get_logger
from colosseum.results import endex
from colosseum.runner.paths import ensure_runtime_ready

from colosseum_shared.prompt._stdin import read_line, wait_any_key

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

_F = TypeVar("_F")

_logger = get_logger("colosseum.shared")


def _fail_and_exit(*, message: str, key: str, command: str) -> None:
    ctx = get_context()
    ensure_runtime_ready(ctx)
    result = CommandResult(status="FAIL", message=message)
    ctx.db.insert_command(
        CommandRow(
            domain="shared",
            command=command,
            key=key,
            result=None,
            status="FAIL",
            optional=False,
            message=message,
        ),
    )
    ctx.result_aggregator.record_command(
        result,
        key=key,
        command=command,
        domain="shared",
    )
    _logger.info("command shared.%s key=%s status=FAIL", command, key)
    endex()


_PROMPT_EXIT_COMMAND = "prompt.prompt_exit"


class PromptTimeoutError(TimeoutError):
    """The operator did not answer before ``timeout_s``."""


def _mark_command(name: str) -> Callable[[_F], _F]:
    def decorate(func: _F) -> _F:
        target = cast("Any", func)
        target.__colosseum_command__ = name
        return func

    return decorate


@command
def prompt(*, message: str, timeout_s: float | None = None) -> CommandResult | None:
    """Display a message and block until the operator presses any key.

    ``timeout_s`` limits the wait. On timeout the command is recorded as ERROR
    and this function returns. The run is not ended here.

    :param message: Text shown on stdout before waiting for input.
    :type message: str
    :param timeout_s: Maximum wait in seconds. Omit to wait without a limit.
    :type timeout_s: float | None, optional

    :returns: ``None`` when a key arrives. A ``CommandResult`` with status ERROR on timeout.
    """
    _logger.info("%s", message)
    if timeout_s is None:
        wait_any_key(message=message)
        return None
    if wait_any_key(message=message, timeout_s=timeout_s):
        return None
    return CommandResult(
        status="ERROR",
        message=f"no key within {timeout_s} s",
    )


@measurement
@_mark_command("prompt.prompt_measurement")
def _prompt_measurement_record(
    *, message: str, key: str, timeout_s: float | None = None,
) -> str:
    line = read_line(message=message) if timeout_s is None else read_line(
        message=message, timeout_s=timeout_s,
    )
    if line is None:
        raise PromptTimeoutError(f"no input within {timeout_s} s")
    _logger.info("prompt_measurement key=%s", key)
    return line


def prompt_measurement(
    *, message: str, key: str, timeout_s: float | None = None,
) -> str | None:
    """Prompt for a line of operator input and store it as a measurement.

    On timeout the measurement is recorded as ERROR and this function returns
    ``None``. An empty line is ``""``, not a timeout.

    :param message: Prompt text shown before reading stdin.
    :type message: str
    :param key: Unique measurement key for this run.
    :type key: str
    :param timeout_s: Maximum wait in seconds. Omit to wait without a limit.
    :type timeout_s: float | None, optional

    :returns: The operator's input line, or ``None`` on timeout.
    :rtype: str | None
    """
    try:
        return _prompt_measurement_record(message=message, key=key, timeout_s=timeout_s)
    except PromptTimeoutError:
        return None


@verification
def prompt_choice(
    *,
    message: str,
    key: str,
    choices: Sequence[str],
    timeout_s: float | None = None,
    optional: bool = False,
) -> VerificationResult:
    """Ask the operator to enter one of ``choices`` and record the answer.

    The line is stored as a measurement. A value outside ``choices`` is FAIL and
    the procedure continues. Timeout is ERROR. This does not end the run; use
    ``prompt_exit`` for a gate that stops on a mismatch.

    :param message: Prompt text shown before reading stdin.
    :type message: str
    :param key: Measurement key for the entered line.
    :type key: str
    :param choices: Allowed lines. Matching is exact.
    :type choices: Sequence[str]
    :param timeout_s: Maximum wait in seconds. Omit to wait without a limit.
    :type timeout_s: float | None, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    if isinstance(choices, str) or len(choices) == 0:
        return VerificationResult(
            status="ERROR",
            message="choices must be a non-empty sequence of allowed lines",
            optional=optional,
        )
    entered = prompt_measurement(message=message, key=key, timeout_s=timeout_s)
    if entered is None:
        return VerificationResult(
            status="ERROR",
            message=f"no input within {timeout_s} s",
            optional=optional,
        )
    if entered in choices:
        return VerificationResult(status="PASS", message="", optional=optional, actual=entered)
    return VerificationResult(
        status="FAIL",
        message=f"expected one of {list(choices)!r}, got {entered!r}",
        optional=optional,
        actual=entered,
    )


@command
def comment(*, message: str) -> None:
    """Log a test annotation at INFO on the run console and in ``debug.log``.

    :param message: Text written at INFO.
    :type message: str

    :returns: None
    """
    _logger.info("%s", message)


@command
def prompt_exit(
    *, message: str, key: str, expected: str, timeout_s: float | None = None,
) -> CommandResult | None:
    """Prompt for input, record it, and exit the run immediately on mismatch.

    The entered value is stored as a measurement under ``key``. When it does not
    exactly match ``expected``, the run is marked FAIL and ``col.endex()`` is
    invoked (the process exits without returning to the caller). Timeout records
    ERROR and returns; it does not call ``endex()``.

    :param message: Prompt text shown before reading stdin.
    :type message: str
    :param key: Measurement key for the operator input.
    :type key: str
    :param expected: Required exact match for the entered line.
    :type expected: str
    :param timeout_s: Maximum wait in seconds. Omit to wait without a limit.
    :type timeout_s: float | None, optional

    :returns: ``None`` when the input matches ``expected``. A ``CommandResult``
        with status ERROR on timeout.

    :raises SystemExit: Exit code ``1`` when the input does not match ``expected``.
    """
    entered = prompt_measurement(message=message, key=key, timeout_s=timeout_s)
    if entered is None:
        return CommandResult(status="ERROR", message=f"no input within {timeout_s} s")
    if entered != expected:
        _fail_and_exit(
            message=f"expected {expected!r}, got {entered!r}",
            key=key,
            command=_PROMPT_EXIT_COMMAND,
        )
    return None
