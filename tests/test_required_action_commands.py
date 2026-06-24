from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

from gptty.commands.ask import run_ask
from gptty.commands.send import run_send
from gptty.state import ChatState, save_chat_state


class RequiredActionClient:
    def __init__(self, *args, **kwargs) -> None:
        self.action = SimpleNamespace(type="oauth_required", reason="missing_link")

    def send(self, prompt: str, **options):
        return SimpleNamespace(
            text="",
            conversation=SimpleNamespace(conversation_id="conv-ask"),
        )

    def send_to_conversation(self, conversation, prompt: str, **options):
        return SimpleNamespace(text="")

    def get_required_action(self, conversation):
        return self.action


def test_ask_renders_required_action_for_empty_response() -> None:
    stdout = StringIO()
    stderr = StringIO()
    args = SimpleNamespace(
        prompt=["latest gmail message"],
        image=[],
        no_stream=True,
        auth="auth_data.json",
        timeout=90,
        model=None,
    )

    exit_code = run_ask(
        args,
        client_factory=RequiredActionClient,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "oauth_required" in stderr.getvalue()
    assert "https://chatgpt.com/c/conv-ask" in stderr.getvalue()


def test_send_renders_required_action_for_attached_conversation(tmp_path) -> None:
    state_path = tmp_path / "state.json"
    save_chat_state(state_path, ChatState(current_conversation="conv-send"))
    stdout = StringIO()
    stderr = StringIO()
    args = SimpleNamespace(
        prompt=["latest gmail message"],
        image=[],
        no_stream=True,
        auth="auth_data.json",
        timeout=90,
        model=None,
        state=str(state_path),
        to=None,
        new=False,
        format="plain",
    )

    exit_code = run_send(
        args,
        client_factory=RequiredActionClient,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "oauth_required" in stderr.getvalue()
    assert "https://chatgpt.com/c/conv-send" in stderr.getvalue()
