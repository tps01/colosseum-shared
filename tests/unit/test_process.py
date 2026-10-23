"""Local process helper."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import colosseum as col
from colosseum.config import load_config
from colosseum.context import get_context
from colosseum.runner.paths import ensure_runtime_ready

if TYPE_CHECKING:
    import pytest


def _load_shared_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "config.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    ensure_runtime_ready(get_context())


def test_run_process_reads_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    result = col.shared.run_process(
        key="echo",
        argv=[sys.executable, "-c", "print('ready')"],
        terminator="ready",
        timeout_s=10,
    )
    assert result["timed_out"] is False
    assert result["exit_code"] == 0
    assert "ready" in str(result["stdout"])


def test_run_process_sends_stdin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    result = col.shared.run_process(
        key="echo-in",
        argv=[sys.executable, "-c", "import sys; print(sys.stdin.readline().strip())"],
        stdin_line="hi",
        timeout_s=10,
    )
    assert result["timed_out"] is False
    assert result["stdout"] == "hi\n"


def test_run_process_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    result = col.shared.run_process(
        key="sleep",
        argv=[sys.executable, "-c", "import time; time.sleep(30)"],
        timeout_s=0.2,
    )
    assert result["timed_out"] is True
    assert result["exit_code"] is None
