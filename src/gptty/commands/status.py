from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from ..output import OutputFormat, normalize_status, render_status
from ..sdk_client import GpttyClient
from ..state import StateError, load_chat_state

NO_CONVERSATION_ERROR = (
    "gptty status requires a conversation URL/id or an attached conversation. "
    "Run `gptty attach <url-or-id>` first."
)


def run_status(
    args: Any,
    *,
    client_factory: Callable[..., Any] = GpttyClient,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    try:
        conversation_ref = resolve_conversation_ref(args)
    except StateError as exc:
        print(f"gptty: {exc}", file=stderr)
        return 1

    if not conversation_ref:
        print(NO_CONVERSATION_ERROR, file=stderr)
        return 2

    client = client_factory(
        auth_file=getattr(args, "auth", "auth_data.json"),
        timeout=getattr(args, "timeout", 90),
    )

    try:
        response = client.get_status(conversation_ref)
    except Exception as exc:  # noqa: BLE001 - command boundary converts SDK errors to exit codes.
        print(f"gptty: status request failed: {exc}", file=stderr)
        return 1

    output_format: OutputFormat = getattr(args, "format", "plain")
    print(render_status(normalize_status(response, conversation=conversation_ref), output_format), file=stdout)
    return 0


def resolve_conversation_ref(args: Any) -> str | None:
    explicit = getattr(args, "url_or_id", None)
    if explicit:
        return str(explicit)

    state = load_chat_state(Path(getattr(args, "state", "gptty_state.json")))
    return state.current_conversation


def format_status(response: Any) -> str:
    return render_status(normalize_status(response), "plain")
