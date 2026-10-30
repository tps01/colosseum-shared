"""File existence and side-effect file verifications (``col.shared.verify``)."""

from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING

from colosseum.decorators import (
    VerificationResult,
    missing_measurement_result,
    verification,
)
from colosseum.logging import get_logger

from colosseum_shared._evidence import latest_measurement_by_key, resolve_path
from colosseum_shared.duration import parse_duration
from colosseum_shared.verify._command import with_verify_command

if TYPE_CHECKING:
    from pathlib import Path

_logger = get_logger("colosseum.shared")


@verification
@with_verify_command("verify_file_exists")
def verify_file_exists(
    *,
    key: str,
    path: str | None = None,
    optional: bool = False,
) -> VerificationResult:
    """Verify a regular file exists on disk, optionally using a prior measurement as the path.

    A directory does not pass.

    :param key: Verification evidence key (and measurement key when ``path`` is omitted).
    :type key: str
    :param path: Relative path under the run output directory, or an absolute path.
    :type path: str | None, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    file_path = path
    if file_path is None:
        row = latest_measurement_by_key(key)
        if row is None or row.value is None:
            _logger.debug("verify_file_exists key=%s missing measurement for path", key)
            return missing_measurement_result(key=key, optional=optional)
        file_path = str(row.value)
    if not file_path:
        return VerificationResult(
            status="ERROR",
            message="no path provided and measurement value is empty",
            optional=optional,
        )
    resolved = resolve_path(file_path)
    is_regular = resolved.is_file()
    _logger.debug("verify_file_exists key=%s path=%s is_file=%s", key, resolved, is_regular)
    if is_regular:
        return VerificationResult(
            status="PASS",
            message="",
            optional=optional,
            actual=str(resolved),
        )
    return VerificationResult(
        status="FAIL",
        message=f"file not found: {resolved}",
        optional=optional,
        actual=str(resolved),
    )


@verification
@with_verify_command("verify_file_absent")
def verify_file_absent(
    *,
    key: str,
    path: str | None = None,
    optional: bool = False,
) -> VerificationResult:
    """PASS when ``path`` is not an existing regular file.

    A missing path passes. A directory passes because it is not a regular file.

    :param key: Verification evidence key (and measurement key when ``path`` is omitted).
    :type key: str
    :param path: Relative path under the run output directory, or an absolute path.
    :type path: str | None, optional
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    :type optional: bool, optional

    :returns: VerificationResult with PASS, FAIL, or ERROR status.
    :rtype: VerificationResult
    """
    file_path = path
    if file_path is None:
        row = latest_measurement_by_key(key)
        if row is None or row.value is None:
            return missing_measurement_result(key=key, optional=optional)
        file_path = str(row.value)
    if not file_path:
        return VerificationResult(
            status="ERROR",
            message="no path provided and measurement value is empty",
            optional=optional,
        )
    resolved = resolve_path(file_path)
    if resolved.is_file():
        return VerificationResult(
            status="FAIL",
            message=f"file exists: {resolved}",
            optional=optional,
            actual=str(resolved),
        )
    return VerificationResult(
        status="PASS",
        message="",
        optional=optional,
        actual=str(resolved),
    )


@verification
@with_verify_command("verify_file_contents")
def verify_file_contents(
    *,
    key: str,
    pattern: str,
    path: str | None = None,
    count: int = 1,
    invert: bool = False,
    optional: bool = False,
) -> VerificationResult:
    """PASS when a regex appears in a file at least ``count`` times.

    With ``invert=True``, PASS when the pattern appears fewer than ``count`` times
    (so ``count=1`` means the pattern must be absent).

    :param key: Verification evidence key (and measurement key when ``path`` is omitted).
    :param pattern: Regular expression searched in the file text.
    :param path: Absolute path, or relative to the run output directory. When
        omitted, the latest measurement for ``key`` is used as the path.
    :param count: Required match count threshold (must be >= 1).
    :param invert: Invert the threshold comparison.
    :param optional: When ``True``, FAIL/ERROR does not fail the run at ``col.endex()``.
    """
    if count < 1:
        return VerificationResult(
            status="ERROR",
            message=f"count must be >= 1, got {count}",
            optional=optional,
        )
    file_path = path
    if file_path is None:
        row = latest_measurement_by_key(key)
        if row is None or row.value is None:
            _logger.debug("verify_file_contents key=%s missing measurement for path", key)
            return missing_measurement_result(key=key, optional=optional)
        file_path = str(row.value)
    if not file_path:
        return VerificationResult(
            status="ERROR",
            message="no path provided and measurement value is empty",
            optional=optional,
        )
    resolved = resolve_path(file_path)
    if not resolved.is_file():
        return VerificationResult(
            status="FAIL",
            message=f"file not found: {resolved}",
            optional=optional,
            actual=str(resolved),
        )
    try:
        text = resolved.read_text(encoding="utf-8")
    except OSError as exc:
        return VerificationResult(
            status="ERROR",
            message=f"could not read {resolved}: {exc}",
            optional=optional,
            actual=str(resolved),
        )
    try:
        compiled = re.compile(pattern)
    except re.error as exc:
        return VerificationResult(
            status="ERROR",
            message=f"invalid pattern {pattern!r}: {exc}",
            optional=optional,
        )
    hits = sum(1 for _ in compiled.finditer(text))
    _logger.debug(
        "verify_file_contents key=%s path=%s pattern=%r count=%s invert=%s hits=%s",
        key,
        resolved,
        pattern,
        count,
        invert,
        hits,
    )
    if invert:
        if hits < count:
            return VerificationResult(
                status="PASS",
                message=f"{hits} match(es) < {count}",
                optional=optional,
                actual=hits,
            )
        return VerificationResult(
            status="FAIL",
            message=f"expected fewer than {count} match(es) of {pattern!r}, found {hits}",
            optional=optional,
            actual=hits,
        )
    if hits >= count:
        return VerificationResult(
            status="PASS",
            message=f"{hits} match(es) >= {count}",
            optional=optional,
            actual=hits,
        )
    return VerificationResult(
        status="FAIL",
        message=f"expected at least {count} match(es) of {pattern!r}, found {hits}",
        optional=optional,
        actual=hits,
    )


def _relative_file_id(root: Path, path: Path) -> str:
    """Identity of ``path`` relative to the monitored directory, with POSIX separators."""
    return path.relative_to(root).as_posix()


def _require_nonnegative_finite(label: str, value: float | int | str) -> float:
    """Return seconds. Numbers are seconds; strings may use duration suffixes (``61s``)."""
    try:
        return parse_duration(value)
    except ValueError as exc:
        raise ValueError(
            f"{label} must be a finite nonnegative duration, got {value!r}",
        ) from exc


def snapshot_files(directory: str, *, pattern: str = "*") -> set[str]:
    """Return paths relative to ``directory`` for files matching ``pattern``.

    Identifiers use POSIX separators. A file directly in ``directory`` is still
    just its name, so a non-recursive snapshot is unchanged. Nested matches such
    as ``a/result.txt`` and ``b/result.txt`` stay distinct.

    :param directory: Absolute directory, or relative to the run output directory.
    :param pattern: Glob relative to ``directory`` (for example ``*_screenshot.*``).
    """
    root = resolve_path(directory)
    if not root.is_dir():
        return set()
    return {
        _relative_file_id(root, path) for path in root.glob(pattern) if path.is_file()
    }


def wait_for_log_line(
    path: str,
    *,
    pattern: str,
    timeout_s: float | int | str = 10.0,
    poll_s: float | int | str = 0.25,
) -> str | None:
    """Poll ``path`` until ``pattern`` matches, or return ``None`` at ``timeout_s``.

    The file may be missing at the start. Each look reads the current UTF-8 text
    and replaces invalid bytes. ``timeout_s`` of zero looks once. This does not
    judge a finished file; use ``verify_file_contents`` for that.

    :param path: Absolute path, or relative to the run output directory.
    :param pattern: Regular expression searched in the file text.
    :param timeout_s: How long to poll. A number is seconds; a string may use
        duration suffixes (``500ms``, ``61s``). Finite and nonnegative.
    :param poll_s: Delay between looks. Same duration forms as ``timeout_s``.
    :returns: The matched text, or ``None`` when the wait expires.
    """
    timeout_s = _require_nonnegative_finite("timeout_s", timeout_s)
    poll_s = _require_nonnegative_finite("poll_s", poll_s)
    compiled = re.compile(pattern)
    resolved = resolve_path(path)
    deadline = time.monotonic() + timeout_s
    while True:
        if resolved.is_file():
            text = resolved.read_text(encoding="utf-8", errors="replace")
            match = compiled.search(text)
            if match is not None:
                return match.group(0)
        if time.monotonic() >= deadline:
            return None
        time.sleep(poll_s)


def wait_for_new_file(
    directory: str,
    *,
    before: set[str] | None = None,
    pattern: str = "*",
    timeout_s: float | int | str = 10.0,
    poll_s: float | int | str = 0.25,
) -> Path | None:
    """Poll until a new file matching ``pattern`` appears; return its path or ``None``.

    ``before`` is typically ``snapshot_files(...)`` taken before the action under test.
    Entries are paths relative to ``directory``. When omitted, an empty set is used
    (any matching file counts as new). ``timeout_s`` and ``poll_s`` are seconds, or
    duration strings such as ``500ms`` or ``61s``. Both must be finite and
    nonnegative; zero timeout returns without waiting.

    :param directory: Absolute directory, or a path relative to the active run output directory.
    :param before: Relative file paths returned by snapshot_files before the action; None uses
        an empty baseline.
    :param pattern: Glob pattern relative to directory, such as `*.txt`; defaults to `*`.
    :param timeout_s: Maximum wait in seconds. Expiration does not establish that the operation
        completed. Default: ``10.0``.
    :param poll_s: Delay between polls in seconds, or a duration string such as 500ms. Must be
        finite and nonnegative. Default: ``0.25``.

    :returns: Path to the new matching file, or None when the wait expires.
    """
    timeout_s = _require_nonnegative_finite("timeout_s", timeout_s)
    poll_s = _require_nonnegative_finite("poll_s", poll_s)
    root = resolve_path(directory)
    seen = set() if before is None else set(before)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if root.is_dir():
            for path in root.glob(pattern):
                if path.is_file() and _relative_file_id(root, path) not in seen:
                    return path
        time.sleep(poll_s)
    return None


@verification
@with_verify_command("verify_new_file")
def verify_new_file(
    *,
    key: str,
    directory: str,
    before: set[str] | None = None,
    pattern: str = "*",
    timeout_s: float | int | str = 10.0,
    optional: bool = False,
) -> VerificationResult:
    """PASS when a new file matching ``pattern`` appears under ``directory``.

    :param key: Verification evidence key.
    :param directory: Absolute directory, or relative to the run output directory.
    :param before: Relative paths from ``snapshot_files`` before the triggering action.
    :param pattern: Glob relative to ``directory``.
    :param timeout_s: How long to wait for a new match. A number is seconds; a
        string may use duration suffixes (``500ms``, ``61s``). Finite and nonnegative.
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.


    Take snapshot_files before the triggering action and pass that set as
    before. See the new-file recipe for a complete runnable example.
    """
    _ = key
    timeout_s = _require_nonnegative_finite("timeout_s", timeout_s)
    found = wait_for_new_file(
        directory,
        before=before,
        pattern=pattern,
        timeout_s=timeout_s,
    )
    if found is not None:
        relative = _relative_file_id(resolve_path(directory), found)
        return VerificationResult(
            status="PASS",
            message=f"new file {relative}",
            optional=optional,
            actual=str(found),
        )
    return VerificationResult(
        status="FAIL",
        message=f"no new file matching {pattern!r} within {timeout_s:.0f}s",
        optional=optional,
    )


@verification
@with_verify_command("verify_no_new_file")
def verify_no_new_file(
    *,
    key: str,
    directory: str,
    before: set[str] | None = None,
    pattern: str = "*",
    settle_s: float | int | str = 2.0,
    optional: bool = False,
) -> VerificationResult:
    """PASS when no new file matching ``pattern`` appears during ``settle_s``.

    :param key: Verification evidence key.
    :param directory: Absolute directory, or relative to the run output directory.
    :param before: Relative paths from ``snapshot_files`` before the quiet period.
    :param pattern: Glob relative to ``directory``.
    :param settle_s: How long the directory must stay quiet. A number is seconds;
        a string may use duration suffixes (``500ms``, ``61s``). Finite and
        nonnegative; zero returns immediately.
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.
    """
    _ = key
    settle_s = _require_nonnegative_finite("settle_s", settle_s)
    found = wait_for_new_file(
        directory,
        before=before,
        pattern=pattern,
        timeout_s=settle_s,
    )
    if found is None:
        return VerificationResult(
            status="PASS",
            message=f"quiet for {settle_s:.1f}s",
            optional=optional,
        )
    relative = _relative_file_id(resolve_path(directory), found)
    return VerificationResult(
        status="FAIL",
        message=f"unexpected new file {relative}",
        optional=optional,
        actual=str(found),
    )
