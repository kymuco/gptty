from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol


class ChatGPTWebClientProtocol(Protocol):
    def send(self, prompt: str, **options: Any) -> Any: ...

    def send_to_conversation(
        self,
        url_or_id: Any,
        prompt: str,
        **options: Any,
    ) -> Any: ...

    def attach_conversation(self, url_or_id: Any, **options: Any) -> Any: ...

    def get_messages(self, url_or_id: Any, **options: Any) -> Any: ...

    def get_required_action(self, url_or_id: Any, **options: Any) -> Any: ...

    def get_status(self, url_or_id: Any, **options: Any) -> Any: ...

    def wait_until_completed(self, url_or_id: Any, **options: Any) -> Any: ...


class GpttyClient:
    """Thin boundary between gptty commands and chatgpt-web-adapter.

    This class must stay CLI-shaped, not backend-shaped. The SDK owns web-session
    transport, payload construction, conversation parsing, and status detection.
    """

    def __init__(
        self,
        auth_file: str | Path = "auth_data.json",
        timeout: int = 90,
        *,
        sdk_client: ChatGPTWebClientProtocol | None = None,
    ) -> None:
        self.auth_file = Path(auth_file)
        self.timeout = int(timeout)
        self._client = sdk_client or self._build_sdk_client()

    def _build_sdk_client(self) -> ChatGPTWebClientProtocol:
        from chatgpt_web_adapter import ChatGPTWebClient

        return ChatGPTWebClient(auth_file=self.auth_file, timeout=self.timeout)

    def send(self, prompt: str, **options: Any) -> Any:
        return self._client.send(prompt, **_sdk_send_options(options))

    def send_to_conversation(
        self,
        url_or_id: Any,
        prompt: str,
        **options: Any,
    ) -> Any:
        return self._client.send_to_conversation(
            url_or_id,
            prompt,
            **_sdk_send_options(options),
        )

    def attach_conversation(self, url_or_id: Any, **options: Any) -> Any:
        return self._client.attach_conversation(url_or_id, **options)

    def get_messages(self, url_or_id: Any, **options: Any) -> Any:
        return self._client.get_messages(url_or_id, **options)

    def get_required_action(self, url_or_id: Any, **options: Any) -> Any:
        helper = getattr(self._client, "get_required_action", None)
        if not callable(helper):
            return None
        return helper(url_or_id, **options)

    def get_status(self, url_or_id: Any, **options: Any) -> Any:
        return self._client.get_status(url_or_id, **options)

    def wait_until_completed(self, url_or_id: Any, **options: Any) -> Any:
        return self._client.wait_until_completed(url_or_id, **options)


def _sdk_send_options(options: dict[str, Any]) -> dict[str, Any]:
    sdk_options = dict(options)
    sdk_options.pop("stream", None)
    return sdk_options
