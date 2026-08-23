"""Installed distribution metadata and plugin entry-point contracts."""

from importlib.metadata import distribution

import colosseum_shared


def test_complete_runtime_dependencies_are_installed_by_default() -> None:
    metadata = distribution("colosseum-shared")
    requirements = [requirement.lower() for requirement in metadata.requires or []]

    assert any(requirement.startswith("colosseum-core") for requirement in requirements)
    assert not any(requirement.startswith("paramiko") for requirement in requirements)
    extras = set(metadata.metadata.get_all("Provides-Extra") or [])
    assert extras.issubset({"test", "static"})


def test_plugin_entry_points_and_version_match_metadata() -> None:
    metadata = distribution("colosseum-shared")
    entry_points = {
        (entry_point.group, entry_point.name): entry_point.value
        for entry_point in metadata.entry_points
    }

    assert entry_points[("colosseum.plugins", "shared")] == "colosseum_shared:register"
    assert colosseum_shared.__version__ == metadata.version
