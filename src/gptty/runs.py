from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from .profiles import profile_paths


@dataclass(frozen=True)
class RunPaths:
    run_id: str
    run_file: Path
    events_file: Path


class RunRecorder:
    def __init__(self, paths: RunPaths, summary: dict[str, Any]) -> None:
        self.paths = paths
        self.summary = summary
        self.event("run_started")

    @property
    def run_id(self) -> str:
        return self.paths.run_id

    @property
    def run_file(self) -> Path:
        return self.paths.run_file

    @property
    def events_file(self) -> Path:
        return self.paths.events_file

    def event(self, event_type: str, **data: Any) -> None:
        event = {
            "type": event_type,
            "timestamp": utc_now(),
            **data,
        }
        self.paths.events_file.parent.mkdir(parents=True, exist_ok=True)
        with self.paths.events_file.open("a", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(event, ensure_ascii=False, sort_keys=True))
            file.write("\n")
        self.summary["last_event"] = event_type
        self.summary["updated_at"] = event["timestamp"]
        write_run_summary(self.paths.run_file, self.summary)

    def complete(self) -> None:
        self.summary["status"] = "completed"
        self.summary["completed_at"] = utc_now()
        self.event("completed")

    def fail(self, message: str) -> None:
        self.summary["status"] = "failed"
        self.summary["error"] = message
        self.summary["completed_at"] = utc_now()
        self.event("failed", message=message)


def run_dir(*, profile: str | None, state_path: str | Path) -> Path:
    if profile:
        return profile_paths(profile).profile_dir / "runs"
    return Path(state_path).expanduser().parent / ".gptty_runs"


def start_run(
    *,
    profile: str | None,
    state_path: str | Path,
    command: str,
    conversation_ref: str,
) -> RunRecorder:
    root = run_dir(profile=profile, state_path=state_path)
    run_id = uuid.uuid4().hex
    paths = RunPaths(
        run_id=run_id,
        run_file=root / f"{run_id}.json",
        events_file=root / f"{run_id}.jsonl",
    )
    summary: dict[str, Any] = {
        "run_id": run_id,
        "profile": profile,
        "command": command,
        "conversation_ref": conversation_ref,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": None,
        "last_event": None,
        "events_file": str(paths.events_file),
    }
    write_run_summary(paths.run_file, summary)
    return RunRecorder(paths, summary)


def write_run_summary(path: str | Path, summary: dict[str, Any]) -> None:
    run_path = Path(path)
    run_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = run_path.with_name(f".{run_path.name}.tmp")
    tmp_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp_path.replace(run_path)


def read_run_summary(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def read_run_events(path: str | Path, *, from_start: bool = False) -> list[dict[str, Any]]:
    events_path = Path(path)
    try:
        lines = events_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    if from_start:
        return events
    return events[-20:]


def render_run_status(
    *,
    summary: dict[str, Any],
    events: list[dict[str, Any]],
    stdout: TextIO,
    status_only: bool = False,
) -> None:
    conversation = _optional_str(summary.get("conversation_ref")) or "unknown"
    profile = _optional_str(summary.get("profile")) or "local files"
    elapsed = format_elapsed(_optional_str(summary.get("started_at")))
    status = _optional_str(summary.get("status")) or "unknown"
    last_event = _optional_str(summary.get("last_event")) or "unknown"

    if status == "running":
        print("gptty: conversation in progress", file=stdout)
    elif status == "failed":
        print("gptty: previous command failed", file=stdout)
    else:
        print("gptty: conversation run status", file=stdout)
    print(file=stdout)
    print(f"Profile: {profile}", file=stdout)
    print(f"Conversation: {conversation}", file=stdout)
    print(f"Elapsed: {elapsed}", file=stdout)
    print(f"Status: {status}", file=stdout)
    print(f"Last event: {last_event}", file=stdout)

    if status_only:
        return

    token_text = "".join(str(event.get("text", "")) for event in events if event.get("type") == "token_delta")
    required_action = next((event for event in reversed(events) if event.get("type") == "required_action"), None)
    failure = next((event for event in reversed(events) if event.get("type") == "failed"), None)

    if token_text:
        print(file=stdout)
        print("Assistant:", file=stdout)
        print(token_text, file=stdout)
    elif required_action:
        print(file=stdout)
        print("Action needed:", file=stdout)
        print(str(required_action.get("message") or "ChatGPT is waiting for a web UI action."), file=stdout)
    elif failure:
        print(file=stdout)
        print(str(failure.get("message") or "The command failed."), file=stdout)
    elif status == "running":
        print(file=stdout)
        print("Waiting for ChatGPT...", file=stdout)


def format_elapsed(started_at: str | None) -> str:
    started = parse_time(started_at)
    if started is None:
        return "unknown"
    seconds = max(0, int(datetime.now(timezone.utc).timestamp() - started.timestamp()))
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
