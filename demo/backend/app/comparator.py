import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from .schemas import Evidence, ExtractionResult, VerificationItem, VerificationResult


CURRENCY_ALIASES = {
    "USD": {"USD", "US DOLLAR", "US DOLLARS", "$"},
    "CNY": {"CNY", "RMB", "人民币", "人民币元", "￥"},
    "EUR": {"EUR", "EURO", "EUROS", "€"},
    "HKD": {"HKD", "HK DOLLAR", "HONG KONG DOLLAR"},
}


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).upper().strip()
    text = re.sub(r"[\s,，。.\-_/\\()（）:：]+", "", text)
    text = text.replace("有限公司", "公司").replace("LIMITED", "LTD")
    return text


def normalize_account(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def normalize_amount(value: Any) -> Decimal | None:
    text = str(value or "")
    text = re.sub(r"[^0-9.\-]", "", text)
    if not text:
        return None
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def normalize_currency(value: Any) -> str:
    text = str(value or "").upper().strip()
    for code, aliases in CURRENCY_ALIASES.items():
        if text == code or text in aliases:
            return code
    return text


def normalize_date(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("年", "-").replace("月", "-").replace("日", "")
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def compare_values(compare_type: str, system_value: Any, document_value: Any) -> bool:
    if compare_type == "amount":
        return normalize_amount(system_value) == normalize_amount(document_value)
    if compare_type in {"account", "bank_name", "normalized_text"}:
        return normalize_text(system_value) == normalize_text(document_value) if compare_type != "account" else normalize_account(system_value) == normalize_account(document_value)
    if compare_type == "currency":
        return normalize_currency(system_value) == normalize_currency(document_value)
    if compare_type == "date":
        return normalize_date(system_value) == normalize_date(document_value)
    if compare_type == "contains_text":
        sys_text = normalize_text(system_value)
        doc_text = normalize_text(document_value)
        return bool(sys_text and doc_text and (sys_text in doc_text or doc_text in sys_text))
    return normalize_text(system_value) == normalize_text(document_value)


def verify(sample_id: str, payment_instruction: dict[str, Any], extraction: ExtractionResult, field_schema: dict[str, Any]) -> VerificationResult:
    by_field = {}
    for field in extraction.extracted_fields:
        current = by_field.get(field.normalized_field)
        if current is None or field.confidence > current.confidence:
            by_field[field.normalized_field] = field

    items: list[VerificationItem] = []
    for field, meta in field_schema.items():
        if meta.get("document_presence") == "special_risk":
            continue
        system_value = payment_instruction.get(field)
        document_field = by_field.get(field)
        if system_value in (None, "") and document_field is None:
            continue

        display_name = meta.get("display_name", field)
        compare_type = meta.get("compare_type", "normalized_text")
        risk_level = meta.get("risk_level", "medium")

        if document_field is None:
            if meta.get("document_presence") == "optional":
                continue
            items.append(
                VerificationItem(
                    field=field,
                    display_name=display_name,
                    risk_level=risk_level,
                    status="missing_in_document",
                    system_value=system_value,
                    document_value=None,
                    message=f"系统存在{display_name}，票面未识别到对应字段",
                    confidence=0.0,
                    compare_type=compare_type,
                )
            )
            continue

        matched = compare_values(compare_type, system_value, document_field.raw_value)
        items.append(
            VerificationItem(
                field=field,
                display_name=display_name,
                risk_level=risk_level,
                status="match" if matched else "mismatch",
                system_value=system_value,
                document_value=document_field.raw_value,
                message=f"{display_name}一致" if matched else f"{display_name}与系统值不一致",
                confidence=document_field.confidence,
                evidence=document_field.evidence,
                compare_type=compare_type,
            )
        )

    for risk in extraction.special_risks:
        system_value = payment_instruction.get(risk.type)
        matched = bool(system_value) and compare_values("normalized_text", system_value, risk.text)
        items.append(
            VerificationItem(
                field=risk.type,
                display_name=field_schema.get(risk.type, {}).get("display_name", risk.type),
                risk_level=field_schema.get(risk.type, {}).get("risk_level", "low"),
                status="match" if matched else "document_only",
                system_value=system_value,
                document_value=risk.text,
                message=f"特殊票面提示一致：{risk.text}" if matched else f"票面出现特殊提示：{risk.text}",
                confidence=risk.confidence,
                evidence=risk.evidence,
                compare_type="special_presence",
            )
        )

    summary = {"high": 0, "medium": 0, "low": 0, "match": 0}
    for item in items:
        if item.status == "match":
            summary["match"] += 1
        else:
            summary[item.risk_level] += 1

    overall = "review_required" if summary["high"] or summary["medium"] or summary["low"] else "pass"
    return VerificationResult(sample_id=sample_id, overall_status=overall, summary=summary, items=items, extraction=extraction)
