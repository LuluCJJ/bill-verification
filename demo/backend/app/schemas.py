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


class DocumentItem(BaseModel):
    raw_key: str = ""
    raw_value: str = ""
    evidence: Evidence = Field(default_factory=Evidence)


class ExtractionResult(BaseModel):
    sample_id: str | None = None
    document_type: str = "unknown"
    document_items: list[DocumentItem] = Field(default_factory=list)
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
    template_id: str | None = None


class ModelSettings(BaseModel):
    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = 60


class ModelTestRequest(BaseModel):
    prompt: str = "请用一句话回复：模型连通测试成功。"
    image_base64: str | None = None
    mime_type: str = "image/png"


class ModelDiagnoseRequest(BaseModel):
    include_image: bool = False
    image_base64: str | None = None
    mime_type: str = "image/png"


class TemplateFieldConfig(BaseModel):
    field_id: str
    source_system_field: str = ""
    display_name: str = ""
    business_meaning: str = ""
    aliases: list[str] = Field(default_factory=list)
    position_hint: str = ""
    extraction_hint: str = ""


class FeedbackRequest(BaseModel):
    sample_id: str
    field: str
    action: Literal["confirm_match", "confirm_mismatch", "ai_error", "ignore", "submit_optimization"]
    corrected_value: str | None = None
    note: str | None = None


class CustomVerificationRequest(BaseModel):
    sample_id: str = "custom_input"
    template_id: str | None = None
    payment_instruction: dict[str, Any]
    extraction: ExtractionResult
