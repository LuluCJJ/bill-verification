import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
SAMPLES_DIR = DATA_DIR / "samples"
RESULTS_DIR = DATA_DIR / "results"
FEEDBACK_DIR = DATA_DIR / "feedback"


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
