from __future__ import annotations

from io import StringIO

import pytest

from gptty.locks import (
    ConversationLockError,
    acquire_conversation_lock,
    conversation_lock_path,
    render_lock_error,
    render_lock_timeout,
)


def test_acquire_conversation_lock_creates_and_releases_file(tmp_path) -> None:
    lock = acquire_conversation_lock(
        conversation_ref="conv-1",
        lock_dir=tmp_path,
        profile="work",
        command="send",
    )

    assert lock.info.lock_path.exists()
    assert lock.info.profile == "work"
    assert lock.info.command == "send"

    lock.release()

    assert not lock.info.lock_path.exists()


def test_acquire_conversation_lock_fails_when_existing_lock_is_active(tmp_path) -> None:
    lock = acquire_conversation_lock(conversation_ref="conv-1", lock_dir=tmp_path, command="send")

    try:
        with pytest.raises(ConversationLockError) as exc_info:
            acquire_conversation_lock(
                conversation_ref="conv-1",
                lock_dir=tmp_path,
                command="send",
                timeout=0,
            )
    finally:
        lock.release()

    assert exc_info.value.info.conversation_ref == "conv-1"


def test_acquire_conversation_lock_clears_stale_lock(tmp_path) -> None:
    first = acquire_conversation_lock(conversation_ref="conv-1", lock_dir=tmp_path, command="send")
    path = first.info.lock_path
    assert path == conversation_lock_path(tmp_path, "conv-1")

    second = acquire_conversation_lock(
        conversation_ref="conv-1",
        lock_dir=tmp_path,
        command="send",
        stale_after=0,
    )

    assert second.recovered_stale is True
    second.release()


def test_render_lock_error_uses_in_progress_copy(tmp_path) -> None:
    first = acquire_conversation_lock(
        conversation_ref="conv-1",
        lock_dir=tmp_path,
        profile="work",
        command="send",
    )

    try:
        with pytest.raises(ConversationLockError) as exc_info:
            acquire_conversation_lock(conversation_ref="conv-1", lock_dir=tmp_path, timeout=0)
    finally:
        first.release()

    stderr = StringIO()
    render_lock_error(exc_info.value, stderr=stderr)

    output = stderr.getvalue()
    assert "gptty: conversation in progress" in output
    assert "This conversation is already waiting for a reply." in output
    assert "Profile: work" in output
    assert "Conversation: conv-1" in output


def test_render_lock_timeout_includes_waited_time(tmp_path) -> None:
    first = acquire_conversation_lock(conversation_ref="conv-1", lock_dir=tmp_path, command="send")

    try:
        with pytest.raises(ConversationLockError) as exc_info:
            acquire_conversation_lock(conversation_ref="conv-1", lock_dir=tmp_path, timeout=0)
    finally:
        first.release()

    stderr = StringIO()
    render_lock_timeout(exc_info.value, stderr=stderr)

    output = stderr.getvalue()
    assert "gptty: conversation still in progress" in output
    assert "Waited:" in output
