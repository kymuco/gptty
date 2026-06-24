from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class StateError(RuntimeError):
    """Raised when a gptty state file cannot be loaded or saved."""


@dataclass
class ChatState:
    current_conversation: str | None = None
    model: str | None = None


def default_chat_state() -> ChatState:
    return ChatState()


def load_chat_state(path: str | Path) -> ChatState:
    state_path = Path(path)
    if not state_path.exists():
        return default_chat_state()

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise StateError(f"failed to load state from {state_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise StateError(f"failed to load state from {state_path}: expected JSON object")

    return ChatState(
        current_conversation=_optional_str(data.get("current_conversation")),
        model=_optional_str(data.get("model")),
    )


def save_chat_state(path: str | Path, state: ChatState) -> None:
    state_path = Path(path)
    tmp_path = state_path.with_name(f".{state_path.name}.tmp")
    payload = json.dumps(asdict(state), indent=2, sort_keys=True) + "\n"

    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(state_path)
    except OSError as exc:
        raise StateError(f"failed to save state to {state_path}: {exc}") from exc


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value)
