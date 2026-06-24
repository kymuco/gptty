from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any, TextIO

from ..media import MediaInputError, collect_media_inputs
from ..prompt import build_prompt
from ..required_action import maybe_render_required_action
from ..sdk_client import GpttyClient


EMPTY_PROMPT_ERROR = "gptty ask requires a prompt argument or piped stdin."


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text is not None:
        return str(text)
    if response is None:
        return ""
    return str(response)


def _build_send_options(
    args: Any,
    *,
    stream: bool,
    media: list[str] | None,
    on_token: Callable[[str], None] | None,
) -> dict[str, Any]:
    options: dict[str, Any] = {"stream": stream}
    model = getattr(args, "model", None)
    if model:
        options["model"] = model
    if media:
        options["media"] = media
    if on_token is not None:
        options["on_token"] = on_token
    return options


def run_ask(
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

    stream = not bool(getattr(args, "no_stream", False))
    saw_stream_token = False

    def on_token(token: str) -> None:
        nonlocal saw_stream_token
        saw_stream_token = True
        print(token, end="", file=stdout, flush=True)

    client = client_factory(
        auth_file=getattr(args, "auth", "auth_data.json"),
        timeout=getattr(args, "timeout", 90),
    )
    try:
        response = client.send(
            prompt,
            **_build_send_options(
                args,
                stream=stream,
                media=media,
                on_token=on_token if stream else None,
            ),
        )
    except Exception as exc:  # noqa: BLE001 - command boundary converts SDK errors to exit codes.
        print(f"gptty: ask request failed: {exc}", file=stderr)
        return 1

    response_text = _response_text(response)
    if not saw_stream_token and not response_text and maybe_render_required_action(
        client,
        response,
        stderr=stderr,
    ):
        return 1

    if stream:
        if not saw_stream_token:
            print(response_text, file=stdout)
        else:
            print(file=stdout)
    else:
        print(response_text, file=stdout)

    return 0
