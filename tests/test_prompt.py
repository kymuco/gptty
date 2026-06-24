from __future__ import annotations

import pytest

from gptty.prompt import build_prompt


def test_build_prompt_from_prompt_only() -> None:
    assert build_prompt(["explain", "this"]) == "explain this"


def test_build_prompt_from_stdin_only() -> None:
    assert build_prompt([], stdin_text="context from pipe\n") == "context from pipe"


def test_build_prompt_combines_stdin_and_prompt() -> None:
    assert build_prompt(["review", "this"], stdin_text="diff --git") == (
        "diff --git\n\nUser prompt:\nreview this"
    )


def test_build_prompt_rejects_empty_input() -> None:
    with pytest.raises(ValueError, match="prompt argument"):
        build_prompt([], stdin_text="  \n")
