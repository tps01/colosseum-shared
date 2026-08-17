"""Colosseum shared utilities plugin (regex, parsing)."""

__colosseum_domain__ = "shared"

__version__ = "0.2.0"

from colosseum.plugins.registry import PluginRegistry


def register(registry: PluginRegistry) -> None:
    from colosseum_shared import api

    registry.register_namespace("shared", api)
