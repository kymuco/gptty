from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

OutputFormat = Literal["plain", "json", "markdown"]

CONVERSATION_FIELDS = (
    "conversation_url",
    "conversation_id",
    "conversation_ref",
    "current_conversation",
    "url",
    "id",
)


@dataclass(frozen=True)
class OutputMessage:
    role: str
    text: str
    created_at: str | None = None


def normalize_messages(response: Any) -> list[OutputMessage]:
    raw_messages = _extract_raw_messages(response)
    return [_normalize_message(message) for message in raw_messages]


def render_messages(messages: list[OutputMessage], output_format: OutputFormat = "plain") -> str:
    if output_format == "plain":
        return _render_messages_plain(messages)
    if output_format == "json":
        return _json_dump({"messages": [asdict(message) for message in messages]})
    if output_format == "markdown":
        return _render_messages_markdown(messages)
    raise ValueError(f"Unsupported output format: {output_format}")


def normalize_status(response: Any, *, conversation: str | None = None) -> dict[str, Any]:
    if isinstance(response, str):
        data: dict[str, Any] = {"status": response}
    elif isinstance(response, dict):
        data = dict(response)
    else:
        data = _object_fields(response, ("status", "state", "conversation", *CONVERSATION_FIELDS))
        if not data:
            data = {"status": str(response)}

    if conversation and not _has_conversation(data):
        data["conversation"] = conversation
    return data


def render_status(status: dict[str, Any], output_format: OutputFormat = "plain") -> str:
    if output_format == "plain":
        if set(status) == {"status"}:
            return str(status["status"])
        return "\n".join(f"{key}: {_plain_value(value)}" for key, value in status.items())
    if output_format == "json":
        return _json_dump(status)
    if output_format == "markdown":
        return _render_mapping_markdown(status)
    raise ValueError(f"Unsupported output format: {output_format}")


def normalize_response(response: Any, *, conversation: str | None = None) -> dict[str, Any]:
    text = _response_text(response)
    response_conversation = _conversation_ref(response) or conversation
    data: dict[str, Any] = {"text": text}
    if response_conversation:
        data["conversation"] = response_conversation
    return data


def render_response(response: dict[str, Any], output_format: OutputFormat = "plain") -> str:
    if output_format == "plain":
        return str(response.get("text", ""))
    if output_format == "json":
        return _json_dump(response)
    if output_format == "markdown":
        return str(response.get("text", ""))
    raise ValueError(f"Unsupported output format: {output_format}")


def _extract_raw_messages(response: Any) -> list[Any]:
    messages = _field(response, "messages")
    if isinstance(messages, list):
        return messages
    if messages is not None and _is_iterable_messages(messages):
        return list(messages)
    if isinstance(response, list):
        return response
    if _is_iterable_messages(response):
        return list(response)
    return []


def _normalize_message(message: Any) -> OutputMessage:
    role = _message_field(message, "role", "author", default="message")
    text = _message_field(message, "text", "content", "message", default="")
    created_at = _message_field(message, "created_at", "create_time", "timestamp", default="") or None
    return OutputMessage(role=role, text=text, created_at=created_at)


def _message_field(message: Any, *fields: str, default: str) -> str:
    for field in fields:
        value = _field(message, field)
        if value is not None:
            return _stringify_message_value(value)
    return default


def _field(value: Any, field: str) -> Any:
    if isinstance(value, dict):
        return value.get(field)
    return getattr(value, field, None)


def _object_fields(value: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in fields:
        field_value = getattr(value, field, None)
        if field_value is not None:
            data[field] = field_value
    return data


def _response_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    for field in ("text", "message", "content"):
        value = _field(response, field)
        if value is not None:
            return _stringify_message_value(value)
    if response is None:
        return ""
    return str(response)


def _conversation_ref(response: Any) -> str | None:
    for field in CONVERSATION_FIELDS:
        value = _field(response, field)
        if value:
            return str(value)
    return None


def _has_conversation(data: dict[str, Any]) -> bool:
    return any(key in data and data[key] for key in ("conversation", *CONVERSATION_FIELDS))


def _render_messages_plain(messages: list[OutputMessage]) -> str:
    if not messages:
        return "(no messages)"
    return "\n\n".join(f"{message.role}:\n{message.text}".rstrip() for message in messages)


def _render_messages_markdown(messages: list[OutputMessage]) -> str:
    if not messages:
        return "_No messages._"
    blocks = []
    for message in messages:
        blocks.append(f"### {message.role}\n\n{message.text}".rstrip())
    return "\n\n".join(blocks)


def _render_mapping_markdown(data: dict[str, Any]) -> str:
    lines = ["| Field | Value |", "|---|---|"]
    for key, value in data.items():
        lines.append(f"| {key} | {_markdown_table_value(value)} |")
    return "\n".join(lines)


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


def _plain_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(_to_jsonable(value), ensure_ascii=False, sort_keys=True)
    return str(value)


def _markdown_table_value(value: Any) -> str:
    rendered = _plain_value(value)
    return rendered.replace("|", "\\|").replace("\n", "<br>")


def _json_dump(value: Any) -> str:
    return json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2, sort_keys=True)


def _to_jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "__dict__"):
        return _to_jsonable(vars(value))
    return str(value)


def _is_iterable_messages(value: Any) -> bool:
    if isinstance(value, (str, bytes, dict)):
        return False
    try:
        iter(value)
    except TypeError:
        return False
    return True
