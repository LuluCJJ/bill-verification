import argparse
import base64
import io
import json
import os
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
LOCAL_CONFIG = ROOT / "config.local.json"


def load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def load_local_model_settings() -> dict[str, Any]:
    if not LOCAL_CONFIG.exists():
        return {}
    return json.loads(LOCAL_CONFIG.read_text(encoding="utf-8")).get("model_settings", {})


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def make_tiny_png() -> bytes:
    return png_bytes(Image.new("RGB", (32, 32), "#ffffff"))


def make_text_card_png() -> bytes:
    image = Image.new("RGB", (420, 180), "#ffffff")
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 408, 168), outline="#1f2937", width=2)
    draw.text((28, 34), "PAYMENT TEST", fill="#111827")
    draw.text((28, 72), "BENEFICIARY: ACME LIMITED", fill="#111827")
    draw.text((28, 108), "AMOUNT: USD 123.45", fill="#111827")
    return png_bytes(image)


def load_resized_sample(max_width: int = 640) -> bytes:
    path = ROOT / "data" / "samples" / "documents" / "model_test_tt.png"
    image = Image.open(path).convert("RGB")
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, int(image.height * ratio)))
    return png_bytes(image)


def load_original_sample() -> bytes:
    return (ROOT / "data" / "samples" / "documents" / "model_test_tt.png").read_bytes()


def build_messages(prompt: str, image_bytes: bytes, mime: str, style: str) -> list[dict[str, Any]]:
    data_url = f"data:{mime};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    if style == "image_url_string":
        image_part: Any = {"type": "image_url", "image_url": data_url}
    else:
        image_part = {"type": "image_url", "image_url": {"url": data_url}}
    return [{"role": "user", "content": [{"type": "text", "text": prompt}, image_part]}]


def request_chat(base_url: str, api_key: str, model: str, messages: list[dict[str, Any]], timeout: int) -> dict[str, Any]:
    response = requests.post(
        base_url.rstrip("/") + "/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.1},
        timeout=timeout,
    )
    if response.status_code >= 400:
        return {"ok": False, "status_code": response.status_code, "body": response.text[:800]}
    return {"ok": True, "status_code": response.status_code, "body": response.json()}


def main() -> None:
    load_env_file()
    local_settings = load_local_model_settings()
    parser = argparse.ArgumentParser(description="Probe image access through the OpenAI-compatible chat/completions API.")
    parser.add_argument("--base-url", default=os.getenv("LLM_BASE_URL") or local_settings.get("base_url") or "https://ark.cn-beijing.volces.com/api/coding/v3")
    parser.add_argument("--api-key", default=os.getenv("LLM_API_KEY") or local_settings.get("api_key") or "")
    parser.add_argument("--model", default=os.getenv("LLM_MODEL") or local_settings.get("model") or "Doubao-Seed-2.0-pro")
    parser.add_argument("--timeout", type=int, default=int(float(os.getenv("LLM_TIMEOUT") or local_settings.get("timeout") or 60)))
    parser.add_argument("--style", choices=["image_url_object", "image_url_string"], default="image_url_object")
    args = parser.parse_args()

    if not args.base_url or not args.api_key:
        raise SystemExit("Please set model settings in config.local.json or LLM_BASE_URL/LLM_API_KEY environment variables.")

    cases = [
        ("tiny_png", make_tiny_png(), "image/png", "请只回答：是否看到了图片。"),
        ("text_card_png", make_text_card_png(), "image/png", "请识别图片中的金额。"),
        ("sample_resized_png", load_resized_sample(), "image/png", "请识别付款文件中的金额、币种和收款方。"),
        ("sample_original_png", load_original_sample(), "image/png", "请识别付款文件中的金额、币种和收款方。"),
    ]

    print(f"endpoint={args.base_url.rstrip('/')}/chat/completions")
    print(f"model={args.model}")
    print(f"style={args.style}")
    print("api_key_set=true")
    print()
    for name, image_bytes, mime, prompt in cases:
        result = request_chat(args.base_url, args.api_key, args.model, build_messages(prompt, image_bytes, mime, args.style), args.timeout)
        print(f"## {name}")
        print(f"bytes={len(image_bytes)} mime={mime} status={result['status_code']} ok={result['ok']}")
        if result["ok"]:
            content = result["body"].get("choices", [{}])[0].get("message", {}).get("content", "")
            print(content[:500])
        else:
            print(result["body"])
        print()


if __name__ == "__main__":
    main()
