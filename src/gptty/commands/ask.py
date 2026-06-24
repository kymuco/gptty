from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any, TextIO

from ..prompt import build_prompt
from ..sdk_client import GpttyClient


EMPTY_PROMPT_ERROR = "gptty ask requires a prompt argument or piped stdin."


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text is not None:
        return str(text)
    if response is None:
        return ""
    return str(response)


def _build_send_options(args: Any, *, stream: bool, on_token: Callable[[str], None] | None) -> dict[str, Any]:
    options: dict[str, Any] = {"stream": stream}
    model = getattr(args, "model", None)
    if model:
        options["model"] = model
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
    response = client.send(
        prompt,
        **_build_send_options(
            args,
            stream=stream,
            on_token=on_token if stream else None,
        ),
    )

    if stream:
        if not saw_stream_token:
            print(_response_text(response), file=stdout)
        else:
            print(file=stdout)
    else:
        print(_response_text(response), file=stdout)

    return 0
