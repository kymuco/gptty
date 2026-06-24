from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .io import StdinReadError, read_stdin_text


def _add_session_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--auth",
        default="auth_data.json",
        help="Path to auth_data.json.",
    )
    parser.add_argument(
        "--state",
        default="gptty_state.json",
        help="Path to the local gptty state file.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Request timeout in seconds.",
    )


def _add_stdin_options(parser: argparse.ArgumentParser) -> None:
    stdin_group = parser.add_mutually_exclusive_group()
    stdin_group.add_argument(
        "--stdin",
        dest="stdin_mode",
        action="store_const",
        const="always",
        default="auto",
        help="Force reading stdin, even when stdin does not look piped.",
    )
    stdin_group.add_argument(
        "--no-stdin",
        dest="stdin_mode",
        action="store_const",
        const="never",
        help="Ignore stdin, even when input is piped.",
    )


def _add_output_format_option(parser: argparse.ArgumentParser, *, default: str = "plain") -> None:
    parser.add_argument(
        "--format",
        choices=("plain", "json", "markdown"),
        default=default,
        help="Output format.",
    )


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

    ask_parser = subparsers.add_parser(
        "ask",
        help="Send a one-shot prompt through the SDK-backed ChatGPT web-session client.",
    )
    ask_parser.add_argument(
        "prompt",
        nargs="*",
        help="Prompt text. If omitted, gptty reads the prompt from piped stdin.",
    )
    _add_stdin_options(ask_parser)
    ask_parser.add_argument(
        "--auth",
        default="auth_data.json",
        help="Path to auth_data.json.",
    )
    ask_parser.add_argument(
        "--model",
        default=None,
        help="Model name to pass through to the SDK.",
    )
    ask_parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Wait for the full response before printing output.",
    )
    ask_parser.add_argument(
        "--plain",
        action="store_true",
        help="Print plain response text. Currently this is the default output mode.",
    )
    ask_parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Request timeout in seconds.",
    )

    send_parser = subparsers.add_parser(
        "send",
        help="Send a prompt to the attached conversation, an explicit conversation, or a new chat.",
    )
    send_parser.add_argument(
        "prompt",
        nargs="*",
        help="Prompt text. If omitted, gptty reads the prompt from piped stdin.",
    )
    destination_group = send_parser.add_mutually_exclusive_group()
    destination_group.add_argument(
        "--to",
        default=None,
        help="Conversation URL or id to send to instead of the attached conversation.",
    )
    destination_group.add_argument(
        "--new",
        action="store_true",
        help="Start a new conversation instead of using an attached conversation.",
    )
    _add_stdin_options(send_parser)
    _add_session_options(send_parser)
    _add_output_format_option(send_parser)
    send_parser.add_argument(
        "--model",
        default=None,
        help="Model name to pass through to the SDK and store in state.",
    )
    send_parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Wait for the full response before printing output.",
    )

    chat_parser = subparsers.add_parser(
        "chat",
        help="Start an interactive SDK-backed chat loop.",
    )
    chat_parser.add_argument(
        "--legacy",
        action="store_true",
        help="Run the legacy main.py interactive chat runtime.",
    )
    chat_parser.add_argument(
        "--state",
        default=None,
        help="Path to the local chat state file.",
    )
    chat_parser.add_argument(
        "--auth",
        default="auth_data.json",
        help="Path to auth_data.json.",
    )
    chat_parser.add_argument(
        "--model",
        default=None,
        help="Model name to store in state and pass through to the SDK.",
    )
    chat_parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Wait for each full response before printing output.",
    )
    chat_parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Request timeout in seconds.",
    )

    attach_parser = subparsers.add_parser(
        "attach",
        help="Attach an existing ChatGPT conversation and save it in gptty state.",
    )
    attach_parser.add_argument("url_or_id", help="Conversation URL or id to attach.")
    _add_session_options(attach_parser)

    messages_parser = subparsers.add_parser(
        "messages",
        help="Print messages from an explicit or attached ChatGPT conversation.",
    )
    messages_parser.add_argument(
        "url_or_id",
        nargs="?",
        help="Optional conversation URL or id. Defaults to the attached conversation.",
    )
    messages_parser.add_argument(
        "--last",
        type=int,
        default=None,
        help="Limit output to the last N messages when supported by the SDK.",
    )
    _add_session_options(messages_parser)
    _add_output_format_option(messages_parser)

    status_parser = subparsers.add_parser(
        "status",
        help="Print status for an explicit or attached ChatGPT conversation.",
    )
    status_parser.add_argument(
        "url_or_id",
        nargs="?",
        help="Optional conversation URL or id. Defaults to the attached conversation.",
    )
    _add_session_options(status_parser)
    _add_output_format_option(status_parser)

    export_parser = subparsers.add_parser(
        "export",
        help="Export messages from an explicit or attached ChatGPT conversation.",
    )
    export_parser.add_argument(
        "url_or_id",
        nargs="?",
        help="Optional conversation URL or id. Defaults to the attached conversation.",
    )
    export_parser.add_argument(
        "--last",
        type=int,
        default=None,
        help="Limit export to the last N messages when supported by the SDK.",
    )
    export_parser.add_argument(
        "--output",
        default=None,
        help="Write export to a file instead of stdout.",
    )
    export_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite --output if it already exists.",
    )
    _add_session_options(export_parser)
    _add_output_format_option(export_parser, default="markdown")

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

    if args.command == "ask":
        from .commands.ask import run_ask

        try:
            stdin_text = read_stdin_text(getattr(args, "stdin_mode", "auto"))
        except StdinReadError as exc:
            print(f"gptty: {exc}", file=sys.stderr)
            return 1
        return run_ask(args, stdin_text=stdin_text)

    if args.command == "send":
        from .commands.send import run_send

        try:
            stdin_text = read_stdin_text(getattr(args, "stdin_mode", "auto"))
        except StdinReadError as exc:
            print(f"gptty: {exc}", file=sys.stderr)
            return 1
        return run_send(args, stdin_text=stdin_text)

    if args.command == "attach":
        from .commands.attach import run_attach

        return run_attach(args)

    if args.command == "messages":
        from .commands.messages import run_messages

        return run_messages(args)

    if args.command == "status":
        from .commands.status import run_status

        return run_status(args)

    if args.command == "export":
        from .commands.export import run_export

        return run_export(args)

    if args.command in {None, "chat"}:
        if bool(getattr(args, "legacy", False)):
            state_path = getattr(args, "state", None) or "webchat_state.json"
            auth_file = getattr(args, "auth", "auth_data.json")
            return _run_legacy_chat(state_path=state_path, auth_file=auth_file)

        from .commands.chat import run_chat

        if getattr(args, "state", None) is None:
            args.state = "gptty_state.json"
        return run_chat(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
