from __future__ import annotations

from io import StringIO

from gptty.runs import read_run_events, read_run_summary, render_run_status, start_run


def test_start_run_writes_summary_and_events(tmp_path) -> None:
    recorder = start_run(
        profile="work",
        state_path=tmp_path / "gptty_state.json",
        command="send",
        conversation_ref="conv-1",
    )
    recorder.event("prompt_sent")
    recorder.event("token_delta", text="hello")
    recorder.complete()

    summary = read_run_summary(recorder.run_file)
    events = read_run_events(recorder.events_file, from_start=True)

    assert summary["profile"] == "work"
    assert summary["command"] == "send"
    assert summary["conversation_ref"] == "conv-1"
    assert summary["status"] == "completed"
    assert [event["type"] for event in events] == [
        "run_started",
        "prompt_sent",
        "token_delta",
        "completed",
    ]


def test_render_run_status_includes_recent_text(tmp_path) -> None:
    recorder = start_run(
        profile=None,
        state_path=tmp_path / "gptty_state.json",
        command="send",
        conversation_ref="conv-1",
    )
    recorder.event("token_delta", text="hello")
    stdout = StringIO()

    render_run_status(
        summary=read_run_summary(recorder.run_file),
        events=read_run_events(recorder.events_file, from_start=True),
        stdout=stdout,
    )

    output = stdout.getvalue()
    assert "gptty: conversation in progress" in output
    assert "Profile: local files" in output
    assert "Conversation: conv-1" in output
    assert "Assistant:" in output
    assert "hello" in output


def test_render_run_status_only_omits_text(tmp_path) -> None:
    recorder = start_run(
        profile=None,
        state_path=tmp_path / "gptty_state.json",
        command="send",
        conversation_ref="conv-1",
    )
    recorder.event("token_delta", text="hello")
    stdout = StringIO()

    render_run_status(
        summary=read_run_summary(recorder.run_file),
        events=read_run_events(recorder.events_file, from_start=True),
        stdout=stdout,
        status_only=True,
    )

    output = stdout.getvalue()
    assert "Status: running" in output
    assert "Assistant:" not in output
    assert "hello" not in output
