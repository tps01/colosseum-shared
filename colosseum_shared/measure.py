"""One-off measurement helpers (``col.shared.measure_*``)."""

from __future__ import annotations

import hashlib
import os
import time
from datetime import datetime, timezone

from colosseum.decorators import measurement
from colosseum.logging import get_logger

from colosseum_shared._evidence import resolve_path

_logger = get_logger("colosseum.shared")


@measurement
def measure_value(*, key: str, value: object) -> object:
    """Record an arbitrary literal as a measurement (one-off evidence).

    :param key: Unique measurement key within domain ``shared``.
    :type key: str
    :param value: Value to store (string, number, dict, etc.).
    :type value: object

    :returns: The same ``value``.
    :rtype: object
    """
    _ = key
    _logger.debug("measure_value key=%s type=%s", key, type(value).__name__)
    return value


@measurement
def measure_env(*, key: str, name: str) -> str:
    """Record an environment variable value.

    :param key: Unique measurement key within domain ``shared``.
    :type key: str
    :param name: Environment variable name.
    :type name: str

    :returns: Environment value string.
    :rtype: str

    :raises KeyError: When ``name`` is not set in the environment.
    """
    _ = key
    if name not in os.environ:
        raise KeyError(f"environment variable {name!r} is not set")
    value = os.environ[name]
    _logger.debug("measure_env key=%s name=%s", key, name)
    return value


@measurement
def measure_mark(*, key: str) -> float:
    """Record ``time.perf_counter()`` for later ``verify_elapsed``.

    This is a monotonic elapsed mark for the current process. It is not a wall
    time, and it is not comparable across runs or machines. Use
    ``measure_wall_time`` when the procedure needs a UTC clock reading.

    :param key: Unique measurement key within domain ``shared``.
    :type key: str

    :returns: Perf-counter mark value.
    :rtype: float
    """
    _ = key
    mark = time.perf_counter()
    _logger.debug("measure_mark key=%s mark=%s", key, mark)
    return mark


@measurement
def measure_wall_time(*, key: str) -> str:
    """Record the current UTC time as an ISO-8601 string.

    The value is the bench wall clock (``datetime.now(timezone.utc)``), the same
    kind of timestamp core stores on evidence rows. A clock step can move it.
    It is the reading a procedure prints or compares to a product log. It is not
    a monotonic elapsed budget; use ``measure_mark`` and ``verify_elapsed`` for that.

    :param key: Unique measurement key within domain ``shared``.
    :type key: str

    :returns: Timezone-aware UTC timestamp.
    :rtype: str
    """
    _ = key
    stamp = datetime.now(timezone.utc).isoformat()
    _logger.debug("measure_wall_time key=%s stamp=%s", key, stamp)
    return stamp


@measurement
def measure_file_text(*, key: str, path: str) -> str:
    """Record a UTF-8 text file as a measurement.

    :param key: Unique measurement key within domain ``shared``.
    :type key: str
    :param path: Absolute path, or relative to the run output directory.
    :type path: str

    :returns: File text.
    :rtype: str

    :raises UnicodeDecodeError: When the file is not valid UTF-8.
    """
    _ = key
    text = resolve_path(path).read_text(encoding="utf-8")
    _logger.debug("measure_file_text key=%s path=%s bytes=%s", key, path, len(text))
    return text


@measurement
def measure_file_sha256(*, key: str, path: str) -> str:
    """Record the SHA-256 hex digest of a file.

    :param key: Unique measurement key within domain ``shared``.
    :type key: str
    :param path: Absolute path, or relative to the run output directory.
    :type path: str

    :returns: Lowercase hex digest.
    :rtype: str
    """
    _ = key
    digest = hashlib.sha256(resolve_path(path).read_bytes()).hexdigest()
    _logger.debug("measure_file_sha256 key=%s path=%s", key, path)
    return digest
