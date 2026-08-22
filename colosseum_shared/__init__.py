"""Colosseum shared utilities plugin (regex, parsing)."""

__colosseum_domain__ = "shared"

__version__ = "0.2.1"

from colosseum.logging import get_logger
from colosseum.plugins.registry import PluginRegistry

_logger = get_logger("colosseum.shared")


def register(registry: PluginRegistry) -> None:
    from colosseum_shared import api

    registry.register_namespace("shared", api)
    _logger.debug("Registered col.shared namespace")
