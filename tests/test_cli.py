from __future__ import annotations

from typing import Any

import pytest

import gptty.commands.ask as ask_command
from gptty import cli
from gptty.io import StdinReadError


def test_ask_uses_auto_stdin_mode_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_read_stdin_text(mode: str) -> str:
        calls["mode"] = mode
        return "piped text"

    def fake_run_ask(args: Any, *, stdin_text: str | None = None) -> int:
        calls["prompt"] = args.prompt
        calls["stdin_text"] = stdin_text
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(ask_command, "run_ask", fake_run_ask)

    assert cli.main(["ask", "review"]) == 0
    assert calls == {
        "mode": "auto",
        "prompt": ["review"],
        "stdin_text": "piped text",
    }


def test_ask_stdin_flag_forces_stdin_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_read_stdin_text(mode: str) -> str:
        calls["mode"] = mode
        return "forced text"

    def fake_run_ask(args: Any, *, stdin_text: str | None = None) -> int:
        calls["prompt"] = args.prompt
        calls["stdin_text"] = stdin_text
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(ask_command, "run_ask", fake_run_ask)

    assert cli.main(["ask", "--stdin", "summarize"]) == 0
    assert calls == {
        "mode": "always",
        "prompt": ["summarize"],
        "stdin_text": "forced text",
    }


def test_ask_no_stdin_flag_ignores_piped_stdin(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_read_stdin_text(mode: str) -> None:
        calls["mode"] = mode
        return None

    def fake_run_ask(args: Any, *, stdin_text: str | None = None) -> int:
        calls["prompt"] = args.prompt
        calls["stdin_text"] = stdin_text
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(ask_command, "run_ask", fake_run_ask)

    assert cli.main(["ask", "--no-stdin", "ignore", "pipe"]) == 0
    assert calls == {
        "mode": "never",
        "prompt": ["ignore", "pipe"],
        "stdin_text": None,
    }


def test_ask_stdin_read_error_returns_1(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_read_stdin_text(mode: str) -> str:
        raise StdinReadError("failed to read stdin: broken pipe")

    def fake_run_ask(args: Any, *, stdin_text: str | None = None) -> int:
        raise AssertionError("run_ask should not be called when stdin read fails")

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(ask_command, "run_ask", fake_run_ask)

    assert cli.main(["ask", "review"]) == 1
    captured = capsys.readouterr()
    assert "gptty: failed to read stdin" in captured.err
