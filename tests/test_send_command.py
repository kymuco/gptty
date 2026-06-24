from __future__ import annotations

import json
from argparse import Namespace
from io import StringIO
from pathlib import Path
from typing import Any

from gptty.commands.send import extract_conversation_ref, run_send
from gptty.state import ChatState, load_chat_state, save_chat_state


class Response:
    def __init__(self, text: str = "reply", conversation_id: str | None = "conv-1") -> None:
        self.text = text
        self.conversation_id = conversation_id


class FakeGpttyClient:
    instances: list["FakeGpttyClient"] = []

    def __init__(self, auth_file: str = "auth_data.json", timeout: int = 90) -> None:
        self.auth_file = auth_file
        self.timeout = timeout
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        FakeGpttyClient.instances.append(self)

    def send(self, prompt: str, **options: Any) -> Response:
        self.calls.append(("send", (prompt,), options))
        on_token = options.get("on_token")
        if on_token is not None:
            on_token("new reply")
        return Response(text="new reply", conversation_id="new-conv")

    def send_to_conversation(self, conversation_ref: str, prompt: str, **options: Any) -> Response:
        self.calls.append(("send_to_conversation", (conversation_ref, prompt), options))
        on_token = options.get("on_token")
        if on_token is not None:
            on_token("reply")
        return Response(text="reply", conversation_id=conversation_ref)


def make_args(tmp_path: Path, **overrides: Any) -> Namespace:
    values = {
        "prompt": ["continue"],
        "stdin_mode": "auto",
        "to": None,
        "new": False,
        "state": str(tmp_path / "gptty_state.json"),
        "auth": "auth_data.json",
        "timeout": 90,
        "model": None,
        "no_stream": True,
        "format": "plain",
        "image": [],
    }
    values.update(overrides)
    return Namespace(**values)


def test_send_uses_attached_conversation_by_default(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-ref"))
    stdout = StringIO()

    code = run_send(
        make_args(tmp_path, auth="custom_auth.json", timeout=12),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.auth_file == "custom_auth.json"
    assert client.timeout == 12
    assert client.calls == [
        ("send_to_conversation", ("attached-ref", "continue"), {"stream": False}),
    ]
    assert stdout.getvalue() == "reply\n"
    assert load_chat_state(tmp_path / "gptty_state.json").current_conversation == "attached-ref"


def test_send_to_explicit_conversation_updates_state(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    stdout = StringIO()

    code = run_send(
        make_args(tmp_path, to="explicit-ref", model="gpt-4o"),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    state = load_chat_state(tmp_path / "gptty_state.json")
    assert code == 0
    assert client.calls == [
        (
            "send_to_conversation",
            ("explicit-ref", "continue"),
            {"stream": False, "model": "gpt-4o"},
        ),
    ]
    assert state.current_conversation == "explicit-ref"
    assert state.model == "gpt-4o"


def test_send_passes_image_media_to_attached_conversation(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-ref"))
    image_path = tmp_path / "ui.png"
    image_path.write_bytes(b"fake image")

    code = run_send(
        make_args(tmp_path, image=[str(image_path)]),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls == [
        (
            "send_to_conversation",
            ("attached-ref", "continue"),
            {"stream": False, "media": [str(image_path)]},
        ),
    ]


def test_send_passes_remote_image_media_to_explicit_conversation(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()

    code = run_send(
        make_args(
            tmp_path,
            to="explicit-ref",
            image=["https://example.com/chart.webp"],
        ),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls == [
        (
            "send_to_conversation",
            ("explicit-ref", "continue"),
            {"stream": False, "media": ["https://example.com/chart.webp"]},
        ),
    ]


def test_send_passes_multiple_images_to_new_conversation(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    first = tmp_path / "before.png"
    second = tmp_path / "after.png"
    first.write_bytes(b"first")
    second.write_bytes(b"second")

    code = run_send(
        make_args(tmp_path, new=True, image=[str(first), str(second)]),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls[0] == (
        "send",
        ("continue",),
        {"stream": False, "media": [str(first), str(second)]},
    )


def test_send_returns_2_for_missing_local_image(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-ref"))
    stderr = StringIO()

    code = run_send(
        make_args(tmp_path, image=[str(tmp_path / "missing.png")]),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert code == 2
    assert FakeGpttyClient.instances == []
    assert "image file does not exist" in stderr.getvalue()


def test_send_json_format_forces_non_streaming_response(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-ref"))
    stdout = StringIO()

    code = run_send(
        make_args(tmp_path, no_stream=False, format="json"),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls == [
        ("send_to_conversation", ("attached-ref", "continue"), {"stream": False}),
    ]
    assert json.loads(stdout.getvalue()) == {
        "text": "reply",
        "conversation": "attached-ref",
    }


def test_send_markdown_format_forces_non_streaming_response(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-ref"))
    stdout = StringIO()

    code = run_send(
        make_args(tmp_path, no_stream=False, format="markdown"),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls == [
        ("send_to_conversation", ("attached-ref", "continue"), {"stream": False}),
    ]
    assert stdout.getvalue() == "reply\n"


def test_send_new_starts_new_conversation_and_saves_ref(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    stdout = StringIO()

    code = run_send(
        make_args(tmp_path, new=True, prompt=["start"], no_stream=False),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert stdout.getvalue() == "new reply\n"
    assert client.calls[0][0] == "send"
    assert client.calls[0][1] == ("start",)
    assert client.calls[0][2]["stream"] is True
    assert callable(client.calls[0][2]["on_token"])
    assert load_chat_state(tmp_path / "gptty_state.json").current_conversation == "new-conv"


def test_send_combines_stdin_and_prompt(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-ref"))

    code = run_send(
        make_args(tmp_path, prompt=["review", "this"]),
        stdin_text="diff --git",
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls[0][1] == (
        "attached-ref",
        "diff --git\n\nUser prompt:\nreview this",
    )


def test_send_returns_2_without_attached_conversation(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    stderr = StringIO()

    code = run_send(
        make_args(tmp_path),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert code == 2
    assert FakeGpttyClient.instances == []
    assert "requires an attached conversation" in stderr.getvalue()


def test_send_returns_2_for_empty_prompt(tmp_path: Path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-ref"))
    stderr = StringIO()

    code = run_send(
        make_args(tmp_path, prompt=[]),
        stdin_text="  \n",
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert code == 2
    assert FakeGpttyClient.instances == []
    assert "requires a prompt" in stderr.getvalue()


def test_send_returns_1_on_state_error(tmp_path: Path) -> None:
    state_path = tmp_path / "bad_state.json"
    state_path.write_text("{", encoding="utf-8")
    stderr = StringIO()

    code = run_send(
        make_args(tmp_path, state=str(state_path)),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert code == 1
    assert "failed to load state" in stderr.getvalue()


def test_extract_conversation_ref_uses_response_then_fallback() -> None:
    assert extract_conversation_ref({"conversation_url": "https://chatgpt.com/c/abc"}) == (
        "https://chatgpt.com/c/abc"
    )
    assert extract_conversation_ref(Response(conversation_id="abc"), fallback="fallback") == "abc"
    assert extract_conversation_ref(object(), fallback="fallback") == "fallback"
    assert extract_conversation_ref(object()) is None
