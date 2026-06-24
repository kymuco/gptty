from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

import gptty.commands.ask as ask_command
import gptty.commands.send as send_command
from gptty import cli


@pytest.fixture
def isolated_profiles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("GPTTY_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("GPTTY_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.delenv("GPTTY_PROFILE", raising=False)
    return tmp_path


def test_profile_create_use_current_and_list(
    isolated_profiles: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["profile", "create", "work"]) == 0
    assert "Created profile: work" in capsys.readouterr().out

    assert cli.main(["profile", "use", "work"]) == 0
    assert "Active profile: work" in capsys.readouterr().out

    assert cli.main(["profile", "current"]) == 0
    assert capsys.readouterr().out.strip() == "work (config)"

    assert cli.main(["profile", "list"]) == 0
    assert "* work" in capsys.readouterr().out


def test_profile_paths_reports_active_profile(
    isolated_profiles: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert cli.main(["profile", "use", "work"]) == 0
    capsys.readouterr()

    assert cli.main(["profile", "paths"]) == 0
    output = capsys.readouterr().out

    assert "Profile: work" in output
    assert f"Config: {isolated_profiles / 'config' / 'config.toml'}" in output
    assert f"Auth: {isolated_profiles / 'data' / 'profiles' / 'work' / 'auth_data.json'}" in output
    assert f"State: {isolated_profiles / 'data' / 'profiles' / 'work' / 'gptty_state.json'}" in output


def test_ask_uses_global_profile_option(
    isolated_profiles: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}

    def fake_read_stdin_text(mode: str) -> None:
        return None

    def fake_run_ask(args: Any, *, stdin_text: str | None = None) -> int:
        calls["auth"] = args.auth
        calls["profile"] = args.profile
        calls["stdin_text"] = stdin_text
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(ask_command, "run_ask", fake_run_ask)

    assert cli.main(["--profile", "work", "ask", "hello"]) == 0

    assert calls == {
        "auth": str(isolated_profiles / "data" / "profiles" / "work" / "auth_data.json"),
        "profile": "work",
        "stdin_text": None,
    }


def test_ask_uses_command_profile_option(
    isolated_profiles: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}

    def fake_read_stdin_text(mode: str) -> None:
        return None

    def fake_run_ask(args: Any, *, stdin_text: str | None = None) -> int:
        calls["auth"] = args.auth
        calls["profile"] = args.profile
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(ask_command, "run_ask", fake_run_ask)

    assert cli.main(["ask", "--profile", "personal", "hello"]) == 0

    assert calls == {
        "auth": str(isolated_profiles / "data" / "profiles" / "personal" / "auth_data.json"),
        "profile": "personal",
    }


def test_send_uses_environment_profile(
    isolated_profiles: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    monkeypatch.setenv("GPTTY_PROFILE", "work")

    def fake_read_stdin_text(mode: str) -> None:
        return None

    def fake_run_send(args: Any, *, stdin_text: str | None = None) -> int:
        calls["auth"] = args.auth
        calls["state"] = args.state
        calls["profile"] = args.profile
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(send_command, "run_send", fake_run_send)

    assert cli.main(["send", "--new", "hello"]) == 0

    assert calls == {
        "auth": str(isolated_profiles / "data" / "profiles" / "work" / "auth_data.json"),
        "state": str(isolated_profiles / "data" / "profiles" / "work" / "gptty_state.json"),
        "profile": "work",
    }


def test_explicit_paths_override_active_profile(
    isolated_profiles: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: dict[str, Any] = {}
    assert cli.main(["profile", "use", "work"]) == 0

    def fake_read_stdin_text(mode: str) -> None:
        return None

    def fake_run_send(args: Any, *, stdin_text: str | None = None) -> int:
        calls["auth"] = args.auth
        calls["state"] = args.state
        calls["profile"] = args.profile
        return 0

    monkeypatch.setattr(cli, "read_stdin_text", fake_read_stdin_text)
    monkeypatch.setattr(send_command, "run_send", fake_run_send)

    assert cli.main([
        "send",
        "--new",
        "--auth",
        "custom_auth.json",
        "--state",
        "custom_state.json",
        "hello",
    ]) == 0

    assert calls == {
        "auth": "custom_auth.json",
        "state": "custom_state.json",
        "profile": "work",
    }
