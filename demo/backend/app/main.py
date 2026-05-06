from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .comparator import verify
from .extractor import extract_with_model, extraction_from_static
from .model_client import ModelClient
from .schemas import CustomVerificationRequest, FeedbackRequest, ModelImageTestRequest, ModelSettings, ModelTestRequest, ModelTextTestRequest
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


@app.post("/api/extract-with-model")
async def extract_model(payload: ModelImageTestRequest):
    try:
        extraction = await extract_with_model(payload.image_base64, payload.mime_type)
        return extraction.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


app.mount("/", StaticFiles(directory=ROOT / "demo" / "frontend", html=True), name="frontend")
