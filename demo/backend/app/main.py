import asyncio
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .comparator import verify
from .extractor import extract_with_model, extraction_from_static
from .model_client import ModelClient
from .schemas import CustomVerificationRequest, FeedbackRequest, ModelDiagnoseRequest, ModelImageTestRequest, ModelSettings, ModelTestRequest, ModelTextTestRequest
from .storage import ROOT, ensure_runtime_dirs, load_config, load_local_config, load_sample, load_samples, save_config, save_feedback, save_local_config


app = FastAPI(title="Bill Verification Demo", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_runtime_dirs()
app.mount("/samples/documents", StaticFiles(directory=ROOT / "data" / "samples" / "documents"), name="sample_documents")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now().isoformat(timespec="seconds")}


@app.get("/api/samples")
def samples() -> list[dict]:
    return load_samples()


@app.get("/api/samples/{sample_id}")
def sample_detail(sample_id: str) -> dict:
    try:
        return load_sample(sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/verify/{sample_id}")
def verify_sample(sample_id: str) -> dict:
    try:
        sample = load_sample(sample_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    extraction = extraction_from_static(sample["expected_result"])
    result = verify(sample_id, sample["payment_instruction"], extraction, load_config("field_schema.json"))
    return result.model_dump()


@app.post("/api/verify-custom")
def verify_custom(payload: CustomVerificationRequest) -> dict:
    result = verify(payload.sample_id, payload.payment_instruction, payload.extraction, load_config("field_schema.json"))
    return result.model_dump()


@app.get("/api/config/{name}")
def get_config(name: str):
    if name not in {"field_schema.json", "field_aliases.json", "mapping_rules.json"}:
        raise HTTPException(status_code=400, detail="Unsupported config file.")
    return load_config(name)


@app.put("/api/config/{name}")
def put_config(name: str, payload: dict):
    if name not in {"field_schema.json", "field_aliases.json", "mapping_rules.json"}:
        raise HTTPException(status_code=400, detail="Unsupported config file.")
    save_config(name, payload)
    return {"status": "saved", "name": name}


@app.post("/api/feedback")
def feedback(payload: FeedbackRequest):
    path = save_feedback(payload.model_dump())
    return {"status": "saved", "path": str(path.relative_to(ROOT))}


@app.post("/api/model/test-text")
async def test_model_text(payload: ModelTextTestRequest):
    client = ModelClient(load_local_config().get("model_settings", {}))
    try:
        return await client.chat_text(payload.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/model/test-image")
async def test_model_image(payload: ModelImageTestRequest):
    client = ModelClient(load_local_config().get("model_settings", {}))
    try:
        return await client.chat_image(payload.prompt, payload.image_base64, payload.mime_type)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/model/settings")
def get_model_settings() -> dict:
    settings = load_local_config().get("model_settings", {})
    return {
        "base_url": settings.get("base_url", ""),
        "model": settings.get("model", ""),
        "timeout": settings.get("timeout", 60),
        "api_key_set": bool(settings.get("api_key")),
        "api_key": "",
    }


@app.put("/api/model/settings")
def put_model_settings(payload: ModelSettings) -> dict:
    local_config = load_local_config()
    existing = local_config.get("model_settings", {})
    api_key = payload.api_key if payload.api_key is not None and payload.api_key != "" else existing.get("api_key", "")
    local_config["model_settings"] = {
        "base_url": payload.base_url.rstrip("/"),
        "model": payload.model,
        "api_key": api_key,
        "timeout": payload.timeout,
    }
    save_local_config(local_config)
    return {"status": "saved", "api_key_set": bool(api_key)}


@app.post("/api/model/test")
async def test_saved_model(payload: ModelTestRequest):
    client = ModelClient(load_local_config().get("model_settings", {}))
    try:
        if payload.image_base64:
            return await client.chat_image(payload.prompt, payload.image_base64, payload.mime_type)
        return await client.chat_text(payload.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _model_step(name: str, ok: bool, message: str, **extra) -> dict:
    return {"name": name, "ok": ok, "message": message, **extra}


async def _with_retry(action, attempts: int = 2) -> tuple[bool, dict | str, int]:
    last_error = ""
    for attempt in range(1, attempts + 1):
        try:
            return True, await action(), attempt
        except Exception as exc:
            last_error = str(exc)
            if attempt < attempts:
                await asyncio.sleep(1)
    return False, last_error, attempts


@app.post("/api/model/diagnose")
async def diagnose_model(payload: ModelDiagnoseRequest) -> dict:
    settings = load_local_config().get("model_settings", {})
    client = ModelClient(settings)
    report = {
        "summary": "诊断完成",
        "steps": [
            _model_step("本地后端", True, "FastAPI 服务可访问。"),
            _model_step(
                "模型配置",
                client.configured,
                "已读取模型配置。" if client.configured else "缺少接口地址或 API Key，请先在系统设置保存模型配置。",
                base_url=client.base_url,
                model=client.model,
                timeout=client.timeout,
                api_key_set=bool(client.api_key),
                endpoint=f"{client.base_url}/chat/completions" if client.base_url else "",
            ),
        ],
    }
    if not client.configured:
        report["summary"] = "配置未完成"
        return report

    text_prompt = "请用一句话回复：模型文本链路诊断成功。"
    text_ok, text_result, text_attempts = await _with_retry(lambda: client.chat_text(text_prompt))
    if text_ok:
        content = text_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        report["steps"].append(_model_step("文本模型调用", True, "正式后端已使用 test_model_api.py 同款 requests 通道，请求成功。", attempts=text_attempts, response_preview=content[:200]))
    else:
        report["steps"].append(_model_step("文本模型调用", False, text_result, attempts=text_attempts))

    httpx_ok, httpx_result, httpx_attempts = await _with_retry(lambda: client.chat_text_httpx(text_prompt))
    if httpx_ok:
        content = httpx_result.get("choices", [{}])[0].get("message", {}).get("content", "")
        report["steps"].append(_model_step("httpx 对照调用", True, "httpx 对照通道请求成功。", attempts=httpx_attempts, response_preview=content[:200]))
    else:
        report["steps"].append(_model_step("httpx 对照调用", False, httpx_result, attempts=httpx_attempts))

    if text_ok and not httpx_ok:
        report["steps"].append(_model_step("差异判断", True, "requests 可用但 httpx 对照失败。配置和模型权限没问题，正式链路已切换为 requests。"))
    elif not text_ok:
        report["summary"] = "文本模型调用失败"
        report["steps"].append(_model_step("差异判断", False, "后端进程内 requests 调用失败。若外部 test_model_api.py 成功，优先检查网页保存的配置、启动后端的环境变量/代理、Python 解释器和工作目录。"))
        return report

    if payload.include_image:
        if not payload.image_base64:
            report["steps"].append(_model_step("图片模型调用", False, "未提供图片，无法诊断多模态链路。"))
            report["summary"] = "图片诊断缺少图片"
            return report
        image_ok, image_result, image_attempts = await _with_retry(lambda: client.chat_image(
                "请用一句话说明你看到了这张付款文件图片，并识别一个关键字段。",
                payload.image_base64,
                payload.mime_type,
            ))
        if image_ok:
            content = image_result.get("choices", [{}])[0].get("message", {}).get("content", "")
            report["steps"].append(_model_step("图片模型调用", True, "图片请求成功。", attempts=image_attempts, mime_type=payload.mime_type, response_preview=content[:300]))
        else:
            report["summary"] = "图片模型调用失败"
            report["steps"].append(_model_step("图片模型调用", False, image_result, attempts=image_attempts, mime_type=payload.mime_type))
            return report
    else:
        report["steps"].append(_model_step("图片模型调用", True, "本次未执行图片诊断。勾选图片诊断或点击测试图片可验证多模态链路。", skipped=True))

    return report


@app.post("/api/extract-with-model")
async def extract_model(payload: ModelImageTestRequest):
    try:
        extraction = await extract_with_model(payload.image_base64, payload.mime_type)
        return extraction.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


app.mount("/", StaticFiles(directory=ROOT / "demo" / "frontend", html=True), name="frontend")
