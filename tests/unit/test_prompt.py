"""U-SH: operator prompt helpers."""

from __future__ import annotations

from pathlib import Path

import colosseum as col
import pytest
from colosseum.config import load_config
from colosseum.context import get_context
from colosseum.runner.paths import ensure_runtime_ready
from colosseum_shared.prompt import api as prompt_api

_PROMPT_MEASUREMENT_COMMAND = "prompt.prompt_measurement"


def _load_shared_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "bench.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    ensure_runtime_ready(get_context())


def test_comment_logs_info(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    with caplog.at_level("INFO", logger="colosseum.shared"):
        prompt_api.comment(message="Attach probe to J5")
    assert "Attach probe to J5" in caplog.text


def test_prompt_measurement_records_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(prompt_api, "read_line", lambda *, message: "SN-12345")
    value = prompt_api.prompt_measurement(message="Serial: ", key="serial")
    assert value == "SN-12345"
    row = get_context().db.get_measurement(
        "shared", _PROMPT_MEASUREMENT_COMMAND, "serial", row_index=0,
    )
    assert row is not None
    assert row.value == "SN-12345"


def test_prompt_waits_for_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    calls: list[str] = []

    def _fake_wait(*, message: str) -> None:
        calls.append(message)

    monkeypatch.setattr(prompt_api, "wait_any_key", _fake_wait)
    prompt_api.prompt(message="LED green?")
    assert calls == ["LED green?"]


def test_prompt_exit_match_continues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(prompt_api, "read_line", lambda *, message: "PASS")
    prompt_api.prompt_exit(message="Type PASS: ", key="ack", expected="PASS")
    row = get_context().db.get_measurement(
        "shared", _PROMPT_MEASUREMENT_COMMAND, "ack", row_index=0,
    )
    assert row is not None
    assert row.value == "PASS"


def test_prompt_exit_mismatch_exits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(prompt_api, "read_line", lambda *, message: "FAIL")
    with pytest.raises(SystemExit) as exc_info:
        prompt_api.prompt_exit(message="Type PASS: ", key="ack", expected="PASS")
    assert exc_info.value.code == 1


def test_prompt_namespace_via_col(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(prompt_api, "read_line", lambda *, message: "abc")
    value = col.shared.prompt.prompt_measurement(message="Enter: ", key="input")
    assert value == "abc"
