from __future__ import annotations

from pathlib import Path
from typing import Any


class MediaInputError(ValueError):
    """Raised when CLI media input is invalid before reaching the SDK."""


def collect_media_inputs(args: Any) -> list[str] | None:
    raw_items = getattr(args, "image", None) or []
    media: list[str] = []
    for raw_item in raw_items:
        item = str(raw_item).strip()
        if not item:
            raise MediaInputError("--image requires a non-empty path, URL, or data URI")
        media.append(_normalize_media_item(item))
    return media or None


def _normalize_media_item(item: str) -> str:
    if _is_remote_url(item) or _is_data_uri(item):
        return item

    path = Path(item).expanduser()
    if not path.exists():
        raise MediaInputError(f"image file does not exist: {item}")
    if not path.is_file():
        raise MediaInputError(f"image path is not a file: {item}")
    return str(path)


def _is_remote_url(item: str) -> bool:
    lowered = item.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def _is_data_uri(item: str) -> bool:
    return item.lower().startswith("data:")
