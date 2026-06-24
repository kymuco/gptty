from __future__ import annotations

from typing import Any

import pytest

import gptty.commands.ask as ask_command
import gptty.commands.send as send_command
from gptty import cli


def test_ask_routes_image_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_read_stdin_text(mode: str) -> None:
        calls["mode"] = mode
        return None

    def fake_run_ask(args: Any, *, stdin_text: str | None = None) -> int:
        calls["prompt"] = args.prompt
        calls["image"] = args.image
        calls["stdin_text"] = stdin_text
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(ask_command, "run_ask", fake_run_ask)

    assert cli.main([
        "ask",
        "--image",
        "before.png",
        "--image",
        "https://example.com/after.webp",
        "compare",
    ]) == 0
    assert calls == {
        "mode": "auto",
        "prompt": ["compare"],
        "image": ["before.png", "https://example.com/after.webp"],
        "stdin_text": None,
    }


def test_send_routes_image_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, Any] = {}

    def fake_read_stdin_text(mode: str) -> str:
        calls["mode"] = mode
        return "stdin context"

    def fake_run_send(args: Any, *, stdin_text: str | None = None) -> int:
        calls["prompt"] = args.prompt
        calls["to"] = args.to
        calls["image"] = args.image
        calls["stdin_text"] = stdin_text
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(send_command, "run_send", fake_run_send)

    assert cli.main([
        "send",
        "--to",
        "abc",
        "--image",
        "diagram.png",
        "review",
    ]) == 0
    assert calls == {
        "mode": "auto",
        "prompt": ["review"],
        "to": "abc",
        "image": ["diagram.png"],
        "stdin_text": "stdin context",
    }
