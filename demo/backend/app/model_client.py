import asyncio
import base64
import os
from pathlib import Path
from typing import Any

import httpx
import requests


class ModelClient:
    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        settings = settings or {}
        self.base_url = (settings.get("base_url") or os.getenv("LLM_BASE_URL", "")).rstrip("/")
        self.api_key = settings.get("api_key") or os.getenv("LLM_API_KEY", "")
        self.model = settings.get("model") or os.getenv("LLM_MODEL", "qwen3.5-35b-a3b")
        self.timeout = float(settings.get("timeout") or os.getenv("LLM_TIMEOUT", "60"))

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat_text(self, prompt: str) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("LLM_BASE_URL and LLM_API_KEY are required for model calls.")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        return await self._post_chat(payload)

    async def chat_text_httpx(self, prompt: str) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("LLM_BASE_URL and LLM_API_KEY are required for model calls.")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
        return await self._post_chat_httpx(payload)

    async def chat_image(self, prompt: str, image_base64: str, mime_type: str = "image/png") -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("LLM_BASE_URL and LLM_API_KEY are required for model calls.")
        data_url = f"data:{mime_type};base64,{image_base64}"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "temperature": 0.1,
        }
        return await self._post_chat(payload)

    async def chat_image_httpx(self, prompt: str, image_base64: str, mime_type: str = "image/png") -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("LLM_BASE_URL and LLM_API_KEY are required for model calls.")
        data_url = f"data:{mime_type};base64,{image_base64}"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            "temperature": 0.1,
        }
        return await self._post_chat_httpx(payload)

    async def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_chat_requests, payload)

    async def _post_chat_httpx(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{self.base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self.timeout, trust_env=True) as client:
                response = await client.post(endpoint, headers=self._headers(), json=payload)
                self._raise_for_status(response)
                return response.json()
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Model API timeout after {self.timeout}s: {endpoint}") from exc
        except httpx.RequestError as exc:
            raise RuntimeError(f"Model API network error via httpx: {exc.__class__.__name__}: {exc}") from exc

    def _post_chat_requests(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{self.base_url}/chat/completions"
        try:
            response = requests.post(endpoint, headers=self._headers(), json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as exc:
            body = exc.response.text[:1200] if exc.response is not None else ""
            status = exc.response.status_code if exc.response is not None else "unknown"
            raise RuntimeError(f"Model API returned {status}: {body}") from exc
        except requests.Timeout as exc:
            raise RuntimeError(f"Model API timeout after {self.timeout}s: {endpoint}") from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Model API network error via requests: {exc.__class__.__name__}: {exc}") from exc

    def _raise_for_status(self, response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = response.text[:1200]
            raise RuntimeError(f"Model API returned {response.status_code}: {body}") from exc


def encode_file_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")
