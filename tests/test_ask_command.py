from __future__ import annotations

from argparse import Namespace
from io import StringIO
from typing import Any

from gptty.commands.ask import run_ask


class Response:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeGpttyClient:
    instances: list["FakeGpttyClient"] = []

    def __init__(self, auth_file: str = "auth_data.json", timeout: int = 90) -> None:
        self.auth_file = auth_file
        self.timeout = timeout
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        FakeGpttyClient.instances.append(self)

    def send(self, prompt: str, **options: Any) -> Response:
        self.calls.append(("send", prompt, options))
        on_token = options.get("on_token")
        if on_token is not None:
            on_token("hello")
            on_token(" world")
        return Response("hello world")


def make_args(**overrides: Any) -> Namespace:
    values = {
        "prompt": ["explain", "this"],
        "auth": "auth_data.json",
        "model": None,
        "no_stream": True,
        "plain": False,
        "timeout": 90,
    }
    values.update(overrides)
    return Namespace(**values)


def test_run_ask_non_stream_prints_response_text() -> None:
    FakeGpttyClient.instances.clear()
    stdout = StringIO()

    code = run_ask(
        make_args(no_stream=True),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert stdout.getvalue() == "hello world\n"
    assert client.calls == [
        ("send", "explain this", {"stream": False}),
    ]


def test_run_ask_streams_tokens() -> None:
    FakeGpttyClient.instances.clear()
    stdout = StringIO()

    code = run_ask(
        make_args(no_stream=False),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert stdout.getvalue() == "hello world\n"
    assert client.calls[0][2]["stream"] is True
    assert callable(client.calls[0][2]["on_token"])


def test_run_ask_passes_auth_timeout_and_model() -> None:
    FakeGpttyClient.instances.clear()

    code = run_ask(
        make_args(
            auth="custom_auth.json",
            model="gpt-4o-mini",
            timeout=12,
        ),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.auth_file == "custom_auth.json"
    assert client.timeout == 12
    assert client.calls[0][2] == {"stream": False, "model": "gpt-4o-mini"}


def test_run_ask_uses_stdin_as_prompt() -> None:
    FakeGpttyClient.instances.clear()

    code = run_ask(
        make_args(prompt=[]),
        stdin_text="stdin prompt",
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls[0][1] == "stdin prompt"


def test_run_ask_combines_stdin_and_prompt_before_send() -> None:
    FakeGpttyClient.instances.clear()

    code = run_ask(
        make_args(prompt=["review", "this"]),
        stdin_text="diff --git",
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls[0][1] == "diff --git\n\nUser prompt:\nreview this"


def test_run_ask_returns_2_for_empty_prompt() -> None:
    stderr = StringIO()

    code = run_ask(
        make_args(prompt=[]),
        stdin_text="  \n",
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert code == 2
    assert "requires a prompt" in stderr.getvalue()
