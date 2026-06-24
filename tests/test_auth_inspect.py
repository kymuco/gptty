from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from gptty.auth_inspect import inspect_auth_file, render_auth_status


def make_token(exp: datetime | None) -> str:
    header = _b64({"alg": "none"})
    payload = {} if exp is None else {"exp": int(exp.timestamp())}
    return f"{header}.{_b64(payload)}.sig"


def _b64(payload: dict[str, object]) -> str:
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return encoded.rstrip("=")


def test_inspect_auth_file_reports_ok_token(tmp_path: Path) -> None:
    path = tmp_path / "auth_data.json"
    path.write_text(
        json.dumps(
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "accessToken": make_token(datetime.now(timezone.utc) + timedelta(hours=2)),
                "cookies": {"session": "yes"},
                "headers": {"user-agent": "test"},
                "proof_token": [1, 2, 3],
                "turnstile_token": "turnstile",
            }
        ),
        encoding="utf-8",
    )

    status = inspect_auth_file(path)

    assert status["status"] == "ok"
    assert status["ok"] is True
    assert status["token_source"] == "accessToken"
    assert status["expired"] is False
    assert status["has_cookies"] is True
    assert status["has_headers"] is True
    assert status["has_proof_token"] is True
    assert status["has_turnstile_token"] is True


def test_inspect_auth_file_reports_expired_token(tmp_path: Path) -> None:
    path = tmp_path / "auth_data.json"
    path.write_text(
        json.dumps({"api_key": make_token(datetime.now(timezone.utc) - timedelta(hours=1))}),
        encoding="utf-8",
    )

    status = inspect_auth_file(path)

    assert status["status"] == "expired"
    assert status["ok"] is False
    assert status["token_source"] == "api_key"
    assert status["expired"] is True
    assert status["error"] == "access token is expired"


def test_inspect_auth_file_reports_unknown_expiry(tmp_path: Path) -> None:
    path = tmp_path / "auth_data.json"
    path.write_text(json.dumps({"accessToken": "not-a-jwt"}), encoding="utf-8")

    status = inspect_auth_file(path)

    assert status["status"] == "unknown-expiry"
    assert status["ok"] is True
    assert status["expired"] is None


def test_inspect_auth_file_reports_missing_file(tmp_path: Path) -> None:
    status = inspect_auth_file(tmp_path / "missing.json")

    assert status["status"] == "missing"
    assert status["ok"] is False
    assert status["error"] == "auth file does not exist"


def test_inspect_auth_file_reports_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "auth_data.json"
    path.write_text("{", encoding="utf-8")

    status = inspect_auth_file(path)

    assert status["status"] == "invalid"
    assert status["ok"] is False
    assert "failed to parse auth file" in status["error"]


def test_render_auth_status_plain_includes_next_step_for_bad_status(tmp_path: Path) -> None:
    status = inspect_auth_file(tmp_path / "missing.json")

    rendered = render_auth_status(status)

    assert "status: missing" in rendered
    assert "next step: run `gptty auth refresh --mode wait`" in rendered


def test_render_auth_status_json(tmp_path: Path) -> None:
    status = inspect_auth_file(tmp_path / "missing.json")

    rendered = render_auth_status(status, "json")

    assert json.loads(rendered)["status"] == "missing"
