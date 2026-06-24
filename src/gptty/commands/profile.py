from __future__ import annotations

import sys
from typing import Any, TextIO

from ..profiles import (
    ProfileError,
    config_file,
    ensure_profile,
    get_active_profile,
    list_profiles,
    profile_paths,
    resolve_profile_name,
    resolve_session_paths,
    set_active_profile,
)


def run_profile(args: Any, *, stdout: TextIO = sys.stdout, stderr: TextIO = sys.stderr) -> int:
    command = getattr(args, "profile_command", None)
    try:
        if command == "list":
            return run_profile_list(stdout=stdout)
        if command == "current":
            return run_profile_current(stdout=stdout)
        if command == "create":
            return run_profile_create(args, stdout=stdout)
        if command == "use":
            return run_profile_use(args, stdout=stdout)
        if command == "paths":
            return run_profile_paths(args, stdout=stdout)
    except ProfileError as exc:
        print(f"gptty: {exc}", file=stderr)
        return 2

    print("gptty profile requires a subcommand. Use `gptty profile --help`.", file=stderr)
    return 2


def run_profile_list(*, stdout: TextIO) -> int:
    active = get_active_profile()
    names = list_profiles()
    if active and active not in names:
        names = sorted([*names, active])

    if not names:
        print("No profiles have been created.", file=stdout)
        print("Use `gptty profile create default` to create one.", file=stdout)
        return 0

    for name in names:
        marker = "*" if name == active else " "
        print(f"{marker} {name}", file=stdout)
    return 0


def run_profile_current(*, stdout: TextIO) -> int:
    profile, source = resolve_profile_name()
    if profile:
        print(f"{profile} ({source})", file=stdout)
    else:
        print("local files (legacy fallback)", file=stdout)
    return 0


def run_profile_create(args: Any, *, stdout: TextIO) -> int:
    profile = ensure_profile(getattr(args, "name"))
    print(f"Created profile: {profile.name}", file=stdout)
    return 0


def run_profile_use(args: Any, *, stdout: TextIO) -> int:
    profile = set_active_profile(getattr(args, "name"))
    print(f"Active profile: {profile.name}", file=stdout)
    return 0


def run_profile_paths(args: Any, *, stdout: TextIO) -> int:
    name = getattr(args, "name", None)
    if name:
        paths = profile_paths(name)
        profile = paths.name
        auth_file = paths.auth_file
        state_file = paths.state_file
    else:
        resolved = resolve_session_paths()
        profile = resolved.profile or "local files"
        auth_file = resolved.auth_file
        state_file = resolved.state_file

    print(f"Profile: {profile}", file=stdout)
    print(f"Config: {config_file()}", file=stdout)
    print(f"Auth: {auth_file}", file=stdout)
    print(f"State: {state_file}", file=stdout)
    return 0
