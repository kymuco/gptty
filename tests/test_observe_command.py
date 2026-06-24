from __future__ import annotations

from argparse import Namespace
from io import StringIO

from gptty.commands.observe import run_observe
from gptty.locks import acquire_conversation_lock, conversation_lock_dir
from gptty.runs import start_run
from gptty.state import ChatState, save_chat_state


def make_args(tmp_path, **overrides):
    values = {
        "url_or_id": None,
        "state": str(tmp_path / "gptty_state.json"),
        "profile": None,
        "status_only": False,
        "from_start": False,
    }
    values.update(overrides)
    return Namespace(**values)


def test_observe_reports_active_run_for_attached_conversation(tmp_path) -> None:
    state_path = tmp_path / "gptty_state.json"
    save_chat_state(state_path, ChatState(current_conversation="conv-1"))
    recorder = start_run(
        profile=None,
        state_path=state_path,
        command="send",
        conversation_ref="conv-1",
    )
    recorder.event("token_delta", text="hello")
    lock = acquire_conversation_lock(
        conversation_ref="conv-1",
        lock_dir=conversation_lock_dir(profile=None, state_path=state_path),
        command="send",
        run_id=recorder.run_id,
        run_file=recorder.run_file,
    )

    try:
        stdout = StringIO()
        code = run_observe(make_args(tmp_path), stdout=stdout)
    finally:
        lock.release()

    assert code == 0
    output = stdout.getvalue()
    assert "gptty: conversation in progress" in output
    assert "Conversation: conv-1" in output
    assert "Assistant:" in output
    assert "hello" in output


def test_observe_explicit_conversation_without_lock_reports_no_active_run(tmp_path) -> None:
    stdout = StringIO()

    code = run_observe(make_args(tmp_path, url_or_id="conv-1"), stdout=stdout)

    assert code == 1
    assert "no active local run" in stdout.getvalue()
    assert "Conversation: conv-1" in stdout.getvalue()


def test_observe_requires_conversation(tmp_path) -> None:
    stderr = StringIO()

    code = run_observe(make_args(tmp_path), stdout=StringIO(), stderr=stderr)

    assert code == 2
    assert "requires a conversation" in stderr.getvalue()


def test_observe_status_only_omits_assistant_text(tmp_path) -> None:
    state_path = tmp_path / "gptty_state.json"
    save_chat_state(state_path, ChatState(current_conversation="conv-1"))
    recorder = start_run(
        profile=None,
        state_path=state_path,
        command="send",
        conversation_ref="conv-1",
    )
    recorder.event("token_delta", text="hello")
    lock = acquire_conversation_lock(
        conversation_ref="conv-1",
        lock_dir=conversation_lock_dir(profile=None, state_path=state_path),
        command="send",
        run_id=recorder.run_id,
        run_file=recorder.run_file,
    )

    try:
        stdout = StringIO()
        code = run_observe(make_args(tmp_path, status_only=True), stdout=stdout)
    finally:
        lock.release()

    assert code == 0
    output = stdout.getvalue()
    assert "Status: running" in output
    assert "Assistant:" not in output
    assert "hello" not in output
