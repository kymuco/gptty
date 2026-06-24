from __future__ import annotations

import sys
from typing import Literal, TextIO

StdinMode = Literal["auto", "always", "never"]


class StdinReadError(RuntimeError):
    """Raised when stdin should be read but cannot be read safely."""


def read_stdin_text(mode: StdinMode = "auto", stdin: TextIO = sys.stdin) -> str | None:
    """Read stdin according to a shell-friendly CLI policy.

    `auto` reads only from a pipe or redirected stdin.
    `always` forces a read even if stdin reports itself as a TTY.
    `never` ignores stdin and returns None.
    """

    if mode == "never":
        return None
    if mode not in {"auto", "always"}:
        raise ValueError(f"Unsupported stdin mode: {mode}")

    try:
        is_tty = stdin.isatty()
    except OSError as exc:
        raise StdinReadError(f"failed to inspect stdin: {exc}") from exc

    if mode == "auto" and is_tty:
        return None

    try:
        return stdin.read()
    except OSError as exc:
        raise StdinReadError(f"failed to read stdin: {exc}") from exc
