"""Unit tests for col.shared.wait."""

from __future__ import annotations

from pathlib import Path

import colosseum as col
import pytest
from colosseum.config import load_config


def _load(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = (
        Path(__file__).resolve().parents[2] / "examples" / "configs" / "config.shared.sim.toml"
    )
    monkeypatch.chdir(tmp_path)
    load_config(config_path)


def test_wait_parses_units_and_sleeps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load(tmp_path, monkeypatch)
    slept: list[float] = []
    monkeypatch.setattr("colosseum_shared.wait.time.sleep", slept.append)
    col.shared.wait(duration="250ms")
    assert len(slept) == 1
    assert slept[0] == pytest.approx(0.25)


def test_wait_progress_bar_ticks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    _load(tmp_path, monkeypatch)
    ticks = {"n": 0}

    def fake_monotonic() -> float:
        values = [0.0, 0.15, 0.3, 0.3]
        idx = min(ticks["n"], len(values) - 1)
        ticks["n"] += 1
        return values[idx]

    monkeypatch.setattr("colosseum_shared.wait.time.monotonic", fake_monotonic)
    monkeypatch.setattr("colosseum_shared.wait.time.sleep", lambda _s: None)
    col.shared.wait(duration=0.3, progress_bar=True)
    out = capsys.readouterr().out
    assert "[" + ("#" * 40) + "]" in out
    assert out.endswith("0.3/0.3s\n") or "0.3/0.3s\n" in out


def test_wait_progress_bar_zero_duration_returns_immediately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    _load(tmp_path, monkeypatch)
    slept: list[float] = []
    monkeypatch.setattr("colosseum_shared.wait.time.sleep", slept.append)
    col.shared.wait(duration=0, progress_bar=True)
    assert slept == []
    assert "\r[" not in capsys.readouterr().out


def test_wait_default_uses_plain_sleep_without_bar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str],
) -> None:
    _load(tmp_path, monkeypatch)
    slept: list[float] = []
    monkeypatch.setattr("colosseum_shared.wait.time.sleep", slept.append)
    col.shared.wait(duration=0.1)
    assert slept == [pytest.approx(0.1)]
    assert "\r[" not in capsys.readouterr().out


def test_wait_rejects_nonfinite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _load(tmp_path, monkeypatch)
    slept: list[float] = []

    def fake_sleep(seconds: float) -> None:
        slept.append(seconds)
        if len(slept) > 4:
            raise RuntimeError("stopped non-finite wait")

    monkeypatch.setattr("colosseum_shared.wait.time.sleep", fake_sleep)
    for duration in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite"):
            col.shared.wait(duration=duration)
    with pytest.raises(ValueError, match="finite"):
        col.shared.wait(duration=float("inf"), progress_bar=True)
    assert slept == []
