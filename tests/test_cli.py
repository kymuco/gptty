from __future__ import annotations

from typing import Any

import pytest

import gptty.commands.ask as ask_command
import gptty.commands.attach as attach_command
import gptty.commands.chat as chat_command
import gptty.commands.export as export_command
import gptty.commands.messages as messages_command
import gptty.commands.send as send_command
import gptty.commands.status as status_command
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


def test_send_routes_to_send_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_read_stdin_text(mode: str) -> str:
        calls["mode"] = mode
        return "stdin context"

    def fake_run_send(args: Any, *, stdin_text: str | None = None) -> int:
        calls["prompt"] = args.prompt
        calls["to"] = args.to
        calls["new"] = args.new
        calls["state"] = args.state
        calls["auth"] = args.auth
        calls["timeout"] = args.timeout
        calls["format"] = args.format
        calls["model"] = args.model
        calls["no_stream"] = args.no_stream
        calls["stdin_text"] = stdin_text
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(send_command, "run_send", fake_run_send)

    assert cli.main([
        "send",
        "--to",
        "abc",
        "--stdin",
        "--state",
        "state.json",
        "--auth",
        "auth.json",
        "--timeout",
        "12",
        "--format",
        "json",
        "--model",
        "gpt-4o",
        "--no-stream",
        "review",
    ]) == 0
    assert calls == {
        "mode": "always",
        "prompt": ["review"],
        "to": "abc",
        "new": False,
        "state": "state.json",
        "auth": "auth.json",
        "timeout": 12,
        "format": "json",
        "model": "gpt-4o",
        "no_stream": True,
        "stdin_text": "stdin context",
    }


def test_send_stdin_read_error_returns_1(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_read_stdin_text(mode: str) -> str:
        raise StdinReadError("failed to read stdin: broken pipe")

    def fake_run_send(args: Any, *, stdin_text: str | None = None) -> int:
        raise AssertionError("run_send should not be called when stdin read fails")

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(send_command, "run_send", fake_run_send)

    assert cli.main(["send", "review"]) == 1
    captured = capsys.readouterr()
    assert "gptty: failed to read stdin" in captured.err


def test_chat_routes_to_sdk_chat_with_new_state_default(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run_chat(args: Any) -> int:
        calls["state"] = args.state
        calls["auth"] = args.auth
        calls["model"] = args.model
        calls["no_stream"] = args.no_stream
        calls["timeout"] = args.timeout
        return 0

    monkeypatch.setattr(chat_command, "run_chat", fake_run_chat)

    assert cli.main(["chat"]) == 0
    assert calls == {
        "state": "gptty_state.json",
        "auth": "auth_data.json",
        "model": None,
        "no_stream": False,
        "timeout": 90,
    }


def test_no_args_routes_to_sdk_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run_chat(args: Any) -> int:
        calls["state"] = args.state
        return 0

    monkeypatch.setattr(chat_command, "run_chat", fake_run_chat)

    assert cli.main([]) == 0
    assert calls == {"state": "gptty_state.json"}


def test_chat_legacy_routes_to_legacy_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run_legacy_chat(state_path: str, auth_file: str) -> int:
        calls["state_path"] = state_path
        calls["auth_file"] = auth_file
        return 0

    monkeypatch.setattr(cli, "_run_legacy_chat", fake_run_legacy_chat)

    assert cli.main(["chat", "--legacy"]) == 0
    assert calls == {
        "state_path": "webchat_state.json",
        "auth_file": "auth_data.json",
    }


def test_chat_legacy_keeps_custom_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run_legacy_chat(state_path: str, auth_file: str) -> int:
        calls["state_path"] = state_path
        calls["auth_file"] = auth_file
        return 0

    monkeypatch.setattr(cli, "_run_legacy_chat", fake_run_legacy_chat)

    assert cli.main(["chat", "--legacy", "--state", "old_state.json", "--auth", "auth.json"]) == 0
    assert calls == {
        "state_path": "old_state.json",
        "auth_file": "auth.json",
    }


def test_attach_routes_to_attach_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run_attach(args: Any) -> int:
        calls["url_or_id"] = args.url_or_id
        calls["state"] = args.state
        calls["auth"] = args.auth
        calls["timeout"] = args.timeout
        return 0

    monkeypatch.setattr(attach_command, "run_attach", fake_run_attach)

    assert cli.main(["attach", "abc", "--state", "state.json", "--auth", "auth.json", "--timeout", "12"]) == 0
    assert calls == {
        "url_or_id": "abc",
        "state": "state.json",
        "auth": "auth.json",
        "timeout": 12,
    }


def test_messages_routes_to_messages_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run_messages(args: Any) -> int:
        calls["url_or_id"] = args.url_or_id
        calls["last"] = args.last
        calls["state"] = args.state
        calls["format"] = args.format
        return 0

    monkeypatch.setattr(messages_command, "run_messages", fake_run_messages)

    assert cli.main([
        "messages",
        "abc",
        "--last",
        "5",
        "--state",
        "state.json",
        "--format",
        "markdown",
    ]) == 0
    assert calls == {
        "url_or_id": "abc",
        "last": 5,
        "state": "state.json",
        "format": "markdown",
    }


def test_export_routes_to_export_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run_export(args: Any) -> int:
        calls["url_or_id"] = args.url_or_id
        calls["last"] = args.last
        calls["state"] = args.state
        calls["auth"] = args.auth
        calls["timeout"] = args.timeout
        calls["format"] = args.format
        calls["output"] = args.output
        calls["overwrite"] = args.overwrite
        return 0

    monkeypatch.setattr(export_command, "run_export", fake_run_export)

    assert cli.main([
        "export",
        "abc",
        "--last",
        "5",
        "--state",
        "state.json",
        "--auth",
        "auth.json",
        "--timeout",
        "12",
        "--format",
        "json",
        "--output",
        "conversation.json",
        "--overwrite",
    ]) == 0
    assert calls == {
        "url_or_id": "abc",
        "last": 5,
        "state": "state.json",
        "auth": "auth.json",
        "timeout": 12,
        "format": "json",
        "output": "conversation.json",
        "overwrite": True,
    }


def test_export_defaults_to_markdown(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run_export(args: Any) -> int:
        calls["format"] = args.format
        return 0

    monkeypatch.setattr(export_command, "run_export", fake_run_export)

    assert cli.main(["export"]) == 0
    assert calls == {"format": "markdown"}


def test_status_routes_to_status_command(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_run_status(args: Any) -> int:
        calls["url_or_id"] = args.url_or_id
        calls["state"] = args.state
        calls["auth"] = args.auth
        calls["timeout"] = args.timeout
        calls["format"] = args.format
        return 0

    monkeypatch.setattr(status_command, "run_status", fake_run_status)

    assert cli.main([
        "status",
        "abc",
        "--state",
        "state.json",
        "--auth",
        "auth.json",
        "--timeout",
        "12",
        "--format",
        "json",
    ]) == 0
    assert calls == {
        "url_or_id": "abc",
        "state": "state.json",
        "auth": "auth.json",
        "timeout": 12,
        "format": "json",
    }
