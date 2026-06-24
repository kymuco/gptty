from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, TextIO

from ..locks import conversation_lock_dir, conversation_lock_path, read_conversation_lock
from ..runs import read_run_events, read_run_summary, render_run_status
from ..state import StateError, load_chat_state

NO_CONVERSATION_ERROR = (
    "gptty observe requires a conversation URL/id or an attached conversation. "
    "Run `gptty attach <url-or-id>` first."
)


def run_observe(args: Any, *, stdout: TextIO = sys.stdout, stderr: TextIO = sys.stderr) -> int:
    state_path = Path(getattr(args, "state", "gptty_state.json"))
    try:
        conversation_ref = resolve_conversation_ref(args, state_path=state_path)
    except StateError as exc:
        print(f"gptty: {exc}", file=stderr)
        return 1

    if not conversation_ref:
        print(NO_CONVERSATION_ERROR, file=stderr)
        return 2

    lock_dir = conversation_lock_dir(profile=getattr(args, "profile", None), state_path=state_path)
    lock_path = conversation_lock_path(lock_dir, conversation_ref)
    if not lock_path.exists():
        print("gptty: no active local run for this conversation", file=stdout)
        print(file=stdout)
        if getattr(args, "profile", None):
            print(f"Profile: {getattr(args, 'profile')}", file=stdout)
        print(f"Conversation: {conversation_ref}", file=stdout)
        print(file=stdout)
        print("`gptty observe` can only show runs started by gptty on this machine.", file=stdout)
        return 1

    lock = read_conversation_lock(lock_path, fallback_conversation=conversation_ref)
    if lock.run_file is None:
        print("gptty: active run metadata is not available for this conversation", file=stderr)
        return 1

    summary = read_run_summary(lock.run_file)
    if not summary:
        print("gptty: active run metadata could not be read", file=stderr)
        return 1

    events_file = summary.get("events_file")
    events = read_run_events(
        events_file,
        from_start=bool(getattr(args, "from_start", False)),
    ) if events_file else []
    render_run_status(
        summary=summary,
        events=events,
        stdout=stdout,
        status_only=bool(getattr(args, "status_only", False)),
    )
    return 0


def resolve_conversation_ref(args: Any, *, state_path: Path) -> str | None:
    explicit = getattr(args, "url_or_id", None)
    if explicit:
        return str(explicit)

    state = load_chat_state(state_path)
    return state.current_conversation
