from __future__ import annotations

from io import StringIO
from types import SimpleNamespace

from gptty.required_action import maybe_render_required_action, render_required_action


def test_render_required_action_includes_next_step_url() -> None:
    action = SimpleNamespace(
        type="oauth_required",
        reason="missing_link",
        connector_id="connector-gmail",
        domain="call_tool",
        path="/connector-gmail/search_emails",
        actions=("oauth_redirect", "deny"),
    )
    conversation = SimpleNamespace(conversation_id="conv-123")

    rendered = render_required_action(action, conversation=conversation)

    assert "oauth_required" in rendered
    assert "missing_link" in rendered
    assert "connector-gmail" in rendered
    assert "/connector-gmail/search_emails" in rendered
    assert "oauth_redirect, deny" in rendered
    assert "https://chatgpt.com/c/conv-123" in rendered
    assert "retry the command" in rendered


def test_maybe_render_required_action_uses_client_helper() -> None:
    action = SimpleNamespace(type="oauth_required", reason="missing_link")
    response = SimpleNamespace(conversation=SimpleNamespace(conversation_id="conv-123"))
    calls = []
    stderr = StringIO()

    class Client:
        def get_required_action(self, conversation):
            calls.append(conversation)
            return action

    found = maybe_render_required_action(Client(), response, stderr=stderr)

    assert found is True
    assert calls == [response.conversation]
    assert "oauth_required" in stderr.getvalue()
    assert "https://chatgpt.com/c/conv-123" in stderr.getvalue()


def test_maybe_render_required_action_ignores_old_sdk_without_helper() -> None:
    response = SimpleNamespace(conversation=SimpleNamespace(conversation_id="conv-123"))
    stderr = StringIO()

    found = maybe_render_required_action(object(), response, stderr=stderr)

    assert found is False
    assert stderr.getvalue() == ""


def test_maybe_render_required_action_uses_fallback_conversation() -> None:
    action = SimpleNamespace(type="oauth_required", reason="missing_link")
    calls = []
    stderr = StringIO()

    class Client:
        def get_required_action(self, conversation):
            calls.append(conversation)
            return action

    found = maybe_render_required_action(
        Client(),
        SimpleNamespace(text=""),
        stderr=stderr,
        fallback_conversation="conv-fallback",
    )

    assert found is True
    assert calls == ["conv-fallback"]
    assert "https://chatgpt.com/c/conv-fallback" in stderr.getvalue()
