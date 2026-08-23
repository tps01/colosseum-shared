"""Pytest fixtures for colosseum-shared unit tests."""

from __future__ import annotations

import colosseum.context as context_module
import pytest


@pytest.fixture(autouse=True)
def _reset_colosseum_context() -> None:
    """Give each test a fresh runtime by clearing the active context."""
    old = context_module._ACTIVE_CONTEXT
    if old is not None:
        old.auto_finalize = False
        if old.db.is_initialized():
            old.db.close()
    context_module._ACTIVE_CONTEXT = None
    yield
    current = context_module._ACTIVE_CONTEXT
    if current is not None:
        current.auto_finalize = False
        if current.db.is_initialized():
            current.db.close()
    context_module._ACTIVE_CONTEXT = None
