from __future__ import annotations

from argparse import Namespace
from io import StringIO
from typing import Any

from gptty.commands.messages import ChatMessage, format_messages, normalize_messages, run_messages
from gptty.state import ChatState, save_chat_state


class MessageObject:
    def __init__(self, role: str, text: str) -> None:
        self.role = role
        self.text = text


class ResponseWithMessages:
    def __init__(self, messages: list[object]) -> None:
        self.messages = messages


class FakeGpttyClient:
    instances: list["FakeGpttyClient"] = []

    def __init__(self, auth_file: str = "auth_data.json", timeout: int = 90) -> None:
        self.auth_file = auth_file
        self.timeout = timeout
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        FakeGpttyClient.instances.append(self)

    def get_messages(self, url_or_id: str, **options: Any) -> list[dict[str, str]]:
        self.calls.append(("get_messages", (url_or_id,), options))
        return [
            {"role": "user", "text": "hello"},
            {"role": "assistant", "content": "hi"},
        ]


def make_args(tmp_path, **overrides: Any) -> Namespace:
    values = {
        "url_or_id": None,
        "state": str(tmp_path / "gptty_state.json"),
        "auth": "auth_data.json",
        "timeout": 90,
        "last": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_messages_uses_explicit_ref_and_last_limit(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    stdout = StringIO()

    code = run_messages(
        make_args(
            tmp_path,
            url_or_id="explicit-ref",
            last=5,
            auth="custom_auth.json",
            timeout=12,
        ),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.auth_file == "custom_auth.json"
    assert client.timeout == 12
    assert client.calls == [("get_messages", ("explicit-ref",), {"limit": 5})]
    assert stdout.getvalue() == "user:\nhello\n\nassistant:\nhi\n"


def test_messages_uses_attached_state_ref(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-ref"))

    code = run_messages(
        make_args(tmp_path),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls[0] == ("get_messages", ("attached-ref",), {})


def test_messages_returns_2_without_ref(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    stderr = StringIO()

    code = run_messages(
        make_args(tmp_path),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert code == 2
    assert FakeGpttyClient.instances == []
    assert "requires a conversation" in stderr.getvalue()


def test_messages_returns_1_on_state_error(tmp_path) -> None:
    state_path = tmp_path / "bad_state.json"
    state_path.write_text("{", encoding="utf-8")
    stderr = StringIO()

    code = run_messages(
        make_args(tmp_path, state=str(state_path)),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert code == 1
    assert "failed to load state" in stderr.getvalue()


def test_normalize_messages_handles_response_messages_and_content_parts() -> None:
    response = ResponseWithMessages(
        [
            MessageObject("user", "hello"),
            {"role": "assistant", "content": [{"text": "hi"}, {"text": " there"}]},
        ]
    )

    assert normalize_messages(response) == [
        ChatMessage(role="user", text="hello"),
        ChatMessage(role="assistant", text="hi there"),
    ]


def test_format_messages_handles_empty_list() -> None:
    assert format_messages([]) == "(no messages)"
