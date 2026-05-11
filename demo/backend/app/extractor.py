import json
import re
from typing import Any

from .model_client import ModelClient
from .schemas import ExtractionResult
from .storage import load_config, load_local_config, load_template_ai_config


EXTRACTION_PROMPT = """
你是权签票据一致性预审助手。请从票据图片中按“当前模板已配置字段清单”做定向提取。

要求：
1. 只围绕“当前模板已配置字段清单”提取，不要新增未配置字段。
2. 只提取票面可见信息，不要补全、改写、翻译或标准化票面文字。
3. document_items 保存票面原始 Key/Value，raw_key 和 raw_value 必须尽量逐字照抄票面；如果能判断它对应哪个配置字段，同时填写 mapped_field。
4. extracted_fields 保存定向提取结果：raw_label/raw_value 仍然照抄票面，normalized_field 必须来自已配置字段 field_id。
5. 如果某个配置字段在票面中找不到，不要编造值；可以不返回该字段，后续系统会按规则判断缺失。
6. 如果不确定，保留低置信度候选，并在 mapping_source 写 "ai_uncertain"。
7. 输出严格 JSON，不要 Markdown。
8. 特殊票面风险如 Not Negotiable、A/C Payee Only、不可转让，放入 special_risks。
9. 不要用项目符号、解释文字或自然语言总结，只返回一个 JSON 对象。

JSON 格式示例：
{{
  "document_type": "check",
  "document_items": [
    {{"raw_key": "收款人", "raw_value": "上海星河供应链有限公司", "mapped_field": "beneficiary_name", "evidence": {{"page": 1, "text": "收款人：上海星河供应链有限公司", "region_hint": ""}}}},
    {{"raw_key": "收款银行", "raw_value": "中国工商银行上海分行", "mapped_field": "beneficiary_bank", "evidence": {{"page": 1, "text": "收款银行：中国工商银行上海分行", "region_hint": ""}}}}
  ],
  "extracted_fields": [
    {{"normalized_field": "beneficiary_name", "raw_label": "收款人", "raw_value": "上海星河供应链有限公司", "confidence": 0.9, "mapping_source": "ai", "evidence": {{"page": 1, "text": "收款人：上海星河供应链有限公司", "region_hint": ""}}}}
  ],
  "special_risks": [
    {{"type": "non_transferable", "text": "不可转让", "confidence": 0.9, "evidence": {{"page": 1, "text": "不可转让", "region_hint": ""}}}}
  ]
}}

当前模板已配置字段清单：
{target_fields}
"""


def configured_template(template_id: str | None) -> dict[str, Any]:
    template = load_template_ai_config(template_id)
    if not template.get("ai_enabled") or template.get("status") != "published":
        raise ValueError(f"Template {template_id} has no published AI field configuration. AI pre-audit will not start.")
    if not template.get("fields"):
        raise ValueError(f"Template {template_id} has no configured target fields. AI pre-audit will not start.")
    return template


def configured_field_ids(template: dict[str, Any]) -> set[str]:
    return {str(field.get("field_id")) for field in template.get("fields", []) if field.get("field_id")}


def configured_field_meta(template_id: str | None, field_id: str) -> dict[str, Any]:
    if not template_id or not field_id:
        return {}
    try:
        template = configured_template(template_id)
    except (FileNotFoundError, KeyError, ValueError):
        return {}
    for field in template.get("fields", []):
        if field.get("field_id") == field_id:
            return field
    return {}


def build_extraction_prompt(template_id: str | None) -> str:
    template = configured_template(template_id)
    parts = [
        f"模板ID：{template.get('template_id')}",
        f"模板名称：{template.get('name', '')}",
        f"票据类型：{template.get('document_type', '')}",
        f"国家/区域：{template.get('country', '')}",
        "",
        "字段配置：",
    ]
    for field in template.get("fields", []):
        aliases = "、".join(field.get("aliases", [])) or "无"
        ai_instruction = field_ai_instruction(field)
        parts.append(
            "\n".join(
                [
                    f"- field_id: {field.get('field_id')}",
                    f"  系统来源字段: {field.get('source_system_field', '')}",
                    f"  展示名称: {field.get('display_name', '')}",
                    f"  票面别名: {aliases}",
                    f"  AI识别说明: {ai_instruction}",
                ]
            )
        )
    return EXTRACTION_PROMPT.format(target_fields="\n".join(parts))


def field_ai_instruction(field: dict[str, Any]) -> str:
    explicit = str(field.get("ai_instruction", "") or "").strip()
    if explicit:
        return explicit
    legacy_parts = [
        str(field.get("business_meaning", "") or "").strip(),
        str(field.get("position_hint", "") or "").strip(),
        str(field.get("extraction_hint", "") or "").strip(),
    ]
    return " ".join(part for part in legacy_parts if part)


def parse_model_json(payload: dict[str, Any], template_id: str | None = None) -> dict[str, Any]:
    content = model_content(payload)
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    match = re.search(r"\{.*\}", str(content), re.S)
    if not match:
        return parse_plain_text_extraction(str(content), template_id)
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


def parse_plain_text_extraction(content: str, template_id: str | None = None) -> dict[str, Any]:
    document_items = []
    fields = []
    special_risks = []
    for raw_line in content.splitlines():
        line = raw_line.strip().lstrip("-*•").strip()
        if not line or ("：" not in line and ":" not in line):
            continue
        label, value = re.split(r"[:：]", line, maxsplit=1)
        label = label.strip().strip("*").strip()
        value = value.strip().strip("*").strip()
        document_items.append({"raw_key": label, "raw_value": value, "evidence": {"page": 1, "text": line, "region_hint": ""}})
        normalized = map_plain_label(label, template_id)
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
    return {"document_type": "unknown", "document_items": document_items, "extracted_fields": fields, "special_risks": special_risks}


def map_plain_label(label: str, template_id: str | None = None) -> str:
    clean = re.sub(r"\s+", " ", label).strip().lower()
    if template_id:
        try:
            template = configured_template(template_id)
            contains_candidates: list[tuple[int, str]] = []
            for field in template.get("fields", []):
                names = [field.get("display_name", ""), field.get("field_id", ""), *field.get("aliases", [])]
                for name in names:
                    alias = re.sub(r"\s+", " ", str(name)).strip().lower()
                    if alias and clean == alias:
                        return str(field.get("field_id", ""))
                    if alias and alias in clean:
                        contains_candidates.append((len(alias), str(field.get("field_id", ""))))
            if contains_candidates:
                contains_candidates.sort(reverse=True)
                return contains_candidates[0][1]
        except (FileNotFoundError, KeyError, ValueError):
            pass
    if clean in PLAIN_LABEL_MAP:
        return PLAIN_LABEL_MAP[clean]
    for key, field in PLAIN_LABEL_MAP.items():
        if key.lower() in clean:
            return field
    try:
        aliases = load_config("field_aliases.json")
    except FileNotFoundError:
        aliases = {}
    for field, names in aliases.items():
        for name in names:
            alias = re.sub(r"\s+", " ", str(name)).strip().lower()
            if alias and (clean == alias or alias in clean):
                return field
    return ""


def is_special_risk(value: str) -> bool:
    raw = value.lower()
    return "不可转让" in raw or "not negotiable" in raw or "account payee" in raw or "a/c payee" in raw


def normalize_extraction_payload(parsed: dict[str, Any], raw_payload: dict[str, Any], allowed_fields: set[str] | None = None, template_id: str | None = None) -> dict[str, Any]:
    fields = parsed.get("extracted_fields") or parsed.get("mapped_fields") or parsed.get("fields") or []
    document_items = normalize_document_items(parsed, fields, template_id, allowed_fields)
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
        raw_label = field.get("raw_label", field.get("raw_key", ""))
        normalized_field = field.get("normalized_field") or field.get("field") or ""
        mapped_by_rule = map_plain_label(raw_label, template_id) if template_id else ""
        if allowed_fields is not None and normalized_field not in allowed_fields and mapped_by_rule in allowed_fields:
            normalized_field = mapped_by_rule
        if allowed_fields is not None and normalized_field not in allowed_fields:
            continue
        meta = configured_field_meta(template_id, normalized_field)
        mapping_source = field.get("mapping_source", "ai")
        if mapped_by_rule and mapped_by_rule == normalized_field and mapping_source == "ai" and field.get("normalized_field") != mapped_by_rule:
            mapping_source = "template_alias_rule"
        normalized_fields.append(
            {
                "normalized_field": normalized_field,
                "raw_label": raw_label,
                "raw_value": field.get("raw_value", field.get("value", "")),
                "confidence": normalize_confidence(field.get("confidence", 0.0)),
                "evidence": evidence,
                "mapping_source": mapping_source,
                "display_name": meta.get("display_name", ""),
                "source_system_field": meta.get("source_system_field", ""),
            }
        )

    existing_fields = {field["normalized_field"] for field in normalized_fields}
    for item in document_items:
        mapped_field = item.get("mapped_field", "")
        if not mapped_field or mapped_field in existing_fields:
            continue
        if allowed_fields is not None and mapped_field not in allowed_fields:
            continue
        normalized_fields.append(
            {
                "normalized_field": mapped_field,
                "raw_label": item.get("raw_key", ""),
                "raw_value": item.get("raw_value", ""),
                "confidence": item.get("mapping_confidence", 0.78),
                "evidence": item.get("evidence", {}),
                "mapping_source": item.get("mapping_source", "template_alias_rule"),
                "display_name": item.get("mapped_display_name", ""),
                "source_system_field": item.get("source_system_field", ""),
            }
        )
        existing_fields.add(mapped_field)

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
        "document_items": document_items,
        "extracted_fields": normalized_fields,
        "special_risks": special_risks,
        "raw_model_output": raw_payload,
    }


def normalize_document_items(parsed: dict[str, Any], fields: list[Any], template_id: str | None = None, allowed_fields: set[str] | None = None) -> list[dict[str, Any]]:
    raw_items = parsed.get("document_items") or parsed.get("raw_items") or []
    items = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        evidence = item.get("evidence") or {}
        if isinstance(evidence, str):
            evidence = {"page": 1, "text": evidence, "region_hint": ""}
        raw_key = item.get("raw_key", item.get("key", item.get("label", "")))
        mapped_field = item.get("mapped_field", item.get("normalized_field", ""))
        mapped_by_rule = map_plain_label(raw_key, template_id) if template_id else ""
        if allowed_fields is not None and mapped_field not in allowed_fields and mapped_by_rule in allowed_fields:
            mapped_field = mapped_by_rule
        meta = configured_field_meta(template_id, mapped_field)
        items.append(
            {
                "raw_key": raw_key,
                "raw_value": item.get("raw_value", item.get("value", "")),
                "evidence": {
                    "page": evidence.get("page", 1),
                    "text": evidence.get("text", ""),
                    "region_hint": evidence.get("region_hint", evidence.get("region", "")),
                },
                "mapped_field": mapped_field if allowed_fields is None or mapped_field in allowed_fields else "",
                "mapped_display_name": meta.get("display_name", ""),
                "source_system_field": meta.get("source_system_field", ""),
                "mapping_source": "template_alias_rule" if mapped_by_rule and mapped_by_rule == mapped_field else item.get("mapping_source", "ai"),
                "mapping_confidence": 0.8 if mapped_by_rule and mapped_by_rule == mapped_field else normalize_confidence(item.get("confidence", 0.0)),
            }
        )
    if items:
        return items
    for field in fields:
        if not isinstance(field, dict):
            continue
        label = field.get("raw_label", field.get("raw_key", ""))
        value = field.get("raw_value", field.get("value", ""))
        evidence = field.get("evidence") or {}
        if isinstance(evidence, str):
            evidence = {"page": 1, "text": evidence, "region_hint": ""}
        if label or value:
            mapped_field = map_plain_label(label, template_id) if template_id else ""
            meta = configured_field_meta(template_id, mapped_field)
            items.append(
                {
                    "raw_key": label,
                    "raw_value": value,
                    "evidence": {
                        "page": evidence.get("page", 1),
                        "text": evidence.get("text", ""),
                        "region_hint": evidence.get("region_hint", evidence.get("region", "")),
                    },
                    "mapped_field": mapped_field if allowed_fields is None or mapped_field in allowed_fields else "",
                    "mapped_display_name": meta.get("display_name", ""),
                    "source_system_field": meta.get("source_system_field", ""),
                    "mapping_source": "template_alias_rule" if mapped_field else "",
                    "mapping_confidence": 0.8 if mapped_field else 0.0,
                }
            )
    return items


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


async def extract_with_model(image_base64: str, mime_type: str = "image/png", template_id: str | None = None) -> ExtractionResult:
    template = configured_template(template_id)
    allowed_fields = configured_field_ids(template)
    client = ModelClient(load_local_config().get("model_settings", {}))
    payload = await client.chat_image(build_extraction_prompt(template_id), image_base64, mime_type)
    parsed = parse_model_json(payload, template_id)
    extraction = ExtractionResult.model_validate(normalize_extraction_payload(parsed, payload, allowed_fields, template_id))
    if not extraction.extracted_fields:
        raise ValueError("Model returned zero extracted fields. 图片已成功送达模型，但模型没有按结构化要求返回字段，请重试或检查模型输出。")
    return extraction


def extraction_from_static(expected_result: dict[str, Any]) -> ExtractionResult:
    return ExtractionResult.model_validate(expected_result)
