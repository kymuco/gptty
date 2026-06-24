from __future__ import annotations

from argparse import Namespace
from io import StringIO
from typing import Any

from gptty.commands.status import format_status, run_status
from gptty.state import ChatState, save_chat_state


class StatusObject:
    def __init__(self, status: str) -> None:
        self.status = status


class FakeGpttyClient:
    instances: list["FakeGpttyClient"] = []

    def __init__(self, auth_file: str = "auth_data.json", timeout: int = 90) -> None:
        self.auth_file = auth_file
        self.timeout = timeout
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        FakeGpttyClient.instances.append(self)

    def get_status(self, url_or_id: str, **options: Any) -> dict[str, str]:
        self.calls.append(("get_status", (url_or_id,), options))
        return {"status": "completed"}


def make_args(tmp_path, **overrides: Any) -> Namespace:
    values = {
        "url_or_id": None,
        "state": str(tmp_path / "gptty_state.json"),
        "auth": "auth_data.json",
        "timeout": 90,
    }
    values.update(overrides)
    return Namespace(**values)


def test_status_uses_explicit_ref(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    stdout = StringIO()

    code = run_status(
        make_args(tmp_path, url_or_id="explicit-ref", auth="custom_auth.json", timeout=12),
        client_factory=FakeGpttyClient,
        stdout=stdout,
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.auth_file == "custom_auth.json"
    assert client.timeout == 12
    assert client.calls == [("get_status", ("explicit-ref",), {})]
    assert stdout.getvalue() == "completed\n"


def test_status_uses_attached_state_ref(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    save_chat_state(tmp_path / "gptty_state.json", ChatState(current_conversation="attached-ref"))

    code = run_status(
        make_args(tmp_path),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
    )

    client = FakeGpttyClient.instances[0]
    assert code == 0
    assert client.calls[0] == ("get_status", ("attached-ref",), {})


def test_status_returns_2_without_ref(tmp_path) -> None:
    FakeGpttyClient.instances.clear()
    stderr = StringIO()

    code = run_status(
        make_args(tmp_path),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert code == 2
    assert FakeGpttyClient.instances == []
    assert "requires a conversation" in stderr.getvalue()


def test_status_returns_1_on_state_error(tmp_path) -> None:
    state_path = tmp_path / "bad_state.json"
    state_path.write_text("{", encoding="utf-8")
    stderr = StringIO()

    code = run_status(
        make_args(tmp_path, state=str(state_path)),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=stderr,
    )

    assert code == 1
    assert "failed to load state" in stderr.getvalue()


def test_format_status_handles_dict_object_and_string() -> None:
    assert format_status({"status": "running"}) == "running"
    assert format_status({"status": "running", "idle": False}) == "status: running\nidle: False"
    assert format_status(StatusObject("completed")) == "completed"
    assert format_status("queued") == "queued"
