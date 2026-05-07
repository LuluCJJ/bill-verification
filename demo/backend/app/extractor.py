import json
import re
from typing import Any

from .model_client import ModelClient
from .schemas import ExtractionResult
from .storage import load_config, load_local_config


EXTRACTION_PROMPT = """
你是权签票据一致性预审助手。请从票据图片中提取可见字段，并映射到给定标准字段。

要求：
1. 只提取票面可见信息，不要补全或臆测。
2. 如果不确定，保留低置信度候选。
3. 输出严格 JSON，不要 Markdown。
4. 字段使用 normalized_field 表示标准字段。
5. 每个字段保留 raw_label、raw_value、confidence、evidence。
6. 特殊票面风险如 Not Negotiable、A/C Payee Only、不可转让，放入 special_risks。
7. 不要用项目符号、解释文字或自然语言总结，只返回一个 JSON 对象。

JSON 格式示例：
{{
  "document_type": "check",
  "extracted_fields": [
    {{"normalized_field": "beneficiary_name", "raw_label": "收款人", "raw_value": "上海星河供应链有限公司", "confidence": 0.9, "evidence": {{"page": 1, "text": "收款人：上海星河供应链有限公司", "region_hint": ""}}}}
  ],
  "special_risks": [
    {{"type": "non_transferable", "text": "不可转让", "confidence": 0.9, "evidence": {{"page": 1, "text": "不可转让", "region_hint": ""}}}}
  ]
}}

标准字段包括：
付款方名称 payer_name，付款方账号 payer_account，付款方银行 payer_bank，收款方名称 beneficiary_name，
收款方账号 beneficiary_account，收款方银行 beneficiary_bank，SWIFT/BIC swift_code，IBAN iban，
币种 currency，金额 amount，大写金额 amount_in_words，付款日期 payment_date，付款用途 purpose，费用承担 charge_bearer。

业务配置补充：
{business_config}
"""


def build_extraction_prompt() -> str:
    aliases = load_config("field_aliases.json")
    rules = load_config("mapping_rules.json")
    parts = []
    for field, names in aliases.items():
        if names:
            parts.append(f"- {field} 的票面常见叫法：{', '.join(names)}")
    for rule in rules.get("template_rules", []):
        hints = rule.get("hints", {})
        if hints:
            parts.append(f"- 模板 {rule.get('template_id', 'unknown')} 位置提示：" + "; ".join(f"{k}: {v}" for k, v in hints.items()))
    business_config = "\n".join(parts) if parts else "无"
    return EXTRACTION_PROMPT.format(business_config=business_config)


def parse_model_json(payload: dict[str, Any]) -> dict[str, Any]:
    content = model_content(payload)
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    match = re.search(r"\{.*\}", str(content), re.S)
    if not match:
        return parse_plain_text_extraction(str(content))
    return json.loads(match.group(0))


def model_content(payload: dict[str, Any]) -> Any:
    return payload["choices"][0]["message"]["content"]


PLAIN_LABEL_MAP = {
    "收款人": "beneficiary_name",
    "收款方": "beneficiary_name",
    "受益人": "beneficiary_name",
    "beneficiary": "beneficiary_name",
    "金额": "amount",
    "付款金额": "amount",
    "amount": "amount",
    "币种": "currency",
    "currency": "currency",
    "收款账号": "beneficiary_account",
    "收款人账号": "beneficiary_account",
    "受益人账号": "beneficiary_account",
    "beneficiary account": "beneficiary_account",
    "付款人": "payer_name",
    "付款方": "payer_name",
    "payer": "payer_name",
    "付款人账号": "payer_account",
    "付款方账号": "payer_account",
    "payer account": "payer_account",
    "用途": "purpose",
    "付款用途": "purpose",
    "purpose": "purpose",
    "出票日期": "payment_date",
    "付款日期": "payment_date",
    "日期": "payment_date",
    "date": "payment_date",
    "支票号码": "check_number",
    "票据号码": "check_number",
    "备注": "note",
}


def parse_plain_text_extraction(content: str) -> dict[str, Any]:
    fields = []
    special_risks = []
    for raw_line in content.splitlines():
        line = raw_line.strip().lstrip("-*•").strip()
        if not line or ("：" not in line and ":" not in line):
            continue
        label, value = re.split(r"[:：]", line, maxsplit=1)
        label = label.strip().strip("*").strip()
        value = value.strip().strip("*").strip()
        normalized = map_plain_label(label)
        if not normalized or not value:
            continue
        if normalized in {"note"} and is_special_risk(value):
            special_risks.append(
                {
                    "type": "non_transferable",
                    "text": value,
                    "confidence": 0.85,
                    "evidence": {"page": 1, "text": line, "region_hint": ""},
                }
            )
            continue
        if normalized == "check_number":
            continue
        fields.append(
            {
                "normalized_field": normalized,
                "raw_label": label,
                "raw_value": value,
                "confidence": 0.82,
                "evidence": {"page": 1, "text": line, "region_hint": ""},
                "mapping_source": "plain_text_fallback",
            }
        )
        if is_special_risk(value):
            special_risks.append(
                {
                    "type": "non_transferable",
                    "text": value,
                    "confidence": 0.85,
                    "evidence": {"page": 1, "text": line, "region_hint": ""},
                }
            )
    return {"document_type": "unknown", "extracted_fields": fields, "special_risks": special_risks}


def map_plain_label(label: str) -> str:
    clean = re.sub(r"\s+", " ", label).strip().lower()
    if clean in PLAIN_LABEL_MAP:
        return PLAIN_LABEL_MAP[clean]
    for key, field in PLAIN_LABEL_MAP.items():
        if key.lower() in clean:
            return field
    return ""


def is_special_risk(value: str) -> bool:
    raw = value.lower()
    return "不可转让" in raw or "not negotiable" in raw or "account payee" in raw or "a/c payee" in raw


def normalize_extraction_payload(parsed: dict[str, Any], raw_payload: dict[str, Any]) -> dict[str, Any]:
    fields = parsed.get("extracted_fields") or parsed.get("fields") or []
    normalized_fields = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        evidence = field.get("evidence") or {}
        if isinstance(evidence, str):
            evidence = {"page": 1, "text": evidence, "region_hint": ""}
        else:
            evidence = {
                "page": evidence.get("page", 1),
                "text": evidence.get("text", ""),
                "region_hint": evidence.get("region_hint", evidence.get("region", "")),
            }
        normalized_fields.append(
            {
                "normalized_field": field.get("normalized_field") or field.get("field") or "",
                "raw_label": field.get("raw_label", ""),
                "raw_value": field.get("raw_value", field.get("value", "")),
                "confidence": normalize_confidence(field.get("confidence", 0.0)),
                "evidence": evidence,
                "mapping_source": field.get("mapping_source", "ai"),
            }
        )

    special_risks = []
    for risk in parsed.get("special_risks", []):
        if isinstance(risk, str):
            risk = {"type": "special_risk", "text": risk, "confidence": 0.6, "evidence": risk}
        if not isinstance(risk, dict):
            continue
        evidence = risk.get("evidence") or {}
        if isinstance(evidence, str):
            evidence = {"page": 1, "text": evidence, "region_hint": ""}
        special_risks.append(
            {
                "type": normalize_special_risk_type(risk.get("type", "special_risk"), risk.get("text", "")),
                "text": risk.get("text", ""),
                "confidence": normalize_confidence(risk.get("confidence", 0.0)),
                "evidence": evidence,
            }
        )

    return {
        "sample_id": parsed.get("sample_id"),
        "document_type": parsed.get("document_type", "unknown"),
        "extracted_fields": normalized_fields,
        "special_risks": special_risks,
        "raw_model_output": raw_payload,
    }


def normalize_confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    text = str(value or "").strip().lower()
    mapping = {"high": 0.9, "medium": 0.6, "low": 0.3, "高": 0.9, "中": 0.6, "低": 0.3}
    if text in mapping:
        return mapping[text]
    try:
        number = float(text)
        if number > 1:
            number = number / 100
        return max(0.0, min(1.0, number))
    except ValueError:
        return 0.0


def normalize_special_risk_type(value: Any, text: Any) -> str:
    raw = f"{value or ''} {text or ''}".lower()
    if "不可转让" in raw or "not negotiable" in raw or "a/c payee" in raw or "account payee" in raw:
        return "non_transferable"
    return str(value or "special_risk")


async def extract_with_model(image_base64: str, mime_type: str = "image/png") -> ExtractionResult:
    client = ModelClient(load_local_config().get("model_settings", {}))
    payload = await client.chat_image(build_extraction_prompt(), image_base64, mime_type)
    parsed = parse_model_json(payload)
    extraction = ExtractionResult.model_validate(normalize_extraction_payload(parsed, payload))
    if not extraction.extracted_fields:
        raise ValueError("Model returned zero extracted fields. 图片已成功送达模型，但模型没有按结构化要求返回字段，请重试或检查模型输出。")
    return extraction


def extraction_from_static(expected_result: dict[str, Any]) -> ExtractionResult:
    return ExtractionResult.model_validate(expected_result)
