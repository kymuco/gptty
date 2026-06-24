from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

APP_NAME = "gptty"
CONFIG_ENV = "GPTTY_CONFIG_HOME"
DATA_ENV = "GPTTY_DATA_HOME"
PROFILE_ENV = "GPTTY_PROFILE"
CONFIG_FILE_NAME = "config.toml"
DEFAULT_AUTH_FILE = "auth_data.json"
DEFAULT_STATE_FILE = "gptty_state.json"

_PROFILE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_ACTIVE_PROFILE_RE = re.compile(r'^\s*active_profile\s*=\s*"([^"]+)"\s*$')


class ProfileError(RuntimeError):
    """Raised when profile config or path resolution fails."""


@dataclass(frozen=True)
class ProfilePaths:
    name: str
    profile_dir: Path
    auth_file: Path
    state_file: Path


@dataclass(frozen=True)
class SessionPaths:
    auth_file: Path
    state_file: Path
    profile: str | None
    source: str


@dataclass(frozen=True)
class ProfileConfig:
    active_profile: str | None = None


def config_dir() -> Path:
    override = os.environ.get(CONFIG_ENV)
    if override:
        return Path(override).expanduser()

    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Roaming" / APP_NAME

    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base).expanduser() / APP_NAME
    return Path.home() / ".config" / APP_NAME


def data_dir() -> Path:
    override = os.environ.get(DATA_ENV)
    if override:
        return Path(override).expanduser()

    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_NAME
        return Path.home() / "AppData" / "Local" / APP_NAME

    base = os.environ.get("XDG_DATA_HOME")
    if base:
        return Path(base).expanduser() / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def config_file() -> Path:
    return config_dir() / CONFIG_FILE_NAME


def profiles_dir() -> Path:
    return data_dir() / "profiles"


def validate_profile_name(name: str) -> str:
    profile = name.strip()
    if not profile:
        raise ProfileError("profile name cannot be empty")
    if profile in {".", ".."} or "/" in profile or "\\" in profile:
        raise ProfileError(f"invalid profile name: {name!r}")
    if not _PROFILE_RE.match(profile):
        raise ProfileError(
            "profile names may contain letters, numbers, '.', '_', and '-', "
            "and must start with a letter or number"
        )
    return profile


def load_config(path: str | Path | None = None) -> ProfileConfig:
    cfg_path = Path(path) if path is not None else config_file()
    if not cfg_path.exists():
        return ProfileConfig()

    try:
        lines = cfg_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ProfileError(f"failed to read profile config from {cfg_path}: {exc}") from exc

    active_profile: str | None = None
    for line in lines:
        match = _ACTIVE_PROFILE_RE.match(line)
        if match:
            active_profile = validate_profile_name(match.group(1))
            break

    return ProfileConfig(active_profile=active_profile)


def save_config(config: ProfileConfig, path: str | Path | None = None) -> None:
    cfg_path = Path(path) if path is not None else config_file()
    active_profile = config.active_profile
    if active_profile is not None:
        active_profile = validate_profile_name(active_profile)

    payload = "version = 1\n"
    if active_profile:
        payload += f'active_profile = "{active_profile}"\n'

    tmp_path = cfg_path.with_name(f".{cfg_path.name}.tmp")
    try:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(cfg_path)
    except OSError as exc:
        raise ProfileError(f"failed to write profile config to {cfg_path}: {exc}") from exc


def get_active_profile() -> str | None:
    return load_config().active_profile


def set_active_profile(name: str) -> ProfilePaths:
    profile = ensure_profile(name)
    save_config(ProfileConfig(active_profile=profile.name))
    return profile


def profile_paths(name: str, *, state_filename: str = DEFAULT_STATE_FILE) -> ProfilePaths:
    profile = validate_profile_name(name)
    root = profiles_dir() / profile
    return ProfilePaths(
        name=profile,
        profile_dir=root,
        auth_file=root / DEFAULT_AUTH_FILE,
        state_file=root / state_filename,
    )


def ensure_profile(name: str, *, state_filename: str = DEFAULT_STATE_FILE) -> ProfilePaths:
    paths = profile_paths(name, state_filename=state_filename)
    try:
        paths.profile_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ProfileError(f"failed to create profile directory {paths.profile_dir}: {exc}") from exc
    return paths


def list_profiles() -> list[str]:
    root = profiles_dir()
    if not root.exists():
        return []
    try:
        names = [path.name for path in root.iterdir() if path.is_dir()]
    except OSError as exc:
        raise ProfileError(f"failed to list profiles in {root}: {exc}") from exc
    return sorted(name for name in names if _PROFILE_RE.match(name))


def resolve_profile_name(explicit_profile: str | None = None) -> tuple[str | None, str]:
    if explicit_profile:
        return validate_profile_name(explicit_profile), "argument"

    env_profile = os.environ.get(PROFILE_ENV)
    if env_profile:
        return validate_profile_name(env_profile), "environment"

    active_profile = get_active_profile()
    if active_profile:
        return active_profile, "config"

    return None, "legacy"


def resolve_session_paths(
    *,
    auth_file: str | Path | None = None,
    state_file: str | Path | None = None,
    profile: str | None = None,
    state_filename: str = DEFAULT_STATE_FILE,
) -> SessionPaths:
    explicit_auth = Path(auth_file).expanduser() if auth_file else None
    explicit_state = Path(state_file).expanduser() if state_file else None

    profile_name, source = resolve_profile_name(profile)
    if profile_name:
        paths = ensure_profile(profile_name, state_filename=state_filename)
        return SessionPaths(
            auth_file=explicit_auth or paths.auth_file,
            state_file=explicit_state or paths.state_file,
            profile=paths.name,
            source=source,
        )

    return SessionPaths(
        auth_file=explicit_auth or Path(DEFAULT_AUTH_FILE),
        state_file=explicit_state or Path(state_filename),
        profile=None,
        source="legacy",
    )


def resolve_auth_path(
    *,
    auth_file: str | Path | None = None,
    profile: str | None = None,
) -> SessionPaths:
    return resolve_session_paths(auth_file=auth_file, profile=profile)
