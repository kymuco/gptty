from __future__ import annotations

from typing import Any, TextIO

CONVERSATION_FIELDS = (
    "conversation_url",
    "conversation_id",
    "conversation_ref",
    "current_conversation",
    "url",
    "id",
)


def maybe_render_required_action(
    client: Any,
    response: Any,
    *,
    stderr: TextIO,
    fallback_conversation: Any = None,
) -> bool:
    """Render SDK required-action state when available.

    Returns True when a required action was found and printed. The helper is
    deliberately compatible with older chatgpt-web-adapter releases where
    get_required_action does not exist yet.
    """

    get_required_action = getattr(client, "get_required_action", None)
    if not callable(get_required_action):
        return False

    conversation = _conversation_from_response(response) or fallback_conversation
    if not conversation:
        return False

    try:
        action = get_required_action(conversation)
    except Exception:
        return False

    if action is None:
        return False

    print(render_required_action(action, conversation=conversation), file=stderr)
    return True


def render_required_action(action: Any, *, conversation: Any = None) -> str:
    action_type = _field(action, "type") or "required_action"
    reason = _field(action, "reason")
    connector_id = _field(action, "connector_id")
    domain = _field(action, "domain")
    path = _field(action, "path")
    actions = _field(action, "actions")

    lines = [
        f"gptty: ChatGPT requires a web UI action before it can continue ({action_type}).",
    ]
    if reason:
        lines.append(f"reason: {reason}")
    if connector_id:
        lines.append(f"connector: {connector_id}")
    if domain:
        lines.append(f"domain: {domain}")
    if path:
        lines.append(f"requested path: {path}")
    normalized_actions = _actions_text(actions)
    if normalized_actions:
        lines.append(f"available actions: {normalized_actions}")

    conversation_url = _conversation_url(conversation)
    if conversation_url:
        lines.extend(
            [
                "next step: open this conversation in ChatGPT web and complete the card there:",
                f"  {conversation_url}",
            ]
        )
    else:
        lines.append("next step: open this conversation in ChatGPT web and complete the required card there.")

    lines.append("then retry the command, or ask again without that connector/tool.")
    return "\n".join(lines)


def _conversation_from_response(response: Any) -> Any:
    conversation = _field(response, "conversation")
    if conversation:
        return conversation
    for field in CONVERSATION_FIELDS:
        value = _field(response, field)
        if value:
            return value
    return None


def _conversation_url(conversation: Any) -> str | None:
    if isinstance(conversation, str):
        if conversation.startswith(("http://", "https://")):
            return conversation
        return f"https://chatgpt.com/c/{conversation}"

    conversation_id = _field(conversation, "conversation_id") or _field(conversation, "id")
    if conversation_id:
        return f"https://chatgpt.com/c/{conversation_id}"
    return None


def _field(value: Any, field: str) -> Any:
    if isinstance(value, dict):
        return value.get(field)
    return getattr(value, field, None)


def _actions_text(actions: Any) -> str:
    if isinstance(actions, str):
        return actions
    if isinstance(actions, (list, tuple)):
        values = [str(action) for action in actions if action]
        return ", ".join(values)
    return ""
