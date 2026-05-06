import argparse
import base64
import json
import os
from pathlib import Path

import requests


def load_env_file() -> None:
    env_path = Path(".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def request_chat(base_url: str, api_key: str, model: str, messages: list, timeout: int) -> dict:
    url = base_url.rstrip("/") + "/chat/completions"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.1},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def build_messages(args) -> list:
    if not args.image:
        return [{"role": "user", "content": args.prompt}]
    image_path = Path(args.image)
    image_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
    mime = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    return [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": args.prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_base64}"}},
            ],
        }
    ]


def main() -> None:
    load_env_file()
    parser = argparse.ArgumentParser(description="Test OpenAI-compatible text or vision API.")
    parser.add_argument("--base-url", default=os.getenv("LLM_BASE_URL", ""))
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY", ""))
    parser.add_argument("--model", default=os.getenv("LLM_MODEL", "qwen3.5-35b-a3b"))
    parser.add_argument("--prompt", default="请用一句话回复：模型连通测试成功。")
    parser.add_argument("--image", help="Optional local image path for vision test.")
    parser.add_argument("--timeout", type=int, default=int(os.getenv("LLM_TIMEOUT", "60")))
    args = parser.parse_args()

    if not args.base_url or not args.api_key:
        raise SystemExit("Please set LLM_BASE_URL and LLM_API_KEY in environment or .env.")

    result = request_chat(args.base_url, args.api_key, args.model, build_messages(args), args.timeout)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
