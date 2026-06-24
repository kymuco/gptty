from __future__ import annotations

from argparse import Namespace
from io import StringIO
from typing import Any

from gptty.commands.chat import extract_conversation_ref, run_chat
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
            on_token("reply")
        return Response()

    def send_to_conversation(self, conversation_ref: str, prompt: str, **options: Any) -> Response:
        self.calls.append(("send_to_conversation", (conversation_ref, prompt), options))
        on_token = options.get("on_token")
        if on_token is not None:
            on_token("continued")
        return Response(text="continued", conversation_id=conversation_ref)


def make_args(tmp_path, **overrides: Any) -> Namespace:
    values = {
        "state": str(tmp_path / "gptty_state.json"),
        "auth": "auth_data.json",
        "model": None,
        "no_stream": False,
        "timeout": 90,
    }
    values.update(overrides)
    return Namespace(**values)


def test_first_prompt_calls_send_and_persists_conversation(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    stdout = StringIO()

    code = run_chat(
        make_args(tmp_path),
        input_stream=StringIO("hello\n/exit\n"),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert stdout.getvalue() == "reply\n"
    assert client.calls == [
        ("send", ("hello",), {"stream": True, "on_token": client.calls[0][2]["on_token"]}),
    ]
    assert callable(client.calls[0][2]["on_token"])
    assert load_chat_state(tmp_path / "gptty_state.json").current_conversation == "conv-1"


def test_existing_conversation_uses_send_to_conversation(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="conv-1"))

    code = run_chat(
        make_args(tmp_path),
        input_stream=StringIO("continue\n/exit\n"),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls[0][0] == "send_to_conversation"
    assert client.calls[0][1] == ("conv-1", "continue")
    assert client.calls[0][2]["stream"] is True


def test_new_command_clears_conversation(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="conv-1"))
    stdout = StringIO()

    code = run_chat(
        make_args(tmp_path),
        input_stream=StringIO("/new\n/exit\n"),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    assert code == 0
    assert stdout.getvalue() == "Started a new chat.\n"
    assert load_chat_state(tmp_path / "gptty_state.json").current_conversation is None
    assert FakeGpttyClient.instances[0].calls == []


def test_exit_command_returns_zero(tmp_path) -> None:
    FakeGpttyClient.instances.clear()

    code = run_chat(
        make_args(tmp_path),
        input_stream=StringIO("/exit\n"),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    assert code == 0
    assert FakeGpttyClient.instances[0].calls == []


def test_empty_input_is_ignored(tmp_path) -> None:
    FakeGpttyClient.instances.clear()

    code = run_chat(
        make_args(tmp_path),
        input_stream=StringIO("\nhello\n/exit\n"),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert len(client.calls) == 1
    assert client.calls[0][1] == ("hello",)


def test_no_stream_passes_stream_false_and_prints_response_text(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    stdout = StringIO()

    code = run_chat(
        make_args(tmp_path, no_stream=True, model="gpt-4o", timeout=12, auth="custom_auth.json"),
        input_stream=StringIO("hello\n/exit\n"),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.auth_file == "custom_auth.json"
    assert client.timeout == 12
    assert stdout.getvalue() == "reply\n"
    assert client.calls[0] == (
        "send",
        ("hello",),
        {"stream": False, "model": "gpt-4o"},
    )
    assert load_chat_state(tmp_path / "gptty_state.json").model == "gpt-4o"


def test_extract_conversation_ref_reads_dict_and_attributes() -> None:
    assert extract_conversation_ref({"conversation_url": "https://chatgpt.com/c/abc"}) == (
        "https://chatgpt.com/c/abc"
    )
    assert extract_conversation_ref(Response(conversation_id="abc")) == "abc"
    assert extract_conversation_ref(object()) is None
