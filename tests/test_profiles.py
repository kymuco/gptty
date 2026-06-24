from __future__ import annotations

from pathlib import Path

import pytest

from gptty.profiles import (
    ProfileConfig,
    ProfileError,
    config_file,
    ensure_profile,
    get_active_profile,
    list_profiles,
    resolve_session_paths,
    save_config,
    set_active_profile,
    validate_profile_name,
)


@pytest.fixture
def isolated_profiles(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("GPTTY_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("GPTTY_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.delenv("GPTTY_PROFILE", raising=False)
    return tmp_path


def test_resolve_session_paths_uses_legacy_local_defaults_without_profile(isolated_profiles: Path) -> None:
    resolved = resolve_session_paths()

    assert resolved.profile is None
    assert resolved.source == "legacy"
    assert resolved.auth_file == Path("auth_data.json")
    assert resolved.state_file == Path("gptty_state.json")


def test_resolve_session_paths_uses_explicit_profile(isolated_profiles: Path) -> None:
    resolved = resolve_session_paths(profile="work")

    assert resolved.profile == "work"
    assert resolved.source == "argument"
    assert resolved.auth_file == isolated_profiles / "data" / "profiles" / "work" / "auth_data.json"
    assert resolved.state_file == isolated_profiles / "data" / "profiles" / "work" / "gptty_state.json"
    assert resolved.auth_file.parent.exists()


def test_resolve_session_paths_uses_environment_profile(
    isolated_profiles: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GPTTY_PROFILE", "personal")

    resolved = resolve_session_paths()

    assert resolved.profile == "personal"
    assert resolved.source == "environment"
    assert resolved.state_file == isolated_profiles / "data" / "profiles" / "personal" / "gptty_state.json"


def test_resolve_session_paths_uses_active_profile_from_config(isolated_profiles: Path) -> None:
    set_active_profile("work")

    resolved = resolve_session_paths()

    assert get_active_profile() == "work"
    assert config_file() == isolated_profiles / "config" / "config.toml"
    assert resolved.profile == "work"
    assert resolved.source == "config"
    assert resolved.auth_file == isolated_profiles / "data" / "profiles" / "work" / "auth_data.json"


def test_explicit_auth_and_state_override_profile_defaults(isolated_profiles: Path) -> None:
    resolved = resolve_session_paths(
        auth_file="custom_auth.json",
        state_file="custom_state.json",
        profile="work",
    )

    assert resolved.profile == "work"
    assert resolved.auth_file == Path("custom_auth.json")
    assert resolved.state_file == Path("custom_state.json")


def test_explicit_auth_without_profile_keeps_legacy_state(isolated_profiles: Path) -> None:
    resolved = resolve_session_paths(auth_file="custom_auth.json")

    assert resolved.profile is None
    assert resolved.auth_file == Path("custom_auth.json")
    assert resolved.state_file == Path("gptty_state.json")


def test_ensure_profile_and_list_profiles(isolated_profiles: Path) -> None:
    ensure_profile("work")
    ensure_profile("personal")

    assert list_profiles() == ["personal", "work"]


def test_save_config_writes_active_profile(isolated_profiles: Path) -> None:
    save_config(ProfileConfig(active_profile="work"))

    assert get_active_profile() == "work"
    assert 'active_profile = "work"' in config_file().read_text(encoding="utf-8")


@pytest.mark.parametrize("name", ["", "../work", "work/account", "work account", "-work"])
def test_invalid_profile_names_raise(name: str) -> None:
    with pytest.raises(ProfileError):
        validate_profile_name(name)
