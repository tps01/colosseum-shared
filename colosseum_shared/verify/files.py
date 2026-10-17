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
from colosseum_shared.verify._command import with_verify_command

if TYPE_CHECKING:
    from pathlib import Path

_logger = get_logger("colosseum.shared")


@verification
def verify_file_exists(
    *,
    key: str,
    path: str | None = None,
    optional: bool = False,
) -> VerificationResult:
    """Verify a file exists on disk, optionally using a prior measurement as the path.

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
    exists = resolved.exists()
    _logger.debug("verify_file_exists key=%s path=%s exists=%s", key, resolved, exists)
    if exists:
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


verify_file_exists = with_verify_command(verify_file_exists, "verify_file_exists")


@verification
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


verify_file_contents = with_verify_command(verify_file_contents, "verify_file_contents")


def snapshot_files(directory: str, *, pattern: str = "*") -> set[str]:
    """Return basenames currently matching ``pattern`` under ``directory``.

    :param directory: Absolute directory, or relative to the run output directory.
    :param pattern: Glob relative to ``directory`` (for example ``*_screenshot.*``).
    """
    root = resolve_path(directory)
    if not root.is_dir():
        return set()
    return {path.name for path in root.glob(pattern) if path.is_file()}


def wait_for_new_file(
    directory: str,
    *,
    before: set[str] | None = None,
    pattern: str = "*",
    timeout_s: float = 10.0,
    poll_s: float = 0.25,
) -> Path | None:
    """Poll until a new file matching ``pattern`` appears; return its path or ``None``.

    ``before`` is typically ``snapshot_files(...)`` taken before the action under test.
    When omitted, an empty set is used (any matching file counts as new).
    """
    root = resolve_path(directory)
    seen = set() if before is None else set(before)
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if root.is_dir():
            for path in root.glob(pattern):
                if path.is_file() and path.name not in seen:
                    return path
        time.sleep(poll_s)
    return None


@verification
def verify_new_file(
    *,
    key: str,
    directory: str,
    before: set[str] | None = None,
    pattern: str = "*",
    timeout_s: float = 10.0,
    optional: bool = False,
) -> VerificationResult:
    """PASS when a new file matching ``pattern`` appears under ``directory``.

    :param key: Verification evidence key.
    :param directory: Absolute directory, or relative to the run output directory.
    :param before: Basenames from ``snapshot_files`` before the triggering action.
    :param pattern: Glob relative to ``directory``.
    :param timeout_s: How long to wait for a new match.
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.
    """
    _ = key
    found = wait_for_new_file(
        directory,
        before=before,
        pattern=pattern,
        timeout_s=timeout_s,
    )
    if found is not None:
        return VerificationResult(
            status="PASS",
            message=f"new file {found.name}",
            optional=optional,
            actual=str(found),
        )
    return VerificationResult(
        status="FAIL",
        message=f"no new file matching {pattern!r} within {timeout_s:.0f}s",
        optional=optional,
    )


verify_new_file = with_verify_command(verify_new_file, "verify_new_file")


@verification
def verify_no_new_file(
    *,
    key: str,
    directory: str,
    before: set[str] | None = None,
    pattern: str = "*",
    settle_s: float = 2.0,
    optional: bool = False,
) -> VerificationResult:
    """PASS when no new file matching ``pattern`` appears during ``settle_s``.

    :param key: Verification evidence key.
    :param directory: Absolute directory, or relative to the run output directory.
    :param before: Basenames from ``snapshot_files`` before the quiet period.
    :param pattern: Glob relative to ``directory``.
    :param settle_s: How long the directory must stay quiet.
    :param optional: When ``True``, FAIL does not fail the run at ``col.endex()``.
    """
    _ = key
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
    return VerificationResult(
        status="FAIL",
        message=f"unexpected new file {found.name}",
        optional=optional,
        actual=str(found),
    )


verify_no_new_file = with_verify_command(verify_no_new_file, "verify_no_new_file")
