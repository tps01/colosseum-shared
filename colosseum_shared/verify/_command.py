"""Attach stable ``verify.*`` command IDs when APIs live outside ``verify.api``."""

from __future__ import annotations

from typing import Any, TypeVar

F = TypeVar("F")


def with_verify_command(func: F, name: str) -> F:
    """Set ``__colosseum_command__`` to ``verify.<name>`` on a decorated callable."""
    target: Any = func
    target.__colosseum_command__ = f"verify.{name}"
    return func
