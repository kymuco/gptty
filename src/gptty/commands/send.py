from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from ..locks import (
    DEFAULT_LOCK_TIMEOUT_SECONDS,
    ConversationLockError,
    acquire_conversation_lock,
    conversation_lock_dir,
    render_lock_error,
    render_lock_timeout,
    render_stale_lock_recovered,
)
from ..media import MediaInputError, collect_media_inputs
from ..output import OutputFormat, normalize_response, render_response
from ..prompt import build_prompt
from ..required_action import maybe_render_required_action
from ..sdk_client import GpttyClient
from ..state import StateError, load_chat_state, save_chat_state

EMPTY_PROMPT_ERROR = "gptty send requires a prompt argument or piped stdin."
NO_CONVERSATION_ERROR = (
    "gptty send requires an attached conversation, `--to <url-or-id>`, or `--new`. "
    "Run `gptty attach <url-or-id>` first."
)

CONVERSATION_REF_FIELDS = (
    "conversation_url",
    "conversation_id",
    "conversation_ref",
    "url",
    "id",
)


def run_send(
    args: Any,
    *,
    stdin_text: str | None = None,
    client_factory: Callable[..., Any] = GpttyClient,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    try:
        prompt = build_prompt(getattr(args, "prompt", []), stdin_text=stdin_text)
    except ValueError:
        print(EMPTY_PROMPT_ERROR, file=stderr)
        return 2

    try:
        media = collect_media_inputs(args)
    except MediaInputError as exc:
        print(f"gptty: {exc}", file=stderr)
        return 2

    state_path = Path(getattr(args, "state", "gptty_state.json"))
    try:
        state = load_chat_state(state_path)
    except StateError as exc:
        print(f"gptty: {exc}", file=stderr)
        return 1

    explicit_ref = getattr(args, "to", None)
    start_new = bool(getattr(args, "new", False))
    conversation_ref = None if start_new else explicit_ref or state.current_conversation

    if not start_new and not conversation_ref:
        print(NO_CONVERSATION_ERROR, file=stderr)
        return 2

    output_format: OutputFormat = getattr(args, "format", "plain")
    stream = not bool(getattr(args, "no_stream", False)) and output_format == "plain"
    saw_stream_token = False

    def on_token(token: str) -> None:
        nonlocal saw_stream_token
        saw_stream_token = True
        print(token, end="", file=stdout, flush=True)

    options: dict[str, Any] = {"stream": stream}
    model = getattr(args, "model", None)
    if model:
        options["model"] = model
    if media:
        options["media"] = media
    if stream:
        options["on_token"] = on_token

    lock = None
    if conversation_ref:
        lock_dir = conversation_lock_dir(profile=getattr(args, "profile", None), state_path=state_path)
        try:
            lock = acquire_conversation_lock(
                conversation_ref=str(conversation_ref),
                lock_dir=lock_dir,
                profile=getattr(args, "profile", None),
                command="send",
                timeout=_lock_timeout(args),
            )
        except ConversationLockError as exc:
            _render_lock_failure(exc, args=args, stderr=stderr)
            return 2
        render_stale_lock_recovered(lock, stderr=stderr)

    try:
        client = client_factory(
            auth_file=getattr(args, "auth", "auth_data.json"),
            timeout=getattr(args, "timeout", 90),
        )

        try:
            if start_new:
                response = client.send(prompt, **options)
            else:
                response = client.send_to_conversation(conversation_ref, prompt, **options)
        except Exception as exc:  # noqa: BLE001 - command boundary converts SDK errors to exit codes.
            print(f"gptty: send request failed: {exc}", file=stderr)
            return 1

        updated_ref = extract_conversation_ref(response, fallback=conversation_ref)
        normalized = normalize_response(response, conversation=updated_ref)
        response_text_value = normalized.get("text", "")
        if not saw_stream_token and not response_text_value and maybe_render_required_action(
            client,
            response,
            stderr=stderr,
            fallback_conversation=updated_ref,
        ):
            return 1

        if stream:
            if saw_stream_token:
                print(file=stdout)
            else:
                print(render_response(normalized, "plain"), file=stdout)
        else:
            print(render_response(normalized, output_format), file=stdout)

        if updated_ref and updated_ref != state.current_conversation:
            state.current_conversation = updated_ref
            if model:
                state.model = model
            try:
                save_chat_state(state_path, state)
            except StateError as exc:
                print(f"gptty: {exc}", file=stderr)
                return 1
        elif model and model != state.model:
            state.model = model
            try:
                save_chat_state(state_path, state)
            except StateError as exc:
                print(f"gptty: {exc}", file=stderr)
                return 1

        return 0
    finally:
        if lock is not None:
            lock.release()


def _lock_timeout(args: Any) -> float:
    value = getattr(args, "lock_timeout", None)
    if value is not None:
        return max(0.0, float(value))
    if bool(getattr(args, "wait_lock", False)):
        return 120.0
    return DEFAULT_LOCK_TIMEOUT_SECONDS


def _render_lock_failure(exc: ConversationLockError, *, args: Any, stderr: TextIO) -> None:
    if getattr(args, "lock_timeout", None) is not None or bool(getattr(args, "wait_lock", False)):
        render_lock_timeout(exc, stderr=stderr)
    else:
        render_lock_error(exc, stderr=stderr)


def extract_conversation_ref(response: Any, fallback: Any = None) -> str | None:
    if isinstance(response, dict):
        for field in CONVERSATION_REF_FIELDS:
            value = response.get(field)
            if value:
                return str(value)

    for field in CONVERSATION_REF_FIELDS:
        value = getattr(response, field, None)
        if value:
            return str(value)

    if fallback:
        return str(fallback)
    return None


def response_text(response: Any) -> str:
    return normalize_response(response).get("text", "")
