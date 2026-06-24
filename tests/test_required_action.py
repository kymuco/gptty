from __future__ import annotations

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


def test_maybe_render_required_action_uses_client_helper(capsys) -> None:
    action = SimpleNamespace(type="oauth_required", reason="missing_link")
    response = SimpleNamespace(conversation=SimpleNamespace(conversation_id="conv-123"))
    calls = []

    class Client:
        def get_required_action(self, conversation):
            calls.append(conversation)
            return action

    found = maybe_render_required_action(Client(), response, stderr=None)

    captured = capsys.readouterr()
    assert found is True
    assert calls == [response.conversation]
    assert "oauth_required" in captured.err
    assert "https://chatgpt.com/c/conv-123" in captured.err


def test_maybe_render_required_action_ignores_old_sdk_without_helper(capsys) -> None:
    response = SimpleNamespace(conversation=SimpleNamespace(conversation_id="conv-123"))

    found = maybe_render_required_action(object(), response, stderr=None)

    captured = capsys.readouterr()
    assert found is False
    assert captured.err == ""


def test_maybe_render_required_action_uses_fallback_conversation(capsys) -> None:
    action = SimpleNamespace(type="oauth_required", reason="missing_link")
    calls = []

    class Client:
        def get_required_action(self, conversation):
            calls.append(conversation)
            return action

    found = maybe_render_required_action(
        Client(),
        SimpleNamespace(text=""),
        stderr=None,
        fallback_conversation="conv-fallback",
    )

    captured = capsys.readouterr()
    assert found is True
    assert calls == ["conv-fallback"]
    assert "https://chatgpt.com/c/conv-fallback" in captured.err
