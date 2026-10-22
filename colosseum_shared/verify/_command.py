"""Attach stable ``verify.*`` command IDs before core captures them."""

from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar, cast

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import Any

F = TypeVar("F")


def with_verify_command(name: str) -> Callable[[F], F]:
    """Set ``__colosseum_command__`` to ``verify.<name>`` before ``@verification``.

    Core's verification decorator calls ``resolve_command(func)`` while building
    its wrapper, so the attribute has to be on the undecorated function.
    Setting it afterwards changes the visible attribute and leaves stored
    evidence on the old id.

    Rows already written with an unprefixed id (for example ``verify_field``)
    keep that id. This helper does not rewrite historical databases.
    """

    def decorate(func: F) -> F:
        target = cast("Any", func)
        target.__colosseum_command__ = f"verify.{name}"
        return func

    return decorate
