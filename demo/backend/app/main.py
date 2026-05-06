from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .comparator import verify
from .extractor import extraction_from_static
from .model_client import ModelClient
from .schemas import CustomVerificationRequest, FeedbackRequest, ModelImageTestRequest, ModelTextTestRequest
from .storage import ROOT, ensure_runtime_dirs, load_config, load_sample, load_samples, save_config, save_feedback


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
    client = ModelClient()
    try:
        return await client.chat_text(payload.prompt)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/model/test-image")
async def test_model_image(payload: ModelImageTestRequest):
    client = ModelClient()
    try:
        return await client.chat_image(payload.prompt, payload.image_base64, payload.mime_type)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


app.mount("/", StaticFiles(directory=ROOT / "demo" / "frontend", html=True), name="frontend")
