from __future__ import annotations

from argparse import Namespace
from io import StringIO
from pathlib import Path
from typing import Any

from gptty.commands.send import run_send
from gptty.runs import read_run_events, read_run_summary
from gptty.state import ChatState, save_chat_state


class Response:
    text = "reply"
    conversation_id = "conv-1"


class FakeGpttyClient:
    instances: list["FakeGpttyClient"] = []

    def __init__(self, auth_file: str = "auth_data.json", timeout: int = 90) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []
        FakeGpttyClient.instances.append(self)

    def send_to_conversation(self, conversation_ref: str, prompt: str, **options: Any) -> Response:
        self.calls.append(("send_to_conversation", (conversation_ref, prompt), options))
        on_token = options.get("on_token")
        if on_token is not None:
            on_token("hello")
        return Response()


def make_args(tmp_path: Path, **overrides: Any) -> Namespace:
    values = {
        "prompt": ["continue"],
        "to": None,
        "new": False,
        "state": str(tmp_path / "gptty_state.json"),
        "auth": "auth_data.json",
        "profile": None,
        "timeout": 90,
        "model": None,
        "no_stream": False,
        "format": "plain",
        "image": [],
        "wait_lock": False,
        "lock_timeout": None,
    }
    values.update(overrides)
    return Namespace(**values)


def test_send_writes_run_events_for_attached_conversation(tmp_path: Path) -> None:
    state_path = tmp_path / "gptty_state.json"
    save_chat_state(state_path, ChatState(current_conversation="conv-1"))

    code = run_send(
        make_args(tmp_path),
        client_factory=FakeGpttyClient,
        stdout=StringIO(),
        stderr=StringIO(),
    )

    assert code == 0
    run_files = list((tmp_path / ".gptty_runs").glob("*.json"))
    assert len(run_files) == 1
    summary = read_run_summary(run_files[0])
    events = read_run_events(summary["events_file"], from_start=True)
    assert summary["status"] == "completed"
    assert [event["type"] for event in events] == [
        "run_started",
        "prompt_sent",
        "waiting_for_reply",
        "token_delta",
        "completed",
    ]
    assert events[3]["text"] == "hello"
