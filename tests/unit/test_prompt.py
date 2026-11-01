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
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "config.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)
    ensure_runtime_ready(get_context())


def test_comment_logs_info(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    # Public re-export: col.shared.comment → prompt.comment
    col.shared.comment(message="Attach probe to J5")
    # Core routes plugin loggers to the run stdout handler (not pytest caplog).
    assert "Attach probe to J5" in capsys.readouterr().out


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


def test_prompt_timeout_returns_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(prompt_api, "wait_any_key", lambda *, message, timeout_s: False)
    result = prompt_api.prompt(message="LED green?", timeout_s=0.1)
    assert result is not None
    assert result.status == "ERROR"
    assert result.optional is False


def test_prompt_timeout_optional_does_not_fail_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(prompt_api, "wait_any_key", lambda *, message, timeout_s: False)
    result = prompt_api.prompt(message="LED green?", timeout_s=0.1, optional=True)
    assert result is not None
    assert result.status == "ERROR"
    assert result.optional is True
    row = get_context().db.fetch_table_rows("commands")[-1]
    assert row["optional"] in (1, True)
    assert get_context().result_aggregator.exit_code() == 0


def test_prompt_measurement_timeout_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(
        prompt_api, "read_line", lambda *, message, timeout_s=None: None,
    )
    assert prompt_api.prompt_measurement(
        message="Serial: ", key="serial", timeout_s=0.1,
    ) is None
    row = get_context().db.get_measurement(
        "shared", _PROMPT_MEASUREMENT_COMMAND, "serial", row_index=0,
    )
    assert row is not None
    assert row.status == "ERROR"


def test_prompt_choice_records_answer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(prompt_api, "read_line", lambda *, message, timeout_s=None: "PASS")
    result = prompt_api.prompt_choice(
        message="Result: ", key="verdict", choices=("PASS", "FAIL"),
    )
    assert result.status == "PASS"
    monkeypatch.setattr(prompt_api, "read_line", lambda *, message, timeout_s=None: "MAYBE")
    failed = prompt_api.prompt_choice(
        message="Result: ", key="verdict2", choices=("PASS", "FAIL"),
    )
    assert failed.status == "FAIL"


def test_prompt_exit_timeout_does_not_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(
        prompt_api, "read_line", lambda *, message, timeout_s=None: None,
    )
    result = prompt_api.prompt_exit(
        message="Type PASS: ", key="ack", expected="PASS", timeout_s=0.1,
    )
    assert result is not None
    assert result.status == "ERROR"
    assert result.optional is False


def test_prompt_exit_optional_mismatch_returns_without_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(prompt_api, "read_line", lambda *, message: "FAIL")
    result = prompt_api.prompt_exit(
        message="Type PASS: ", key="ack", expected="PASS", optional=True,
    )
    assert result is not None
    assert result.status == "FAIL"
    assert result.optional is True
    row = get_context().db.fetch_table_rows("commands")[-1]
    assert row["status"] == "FAIL"
    assert row["optional"] in (1, True)
    assert get_context().result_aggregator.exit_code() == 0


def test_prompt_namespace_via_col(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load_shared_config(tmp_path, monkeypatch)
    monkeypatch.setattr(prompt_api, "read_line", lambda *, message: "abc")
    value = col.shared.prompt.prompt_measurement(message="Enter: ", key="input")
    assert value == "abc"
