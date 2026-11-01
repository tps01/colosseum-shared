"""Local shared APIs that opt into dry_run=\"call\"."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import colosseum as col
from colosseum.config import load_config
from colosseum.context import get_context
from colosseum.decorators._common import DRY_RUN_ATTR
from colosseum.runner.paths import ensure_runtime_ready
from colosseum_shared.prompt import api as prompt_api

if TYPE_CHECKING:
    import pytest


def _load_shared_dry_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "config.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    ctx = get_context()
    ensure_runtime_ready(ctx)
    ctx.run_options.dry_run = True


def test_comment_runs_under_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _load_shared_dry_run(tmp_path, monkeypatch)
    assert getattr(prompt_api.comment, DRY_RUN_ATTR) == "call"
    prompt_api.comment(message="dry-run annotation")
    assert "dry-run annotation" in capsys.readouterr().out


def test_measure_value_and_verify_field_under_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_dry_run(tmp_path, monkeypatch)
    assert getattr(col.shared.measure_value, DRY_RUN_ATTR) == "call"
    assert getattr(col.shared.verify.verify_field, DRY_RUN_ATTR) == "call"
    assert col.shared.measure_value(key="rail_v", value=3.3) == 3.3
    result = col.shared.verify.verify_field(key="rail_v", expected_val=3.3, tolerance=0.1)
    assert result.status == "PASS"
    row = get_context().db.get_measurement("shared", "measure_value", "rail_v", row_index=0)
    assert row is not None
    assert row.value == 3.3
