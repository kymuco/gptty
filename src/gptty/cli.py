from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gptty",
        description="Terminal client for existing ChatGPT web sessions.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"gptty {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command")
    chat_parser = subparsers.add_parser(
        "chat",
        help="Start the legacy interactive chat while the SDK-backed CLI is being migrated.",
    )
    chat_parser.add_argument(
        "--state",
        default="webchat_state.json",
        help="Path to the local chat state file.",
    )
    chat_parser.add_argument(
        "--auth",
        default="auth_data.json",
        help="Path to auth_data.json.",
    )
    return parser


def _run_legacy_chat(state_path: str | Path, auth_file: str | Path) -> int:
    try:
        import main as legacy_main
    except ImportError as exc:
        print(
            "gptty could not import the legacy chat entrypoint. "
            "Run `python main.py` from the repository checkout, or reinstall the package.",
            file=sys.stderr,
        )
        print(f"Import error: {exc}", file=sys.stderr)
        return 1
    return int(legacy_main.main(state_path=state_path, auth_file=auth_file))


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command in {None, "chat"}:
        state_path = getattr(args, "state", "webchat_state.json")
        auth_file = getattr(args, "auth", "auth_data.json")
        return _run_legacy_chat(state_path=state_path, auth_file=auth_file)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
