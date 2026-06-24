from __future__ import annotations

import json
from argparse import Namespace
from io import StringIO
from pathlib import Path
from typing import Any

from gptty.commands.export import run_export
from gptty.state import ChatState, save_chat_state


class FakeGpttyClient:
    instances: list["FakeGpttyClient"] = []

    def __init__(self, auth_file: str = "auth_data.json", timeout: int = 90) -> None:
        self.auth_file = auth_file
        self.timeout = timeout
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        self.instances.append(self)

    def get_messages(self, url_or_id: str, **options: Any) -> list[dict[str, str]]:
        self.calls.append(("get_messages", (url_or_id,), options))
        return [
            {"role": "user", "text": "hello"},
            {"role": "assistant", "content": "hi"},
        ]


class RaisingGpttyClient(FakeGpttyClient):
    def get_messages(self, url_or_id: str, **options: Any) -> list[dict[str, str]]:
        raise RuntimeError("backend unavailable")


def make_args(tmp_path: Path, **overrides: Any) -> Namespace:
    values: dict[str, Any] = {
        "url_or_id": None,
        "state": str(tmp_path / "gptty_state.json"),
        "auth": "auth_data.json",
        "timeout": 90,
        "last": None,
        "format": "markdown",
        "output": None,
        "overwrite": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_export_prints_explicit_conversation_as_markdown(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    stdout = StringIO()

    result = run_export(
        make_args(tmp_path, url_or_id="conversation-123"),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    assert result == 0
    assert stdout.getvalue() == "### user\n\nhello\n\n### assistant\n\nhi\n"
    assert FakeGpttyClient.instances[0].calls == [
        ("get_messages", ("conversation-123",), {}),
    ]


def test_export_uses_attached_conversation_and_last_limit(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-456"))

    result = run_export(
        make_args(
            tmp_path,
            last=5,
            auth="custom_auth.json",
            timeout=12,
        ),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    assert result == 0
    client = FakeGpttyClient.instances[0]
    assert client.auth_file == "custom_auth.json"
    assert client.timeout == 12
    assert client.calls == [("get_messages", ("attached-456",), {"limit": 5})]


def test_export_requires_explicit_or_attached_conversation(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    stderr = StringIO()

    result = run_export(
        make_args(tmp_path),
        client_factory=FakeGpttyClient,
        stderr=stderr,
    )

    assert result == 2
    assert "gptty export requires a conversation URL/id" in stderr.getvalue()
    assert FakeGpttyClient.instances == []


def test_export_supports_json_output(tmp_path: Path) -> None:
    stdout = StringIO()

    result = run_export(
        make_args(tmp_path, url_or_id="conversation-123", format="json"),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    assert result == 0
    assert json.loads(stdout.getvalue()) == {
        "messages": [
            {"created_at": None, "role": "user", "text": "hello"},
            {"created_at": None, "role": "assistant", "text": "hi"},
        ]
    }


def test_export_writes_markdown_to_file(tmp_path: Path) -> None:
    output_path = tmp_path / "conversation.md"

    result = run_export(
        make_args(tmp_path, url_or_id="conversation-123", output=str(output_path)),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    assert result == 0
    assert output_path.read_text(encoding="utf-8") == "### user\n\nhello\n\n### assistant\n\nhi\n"


def test_export_refuses_to_overwrite_existing_file_by_default(tmp_path: Path) -> None:
    output_path = tmp_path / "conversation.md"
    output_path.write_text("existing\n", encoding="utf-8")
    stderr = StringIO()

    result = run_export(
        make_args(tmp_path, url_or_id="conversation-123", output=str(output_path)),
        client_factory=FakeGpttyClient,
        stderr=stderr,
    )

    assert result == 1
    assert output_path.read_text(encoding="utf-8") == "existing\n"
    assert "output file already exists" in stderr.getvalue()


def test_export_allows_overwrite(tmp_path: Path) -> None:
    output_path = tmp_path / "conversation.md"
    output_path.write_text("existing\n", encoding="utf-8")

    result = run_export(
        make_args(
            tmp_path,
            url_or_id="conversation-123",
            output=str(output_path),
            overwrite=True,
        ),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    assert result == 0
    assert output_path.read_text(encoding="utf-8") == "### user\n\nhello\n\n### assistant\n\nhi\n"


def test_export_returns_1_on_sdk_error(tmp_path: Path) -> None:
    stderr = StringIO()

    result = run_export(
        make_args(tmp_path, url_or_id="conversation-123"),
        client_factory=RaisingGpttyClient,
        stderr=stderr,
    )

    assert result == 1
    assert "export request failed: backend unavailable" in stderr.getvalue()


def test_export_returns_1_on_state_error(tmp_path: Path) -> None:
    state_path = tmp_path / "gptty_state.json"
    state_path.write_text("[]", encoding="utf-8")
    stderr = StringIO()

    result = run_export(
        make_args(tmp_path, state=str(state_path)),
        client_factory=FakeGpttyClient,
        stderr=stderr,
    )

    assert result == 1
    assert "failed to load state" in stderr.getvalue()


def test_export_returns_1_on_file_write_error(tmp_path: Path) -> None:
    stderr = StringIO()

    result = run_export(
        make_args(
            tmp_path,
            url_or_id="conversation-123",
            output=str(tmp_path),
            overwrite=True,
        ),
        client_factory=FakeGpttyClient,
        stderr=stderr,
    )

    assert result == 1
    assert "failed to write export" in stderr.getvalue()
