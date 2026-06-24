from __future__ import annotations

import pytest

from gptty.io import StdinReadError, read_stdin_text


class FakeStdin:
    def __init__(
        self,
        text: str = "",
        *,
        is_tty: bool = False,
        isatty_error: OSError | None = None,
        read_error: OSError | None = None,
    ) -> None:
        self.text = text
        self.is_tty = is_tty
        self.isatty_error = isatty_error
        self.read_error = read_error
        self.reads = 0

    def isatty(self) -> bool:
        if self.isatty_error is not None:
            raise self.isatty_error
        return self.is_tty

    def read(self) -> str:
        self.reads += 1
        if self.read_error is not None:
            raise self.read_error
        return self.text


def test_read_stdin_auto_reads_when_not_tty() -> None:
    stdin = FakeStdin("piped text", is_tty=False)

    assert read_stdin_text("auto", stdin=stdin) == "piped text"
    assert stdin.reads == 1


def test_read_stdin_auto_ignores_tty() -> None:
    stdin = FakeStdin("interactive text", is_tty=True)

    assert read_stdin_text("auto", stdin=stdin) is None
    assert stdin.reads == 0


def test_read_stdin_always_reads_even_tty() -> None:
    stdin = FakeStdin("forced text", is_tty=True)

    assert read_stdin_text("always", stdin=stdin) == "forced text"
    assert stdin.reads == 1


def test_read_stdin_never_ignores_pipe() -> None:
    stdin = FakeStdin("piped text", is_tty=False)

    assert read_stdin_text("never", stdin=stdin) is None
    assert stdin.reads == 0


def test_read_stdin_empty_text_is_returned() -> None:
    stdin = FakeStdin("", is_tty=False)

    assert read_stdin_text("auto", stdin=stdin) == ""
    assert stdin.reads == 1


def test_read_stdin_wraps_isatty_errors() -> None:
    stdin = FakeStdin(isatty_error=OSError("bad fd"))

    with pytest.raises(StdinReadError, match="failed to inspect stdin"):
        read_stdin_text("auto", stdin=stdin)


def test_read_stdin_wraps_read_errors() -> None:
    stdin = FakeStdin(read_error=OSError("broken pipe"))

    with pytest.raises(StdinReadError, match="failed to read stdin"):
        read_stdin_text("auto", stdin=stdin)


def test_read_stdin_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="Unsupported stdin mode"):
        read_stdin_text("sometimes")  # type: ignore[arg-type]
