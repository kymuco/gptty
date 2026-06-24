from __future__ import annotations

import json
from argparse import Namespace
from io import StringIO
from pathlib import Path
from typing import Any

from gptty.commands.auth import run_auth_refresh, run_auth_status


async def fake_auth_runner(**kwargs: Any) -> None:
    fake_auth_runner.calls.append(kwargs)


fake_auth_runner.calls = []


def test_auth_status_returns_1_for_missing_file(tmp_path: Path) -> None:
    stdout = StringIO()

    code = run_auth_status(
        Namespace(auth=str(tmp_path / "missing.json"), format="plain"),
        stdout=stdout,
    )

    assert code == 1
    assert "status: missing" in stdout.getvalue()


def test_auth_status_prints_json(tmp_path: Path) -> None:
    path = tmp_path / "auth_data.json"
    path.write_text(json.dumps({"accessToken": "not-a-jwt"}), encoding="utf-8")
    stdout = StringIO()

    code = run_auth_status(Namespace(auth=str(path), format="json"), stdout=stdout)

    assert code == 0
    assert json.loads(stdout.getvalue())["status"] == "unknown-expiry"


def test_auth_refresh_calls_runner_with_cli_options(tmp_path: Path) -> None:
    fake_auth_runner.calls.clear()
    stdout = StringIO()

    code = run_auth_refresh(
        Namespace(
            auth=str(tmp_path / "auth_data.json"),
            mode="wait",
            timeout=42.0,
            ready_timeout=7.0,
            probe_prompt="Ping",
        ),
        auth_runner=fake_auth_runner,
        stdout=stdout,
    )

    assert code == 0
    assert fake_auth_runner.calls == [
        {
            "output_file": str(tmp_path / "auth_data.json"),
            "auth_timeout": 42.0,
            "mode": "wait",
            "ready_timeout": 7.0,
            "probe_prompt": "Ping",
        }
    ]
    assert "auth data refreshed" in stdout.getvalue()


def test_auth_refresh_reports_runner_failure(tmp_path: Path) -> None:
    async def failing_runner(**kwargs: Any) -> None:
        raise RuntimeError("Dependency 'g4f' is not installed")

    stderr = StringIO()

    code = run_auth_refresh(
        Namespace(
            auth=str(tmp_path / "auth_data.json"),
            mode="auto",
            timeout=120.0,
            ready_timeout=0.0,
            probe_prompt="Hello",
        ),
        auth_runner=failing_runner,
        stderr=stderr,
    )

    assert code == 1
    assert "auth refresh failed" in stderr.getvalue()
    assert "gptty-web[auth]" in stderr.getvalue()
