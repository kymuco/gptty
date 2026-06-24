from __future__ import annotations

from pathlib import Path

from gptty.sdk_client import GpttyClient


class FakeSdkClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def send(self, prompt: str, **options: object) -> str:
        self.calls.append(("send", (prompt,), options))
        return "send-result"

    def send_to_conversation(
        self,
        url_or_id: object,
        prompt: str,
        **options: object,
    ) -> str:
        self.calls.append(("send_to_conversation", (url_or_id, prompt), options))
        return "send-to-conversation-result"

    def attach_conversation(self, url_or_id: object, **options: object) -> str:
        self.calls.append(("attach_conversation", (url_or_id,), options))
        return "attach-result"

    def get_messages(self, url_or_id: object, **options: object) -> str:
        self.calls.append(("get_messages", (url_or_id,), options))
        return "messages-result"

    def get_status(self, url_or_id: object, **options: object) -> str:
        self.calls.append(("get_status", (url_or_id,), options))
        return "status-result"

    def wait_until_completed(self, url_or_id: object, **options: object) -> str:
        self.calls.append(("wait_until_completed", (url_or_id,), options))
        return "wait-result"


def test_gptty_client_keeps_auth_and_timeout() -> None:
    sdk = FakeSdkClient()

    client = GpttyClient(auth_file="custom_auth.json", timeout=123, sdk_client=sdk)

    assert client.auth_file == Path("custom_auth.json")
    assert client.timeout == 123


def test_send_delegates_to_sdk_client() -> None:
    sdk = FakeSdkClient()
    client = GpttyClient(sdk_client=sdk)

    result = client.send("hello", model="gpt-4o-mini", stream=True)

    assert result == "send-result"
    assert sdk.calls == [
        ("send", ("hello",), {"model": "gpt-4o-mini", "stream": True})
    ]


def test_conversation_methods_delegate_to_sdk_client() -> None:
    sdk = FakeSdkClient()
    client = GpttyClient(sdk_client=sdk)

    assert client.attach_conversation("abc") == "attach-result"
    assert client.send_to_conversation("abc", "continue", preserve_model=True) == (
        "send-to-conversation-result"
    )
    assert client.get_messages("abc", limit=5) == "messages-result"
    assert client.get_status("abc") == "status-result"
    assert client.wait_until_completed("abc", timeout=30) == "wait-result"

    assert sdk.calls == [
        ("attach_conversation", ("abc",), {}),
        (
            "send_to_conversation",
            ("abc", "continue"),
            {"preserve_model": True},
        ),
        ("get_messages", ("abc",), {"limit": 5}),
        ("get_status", ("abc",), {}),
        ("wait_until_completed", ("abc",), {"timeout": 30}),
    ]
