import base64
import os
from pathlib import Path
from typing import Any

import httpx


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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()

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
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/chat/completions", headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()


def encode_file_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")
