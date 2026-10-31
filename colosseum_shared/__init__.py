"""Colosseum shared utilities plugin (verify, regex, parsing, wait, prompts)."""

from importlib import metadata

from colosseum.logging import get_logger
from colosseum.plugins.lazy import lazy_module
from colosseum.plugins.registry import PluginRegistry

__colosseum_domain__ = "shared"

try:
    __version__ = metadata.version("colosseum-shared")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0"

_logger = get_logger("colosseum.shared")


def register(registry: PluginRegistry) -> None:
    registry.register_namespace("shared", lazy_module("colosseum_shared.api"))
    _logger.debug("Registered col.shared namespace")
