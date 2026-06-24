from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from ..sdk_client import GpttyClient
from ..state import ChatState, StateError, load_chat_state, save_chat_state

CHAT_HELP = """Commands:
  /help        Show this help
  /new         Start a new chat state
  /exit        Exit chat
  /quit        Exit chat
"""

CONVERSATION_REF_FIELDS = (
    "conversation_id",
    "conversation_url",
    "conversation_ref",
    "url",
    "id",
)


def extract_conversation_ref(response: Any) -> str | None:
    if isinstance(response, dict):
        for field in CONVERSATION_REF_FIELDS:
            value = response.get(field)
            if value:
                return str(value)

    for field in CONVERSATION_REF_FIELDS:
        value = getattr(response, field, None)
        if value:
            return str(value)

    return None


def response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text is not None:
        return str(text)
    if isinstance(response, dict):
        for field in ("text", "message", "content"):
            value = response.get(field)
            if value is not None:
                return str(value)
    if response is None:
        return ""
    return str(response)


def run_chat(
    args: Any,
    *,
    client_factory: Callable[..., Any] = GpttyClient,
    input_stream: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    state_path = Path(getattr(args, "state", "gptty_state.json"))
    try:
        state = load_chat_state(state_path)
    except StateError as exc:
        print(f"gptty: {exc}", file=stderr)
        return 1

    model = getattr(args, "model", None)
    if model and model != state.model:
        state.model = model
        try:
            save_chat_state(state_path, state)
        except StateError as exc:
            print(f"gptty: {exc}", file=stderr)
            return 1

    client = client_factory(
        auth_file=getattr(args, "auth", "auth_data.json"),
        timeout=getattr(args, "timeout", 90),
    )
    interactive = _is_interactive(input_stream)

    while True:
        if interactive:
            print("> ", end="", file=stdout, flush=True)

        try:
            line = input_stream.readline()
        except KeyboardInterrupt:
            print(file=stdout)
            return 130

        if line == "":
            if interactive:
                print(file=stdout)
            return 0

        prompt = line.strip()
        if not prompt:
            continue

        if prompt.startswith("/"):
            result = _handle_chat_command(prompt, state=state, state_path=state_path, stdout=stdout, stderr=stderr)
            if result is not None:
                return result
            continue

        code = _send_chat_prompt(
            client,
            state=state,
            state_path=state_path,
            prompt=prompt,
            model=state.model,
            stream=not bool(getattr(args, "no_stream", False)),
            stdout=stdout,
            stderr=stderr,
        )
        if code != 0:
            return code


def _handle_chat_command(
    command: str,
    *,
    state: ChatState,
    state_path: Path,
    stdout: TextIO,
    stderr: TextIO,
) -> int | None:
    if command in {"/exit", "/quit"}:
        return 0
    if command == "/help":
        print(CHAT_HELP.rstrip(), file=stdout)
        return None
    if command == "/new":
        state.current_conversation = None
        try:
            save_chat_state(state_path, state)
        except StateError as exc:
            print(f"gptty: {exc}", file=stderr)
            return 1
        print("Started a new chat.", file=stdout)
        return None

    print(f"Unknown command: {command}. Type /help for available commands.", file=stderr)
    return None


def _send_chat_prompt(
    client: Any,
    *,
    state: ChatState,
    state_path: Path,
    prompt: str,
    model: str | None,
    stream: bool,
    stdout: TextIO,
    stderr: TextIO,
) -> int:
    saw_stream_token = False

    def on_token(token: str) -> None:
        nonlocal saw_stream_token
        saw_stream_token = True
        print(token, end="", file=stdout, flush=True)

    options: dict[str, Any] = {"stream": stream}
    if model:
        options["model"] = model
    if stream:
        options["on_token"] = on_token

    try:
        if state.current_conversation:
            response = client.send_to_conversation(state.current_conversation, prompt, **options)
        else:
            response = client.send(prompt, **options)
    except Exception as exc:  # noqa: BLE001 - command boundary converts SDK errors to exit codes.
        print(f"gptty: chat request failed: {exc}", file=stderr)
        return 1

    if stream:
        if saw_stream_token:
            print(file=stdout)
        else:
            print(response_text(response), file=stdout)
    else:
        print(response_text(response), file=stdout)

    conversation_ref = extract_conversation_ref(response)
    if conversation_ref and conversation_ref != state.current_conversation:
        state.current_conversation = conversation_ref
        try:
            save_chat_state(state_path, state)
        except StateError as exc:
            print(f"gptty: {exc}", file=stderr)
            return 1

    return 0


def _is_interactive(input_stream: TextIO) -> bool:
    try:
        return input_stream.isatty()
    except OSError:
        return False
