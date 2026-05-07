import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
RESULTS_DIR = DATA_DIR / "results"
FEEDBACK_DIR = DATA_DIR / "feedback"
LOCAL_CONFIG_PATH = ROOT / "config.local.json"


def ensure_runtime_dirs() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_samples() -> list[dict[str, Any]]:
    return read_json(DATA_DIR / "samples.json")


def resolve_repo_path(path: str) -> Path:
    return ROOT / path


def load_sample(sample_id: str) -> dict[str, Any]:
    for sample in load_samples():
        if sample["id"] == sample_id:
            payload = dict(sample)
            payload["payment_instruction"] = read_json(resolve_repo_path(sample["payment_instruction_path"]))
            payload["expected_result"] = read_json(resolve_repo_path(sample["expected_result_path"]))
            return payload
    raise KeyError(f"Unknown sample id: {sample_id}")


def load_config(name: str) -> Any:
    return read_json(CONFIG_DIR / name)


def save_config(name: str, data: Any) -> None:
    write_json(CONFIG_DIR / name, data)


def save_feedback(payload: dict[str, Any]) -> Path:
    ensure_runtime_dirs()
    existing = []
    path = FEEDBACK_DIR / f"{payload['sample_id']}.json"
    if path.exists():
        existing = read_json(path)
    existing.append(payload)
    write_json(path, existing)
    return path


def load_feedback_entries() -> list[dict[str, Any]]:
    ensure_runtime_dirs()
    entries: list[dict[str, Any]] = []
    for path in sorted(FEEDBACK_DIR.glob("*.json")):
        payload = read_json(path)
        if isinstance(payload, list):
            for item in payload:
                item = dict(item)
                item.setdefault("source_file", path.name)
                entries.append(item)
        elif isinstance(payload, dict):
            payload.setdefault("source_file", path.name)
            entries.append(payload)
    return entries


def load_local_config() -> dict[str, Any]:
    if not LOCAL_CONFIG_PATH.exists():
        return {}
    return read_json(LOCAL_CONFIG_PATH)


def save_local_config(data: dict[str, Any]) -> None:
    write_json(LOCAL_CONFIG_PATH, data)
