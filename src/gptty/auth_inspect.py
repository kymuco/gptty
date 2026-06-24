from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOKEN_FIELDS = ("accessToken", "access_token", "api_key")


def inspect_auth_file(path: str | Path) -> dict[str, Any]:
    auth_path = Path(path)
    status: dict[str, Any] = {
        "auth_file": str(auth_path),
        "exists": auth_path.exists(),
        "readable": False,
        "status": "missing",
        "ok": False,
        "error": None,
        "timestamp": None,
        "token_source": None,
        "has_token": False,
        "expires_at": None,
        "expires_in_seconds": None,
        "expired": None,
        "has_cookies": False,
        "has_headers": False,
        "has_proof_token": False,
        "has_turnstile_token": False,
    }

    if not status["exists"]:
        status["error"] = "auth file does not exist"
        return status

    try:
        data = json.loads(auth_path.read_text(encoding="utf-8"))
    except OSError as exc:
        status["status"] = "invalid"
        status["error"] = f"failed to read auth file: {exc}"
        return status
    except json.JSONDecodeError as exc:
        status["status"] = "invalid"
        status["error"] = f"failed to parse auth file: {exc}"
        return status

    status["readable"] = True
    if not isinstance(data, dict):
        status["status"] = "invalid"
        status["error"] = "auth file must contain a JSON object"
        return status

    status["timestamp"] = _optional_str(data.get("timestamp"))
    token_source, token = _find_token(data)
    status["token_source"] = token_source
    status["has_token"] = bool(token)
    status["has_cookies"] = _has_mapping_values(data.get("cookies"))
    status["has_headers"] = _has_mapping_values(data.get("headers"))
    status["has_proof_token"] = data.get("proof_token") is not None
    status["has_turnstile_token"] = bool(_optional_str(data.get("turnstile_token")))

    if not token:
        status["status"] = "missing-token"
        status["error"] = "no accessToken or api_key found"
        return status

    expiry = decode_jwt_expiry(token)
    if expiry is None:
        status["status"] = "unknown-expiry"
        status["ok"] = True
        status["expired"] = None
        return status

    now = datetime.now(timezone.utc)
    expires_in = int((expiry - now).total_seconds())
    expired = expires_in <= 0
    status["expires_at"] = expiry.isoformat().replace("+00:00", "Z")
    status["expires_in_seconds"] = expires_in
    status["expired"] = expired
    status["ok"] = not expired
    status["status"] = "expired" if expired else "ok"
    if expired:
        status["error"] = "access token is expired"
    return status


def decode_jwt_expiry(token: str | None) -> datetime | None:
    if not token or token.count(".") < 2:
        return None
    try:
        payload = token.split(".", 2)[1]
        payload += "=" * (-len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
        exp = data.get("exp")
        if exp is None:
            return None
        return datetime.fromtimestamp(int(exp), tz=timezone.utc)
    except Exception:
        return None


def render_auth_status(status: dict[str, Any], output_format: str = "plain") -> str:
    if output_format == "json":
        return json.dumps(status, ensure_ascii=False, indent=2, sort_keys=True)
    if output_format != "plain":
        raise ValueError(f"Unsupported auth status output format: {output_format}")
    return _render_plain_status(status)


def _render_plain_status(status: dict[str, Any]) -> str:
    lines = [
        f"auth file: {status['auth_file']}",
        f"status: {status['status']}",
        f"token: {_present(status['has_token'])}",
    ]
    if status.get("token_source"):
        lines.append(f"token source: {status['token_source']}")
    if status.get("expires_at"):
        lines.append(f"expires at: {status['expires_at']}")
    if status.get("expires_in_seconds") is not None:
        lines.append(f"expires in: {_format_duration(int(status['expires_in_seconds']))}")
    elif status.get("has_token"):
        lines.append("expires in: unknown")
    lines.extend(
        [
            f"cookies: {_present(status['has_cookies'])}",
            f"headers: {_present(status['has_headers'])}",
            f"proof token: {_present(status['has_proof_token'])}",
            f"turnstile token: {_present(status['has_turnstile_token'])}",
        ]
    )
    if status.get("timestamp"):
        lines.append(f"captured at: {status['timestamp']}")
    if status.get("error"):
        lines.append(f"error: {status['error']}")
    if not status.get("ok"):
        lines.append("next step: run `gptty auth refresh --mode wait`")
    return "\n".join(lines)


def _find_token(data: dict[str, Any]) -> tuple[str | None, str | None]:
    for field in TOKEN_FIELDS:
        token = _optional_str(data.get(field))
        if token:
            return field, token
    return None, None


def _optional_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _has_mapping_values(value: Any) -> bool:
    return isinstance(value, dict) and any(bool(item) for item in value.values())


def _present(value: Any) -> str:
    return "present" if value else "missing"


def _format_duration(seconds: int) -> str:
    sign = "-" if seconds < 0 else ""
    remaining = abs(seconds)
    days, remaining = divmod(remaining, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes, _ = divmod(remaining, 60)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or parts:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return sign + " ".join(parts)
