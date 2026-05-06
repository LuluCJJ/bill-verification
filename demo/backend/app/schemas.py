from typing import Any, Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["high", "medium", "low"]
CheckStatus = Literal["match", "mismatch", "missing_in_document", "document_only", "unchecked"]


class Evidence(BaseModel):
    page: int = 1
    text: str = ""
    region_hint: str = ""


class ExtractedField(BaseModel):
    normalized_field: str
    raw_label: str = ""
    raw_value: str = ""
    confidence: float = 0.0
    evidence: Evidence = Field(default_factory=Evidence)
    mapping_source: str = "ai"


class SpecialRisk(BaseModel):
    type: str
    text: str
    confidence: float = 0.0
    evidence: Evidence = Field(default_factory=Evidence)


class ExtractionResult(BaseModel):
    sample_id: str | None = None
    document_type: str = "unknown"
    extracted_fields: list[ExtractedField] = Field(default_factory=list)
    special_risks: list[SpecialRisk] = Field(default_factory=list)
    raw_model_output: Any | None = None


class VerificationItem(BaseModel):
    field: str
    display_name: str
    risk_level: RiskLevel
    status: CheckStatus
    system_value: Any = None
    document_value: Any = None
    message: str
    confidence: float = 0.0
    evidence: Evidence = Field(default_factory=Evidence)
    compare_type: str = "unchecked"


class VerificationResult(BaseModel):
    sample_id: str
    overall_status: Literal["pass", "review_required"]
    summary: dict[str, int]
    items: list[VerificationItem]
    extraction: ExtractionResult


class ModelTextTestRequest(BaseModel):
    prompt: str


class ModelImageTestRequest(BaseModel):
    prompt: str
    image_base64: str
    mime_type: str = "image/png"


class FeedbackRequest(BaseModel):
    sample_id: str
    field: str
    action: Literal["confirm_match", "confirm_mismatch", "ai_error", "ignore", "submit_optimization"]
    corrected_value: str | None = None
    note: str | None = None


class CustomVerificationRequest(BaseModel):
    sample_id: str = "custom_input"
    payment_instruction: dict[str, Any]
    extraction: ExtractionResult
