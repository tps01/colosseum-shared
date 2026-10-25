"""Parse human duration strings for ``col.shared.wait``.

The implementation lives in :func:`colosseum.units.parse_duration` so every
plugin can share it.
"""

from colosseum.units import parse_duration

__all__ = ["parse_duration"]
