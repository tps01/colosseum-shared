"""One-off measurement helpers (``col.shared.measure_*``)."""

from __future__ import annotations

import os
import time

from colosseum.decorators import measurement
from colosseum.logging import get_logger

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

    :param key: Unique measurement key within domain ``shared``.
    :type key: str

    :returns: Perf-counter mark value.
    :rtype: float
    """
    _ = key
    mark = time.perf_counter()
    _logger.debug("measure_mark key=%s mark=%s", key, mark)
    return mark
