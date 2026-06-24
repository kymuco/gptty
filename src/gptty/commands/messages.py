from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TextIO

from ..sdk_client import GpttyClient
from ..state import StateError, load_chat_state

NO_CONVERSATION_ERROR = (
    "gptty messages requires a conversation URL/id or an attached conversation. "
    "Run `gptty attach <url-or-id>` first."
)


@dataclass(frozen=True)
class ChatMessage:
    role: str
    text: str


def run_messages(
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

    options: dict[str, Any] = {}
    last = getattr(args, "last", None)
    if last is not None:
        options["limit"] = int(last)

    try:
        response = client.get_messages(conversation_ref, **options)
    except Exception as exc:  # noqa: BLE001 - command boundary converts SDK errors to exit codes.
        print(f"gptty: messages request failed: {exc}", file=stderr)
        return 1

    print(format_messages(normalize_messages(response)), file=stdout)
    return 0


def resolve_conversation_ref(args: Any) -> str | None:
    explicit = getattr(args, "url_or_id", None)
    if explicit:
        return str(explicit)

    state = load_chat_state(Path(getattr(args, "state", "gptty_state.json")))
    return state.current_conversation


def normalize_messages(response: Any) -> list[ChatMessage]:
    raw_messages = _extract_raw_messages(response)
    return [_normalize_message(message) for message in raw_messages]


def format_messages(messages: list[ChatMessage]) -> str:
    if not messages:
        return "(no messages)"

    blocks = []
    for message in messages:
        blocks.append(f"{message.role}:\n{message.text}".rstrip())
    return "\n\n".join(blocks)


def _extract_raw_messages(response: Any) -> Iterable[Any]:
    if isinstance(response, dict):
        messages = response.get("messages")
        if isinstance(messages, Iterable) and not isinstance(messages, (str, bytes)):
            return messages
    else:
        messages = getattr(response, "messages", None)
        if isinstance(messages, Iterable) and not isinstance(messages, (str, bytes)):
            return messages

    if isinstance(response, Iterable) and not isinstance(response, (str, bytes, dict)):
        return response

    return []


def _normalize_message(message: Any) -> ChatMessage:
    role = _message_field(message, "role", "author", default="message")
    text = _message_field(message, "text", "content", "message", default="")
    return ChatMessage(role=role, text=text)


def _message_field(message: Any, *fields: str, default: str) -> str:
    for field in fields:
        if isinstance(message, dict) and field in message:
            return _stringify_message_value(message[field])
        value = getattr(message, field, None)
        if value is not None:
            return _stringify_message_value(value)
    return default


def _stringify_message_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [_stringify_message_part(part) for part in value]
        return "".join(part for part in parts if part)
    return str(value)


def _stringify_message_part(part: Any) -> str:
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        for field in ("text", "content", "value"):
            value = part.get(field)
            if value is not None:
                return _stringify_message_value(value)
    return str(part)
