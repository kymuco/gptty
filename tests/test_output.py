from __future__ import annotations

import json

from gptty.output import (
    OutputMessage,
    normalize_messages,
    normalize_response,
    normalize_status,
    render_messages,
    render_response,
    render_status,
)


class MessageObject:
    def __init__(self, role: str, text: str, created_at: str | None = None) -> None:
        self.role = role
        self.text = text
        self.created_at = created_at


class ResponseWithMessages:
    def __init__(self, messages: list[object]) -> None:
        self.messages = messages


class StatusObject:
    def __init__(self, status: str, conversation_id: str) -> None:
        self.status = status
        self.conversation_id = conversation_id


class TextResponse:
    def __init__(self, text: str, conversation_id: str = "conv-1") -> None:
        self.text = text
        self.conversation_id = conversation_id


def test_render_messages_plain() -> None:
    messages = [
        OutputMessage(role="user", text="hello"),
        OutputMessage(role="assistant", text="hi"),
    ]

    assert render_messages(messages, "plain") == "user:\nhello\n\nassistant:\nhi"


def test_render_messages_json() -> None:
    messages = [OutputMessage(role="user", text="hello", created_at="2026-01-01")]

    assert json.loads(render_messages(messages, "json")) == {
        "messages": [
            {"role": "user", "text": "hello", "created_at": "2026-01-01"},
        ]
    }


def test_render_messages_markdown() -> None:
    messages = [OutputMessage(role="assistant", text="hi")]

    assert render_messages(messages, "markdown") == "### assistant\n\nhi"


def test_normalize_messages_from_response_shapes() -> None:
    response = ResponseWithMessages(
        [
            MessageObject("user", "hello", "2026-01-01"),
            {"role": "assistant", "content": [{"text": "hi"}, {"text": " there"}]},
        ]
    )

    assert normalize_messages(response) == [
        OutputMessage(role="user", text="hello", created_at="2026-01-01"),
        OutputMessage(role="assistant", text="hi there"),
    ]


def test_render_status_plain_json_and_markdown() -> None:
    status = {"status": "completed", "conversation": "conv-1"}

    assert render_status(status, "plain") == "status: completed\nconversation: conv-1"
    assert json.loads(render_status(status, "json")) == status
    assert render_status(status, "markdown") == (
        "| Field | Value |\n|---|---|\n| status | completed |\n| conversation | conv-1 |"
    )


def test_normalize_status_from_string_dict_and_object() -> None:
    assert normalize_status("completed") == {"status": "completed"}
    assert normalize_status({"status": "running"}, conversation="conv-1") == {
        "status": "running",
        "conversation": "conv-1",
    }
    assert normalize_status(StatusObject("completed", "conv-1")) == {
        "status": "completed",
        "conversation_id": "conv-1",
    }


def test_render_response_plain_json_and_markdown() -> None:
    response = {"text": "reply", "conversation": "conv-1"}

    assert render_response(response, "plain") == "reply"
    assert json.loads(render_response(response, "json")) == response
    assert render_response(response, "markdown") == "reply"


def test_normalize_response_from_shapes() -> None:
    assert normalize_response(TextResponse("reply")) == {
        "text": "reply",
        "conversation": "conv-1",
    }
    assert normalize_response({"content": "reply"}, conversation="fallback") == {
        "text": "reply",
        "conversation": "fallback",
    }
    assert normalize_response("reply") == {"text": "reply"}
