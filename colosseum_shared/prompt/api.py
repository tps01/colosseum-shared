"""Operator prompts and manual test annotations (``col.shared.prompt``)."""

from __future__ import annotations

from typing import NoReturn

from colosseum.context import get_context
from colosseum.database import CommandRow
from colosseum.decorators import CommandResult, command, measurement
from colosseum.logging import get_logger
from colosseum.output import ensure_runtime_ready
from colosseum.results import endex

from colosseum_shared.prompt._stdin import read_line, wait_any_key

_logger = get_logger("colosseum.shared")


def _fail_and_exit(*, message: str, key: str, command: str) -> NoReturn:
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
        )
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


@command
def prompt(*, message: str) -> None:
    """Display a message and block until the operator presses any key.

    :param message: Text shown on stdout before waiting for input.
    :type message: str

    :returns: None
    """
    _logger.info("%s", message)
    wait_any_key(message=message)


@measurement
def prompt_measurement(*, message: str, key: str) -> str:
    """Prompt for a line of operator input and store it as a measurement.

    :param message: Prompt text shown before reading stdin.
    :type message: str
    :param key: Unique measurement key for this run.
    :type key: str

    :returns: The operator's input line (without trailing newline).
    :rtype: str
    """
    value = read_line(message=message)
    _logger.info("prompt_measurement key=%s", key)
    return value


@command
def comment(*, message: str) -> None:
    """Log an operator or test annotation at INFO in ``debug.log``.

    :param message: Text written to the Colosseum log.
    :type message: str

    :returns: None
    """
    _logger.info("%s", message)


@command
def prompt_exit(*, message: str, key: str, expected: str) -> None:
    """Prompt for input, record it, and exit the run immediately on mismatch.

    The entered value is stored as a measurement under ``key``. When it does not
    exactly match ``expected``, the run is marked FAIL and ``col.endex()`` is
    invoked (the process exits without returning to the caller).

    :param message: Prompt text shown before reading stdin.
    :type message: str
    :param key: Measurement key for the operator input.
    :type key: str
    :param expected: Required exact match for the entered line.
    :type expected: str

    :returns: None when the input matches ``expected``.

    :raises SystemExit: Exit code ``1`` when the input does not match ``expected``.
    """
    entered = prompt_measurement(message=message, key=key)
    if entered != expected:
        _fail_and_exit(
            message=f"expected {expected!r}, got {entered!r}",
            key=key,
            command=_PROMPT_EXIT_COMMAND,
        )
