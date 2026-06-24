from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any, TextIO

from ..auth_inspect import inspect_auth_file, render_auth_status

AUTH_EXTRA_HINT = (
    "gptty: auth refresh dependencies are not installed.\n"
    "Install them with:\n"
    "  python -m pip install \"gptty-web[auth]\""
)


def run_auth_status(
    args: Any,
    *,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    status = inspect_auth_file(getattr(args, "auth", "auth_data.json"))
    output_format = getattr(args, "format", "plain")
    try:
        rendered = render_auth_status(status, output_format)
    except ValueError as exc:
        print(f"gptty: {exc}", file=stderr)
        return 2
    print(rendered, file=stdout)
    return 0 if status.get("ok") else 1


def run_auth_refresh(
    args: Any,
    *,
    auth_runner: Callable[..., Coroutine[Any, Any, Any]] | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    runner = auth_runner
    if runner is None:
        try:
            from auth_fetcher import run_auth_and_save
        except (ImportError, ModuleNotFoundError) as exc:
            print(AUTH_EXTRA_HINT, file=stderr)
            print(f"Import error: {exc}", file=stderr)
            return 1
        runner = run_auth_and_save

    output_file = Path(getattr(args, "auth", "auth_data.json"))
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"gptty: failed to create auth directory for {output_file}: {exc}", file=stderr)
        return 1

    try:
        asyncio.run(
            runner(
                output_file=str(output_file),
                auth_timeout=getattr(args, "timeout", 120.0),
                mode=getattr(args, "mode", "auto"),
                ready_timeout=getattr(args, "ready_timeout", 0.0),
                probe_prompt=getattr(args, "probe_prompt", "Hello"),
            )
        )
    except KeyboardInterrupt:
        print("gptty: auth refresh interrupted by user", file=stderr)
        return 130
    except RuntimeError as exc:
        message = str(exc)
        print(f"gptty: auth refresh failed: {message}", file=stderr)
        if _looks_like_missing_auth_dependency(message):
            print(AUTH_EXTRA_HINT, file=stderr)
        return 1
    except Exception as exc:  # noqa: BLE001 - command boundary converts auth capture failures to exit codes.
        print(f"gptty: auth refresh failed: {exc}", file=stderr)
        return 1

    print(f"gptty: auth data refreshed at {output_file}", file=stdout)
    return 0


def _looks_like_missing_auth_dependency(message: str) -> bool:
    lowered = message.lower()
    return "dependency" in lowered or "g4f" in lowered or "zendriver" in lowered or "nodriver" in lowered
