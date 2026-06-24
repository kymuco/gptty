from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TextIO

from .profiles import profile_paths

DEFAULT_LOCK_TIMEOUT_SECONDS = 2.0
DEFAULT_STALE_AFTER_SECONDS = 6 * 60 * 60


class ConversationLockError(RuntimeError):
    """Raised when a conversation lock cannot be acquired."""

    def __init__(self, info: "ConversationLockInfo", *, waited: float) -> None:
        self.info = info
        self.waited = waited
        super().__init__(f"conversation is locked: {info.conversation_ref}")


@dataclass(frozen=True)
class ConversationLockInfo:
    conversation_ref: str
    lock_path: Path
    profile: str | None = None
    command: str | None = None
    pid: int | None = None
    started_at: str | None = None
    run_id: str | None = None
    run_file: Path | None = None


@dataclass(frozen=True)
class ConversationLock:
    info: ConversationLockInfo
    recovered_stale: bool = False

    def release(self) -> None:
        try:
            self.info.lock_path.unlink()
        except FileNotFoundError:
            return
        except OSError:
            return

    def __enter__(self) -> "ConversationLock":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.release()


def conversation_lock_dir(*, profile: str | None, state_path: str | Path) -> Path:
    if profile:
        return profile_paths(profile).profile_dir / "locks"
    return Path(state_path).expanduser().parent / ".gptty_locks"


def conversation_lock_path(lock_dir: str | Path, conversation_ref: str) -> Path:
    digest = hashlib.sha256(conversation_ref.encode("utf-8")).hexdigest()[:32]
    return Path(lock_dir) / f"conversation-{digest}.lock"


def acquire_conversation_lock(
    *,
    conversation_ref: str,
    lock_dir: str | Path,
    profile: str | None = None,
    command: str | None = None,
    run_id: str | None = None,
    run_file: str | Path | None = None,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    stale_after: float = DEFAULT_STALE_AFTER_SECONDS,
    poll_interval: float = 0.2,
) -> ConversationLock:
    root = Path(lock_dir)
    path = conversation_lock_path(root, conversation_ref)
    started = time.monotonic()
    recovered_stale = False

    while True:
        root.mkdir(parents=True, exist_ok=True)
        info = ConversationLockInfo(
            conversation_ref=conversation_ref,
            lock_path=path,
            profile=profile,
            command=command,
            pid=os.getpid(),
            started_at=datetime.now(timezone.utc).isoformat(),
            run_id=run_id,
            run_file=Path(run_file) if run_file is not None else None,
        )
        payload = json.dumps(_serialize_info(info), indent=2, sort_keys=True) + "\n"
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            existing = read_conversation_lock(path, fallback_conversation=conversation_ref)
            if is_stale_lock(path, existing, stale_after=stale_after):
                try:
                    path.unlink()
                    recovered_stale = True
                    continue
                except OSError:
                    pass

            waited = time.monotonic() - started
            if waited >= timeout:
                raise ConversationLockError(existing, waited=waited)
            time.sleep(poll_interval)
            continue

        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(payload)
        return ConversationLock(info=info, recovered_stale=recovered_stale)


def read_conversation_lock(path: str | Path, *, fallback_conversation: str) -> ConversationLockInfo:
    lock_path = Path(path)
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}

    if not isinstance(data, dict):
        data = {}

    conversation_ref = str(data.get("conversation_ref") or fallback_conversation)
    profile = _optional_str(data.get("profile"))
    command = _optional_str(data.get("command"))
    pid = data.get("pid")
    run_file = _optional_str(data.get("run_file"))
    return ConversationLockInfo(
        conversation_ref=conversation_ref,
        lock_path=lock_path,
        profile=profile,
        command=command,
        pid=pid if isinstance(pid, int) else None,
        started_at=_optional_str(data.get("started_at")),
        run_id=_optional_str(data.get("run_id")),
        run_file=Path(run_file) if run_file else None,
    )


def is_stale_lock(path: str | Path, info: ConversationLockInfo, *, stale_after: float) -> bool:
    if stale_after <= 0:
        return True

    started_at = _parse_started_at(info.started_at)
    if started_at is not None:
        age = datetime.now(timezone.utc).timestamp() - started_at.timestamp()
        return age >= stale_after

    try:
        age = time.time() - Path(path).stat().st_mtime
    except OSError:
        return False
    return age >= stale_after


def render_lock_error(exc: ConversationLockError, *, stderr: TextIO) -> None:
    print("gptty: conversation in progress", file=stderr)
    print(file=stderr)
    print("This conversation is already waiting for a reply.", file=stderr)
    print("Wait for the current reply to finish, then try again.", file=stderr)
    print(file=stderr)
    if exc.info.profile:
        print(f"Profile: {exc.info.profile}", file=stderr)
    print(f"Conversation: {exc.info.conversation_ref}", file=stderr)


def render_lock_timeout(exc: ConversationLockError, *, stderr: TextIO) -> None:
    print("gptty: conversation still in progress", file=stderr)
    print(file=stderr)
    print("This conversation is still waiting for a reply.", file=stderr)
    print("Try again after the current reply finishes, or send to another conversation.", file=stderr)
    print(file=stderr)
    if exc.info.profile:
        print(f"Profile: {exc.info.profile}", file=stderr)
    print(f"Conversation: {exc.info.conversation_ref}", file=stderr)
    print(f"Waited: {int(round(exc.waited))}s", file=stderr)


def render_stale_lock_recovered(lock: ConversationLock, *, stderr: TextIO) -> None:
    if not lock.recovered_stale:
        return
    print("gptty: recovered previous session", file=stderr)
    print(file=stderr)
    print("A previous command did not finish cleanly, so gptty cleared its local lock.", file=stderr)
    print(file=stderr)
    print("Continuing...", file=stderr)


def _serialize_info(info: ConversationLockInfo) -> dict[str, object]:
    data = asdict(info)
    data["lock_path"] = str(info.lock_path)
    if info.run_file is not None:
        data["run_file"] = str(info.run_file)
    return data


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_started_at(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
