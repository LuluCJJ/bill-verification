import json
import re
from typing import Any

from .model_client import ModelClient
from .schemas import ExtractionResult


EXTRACTION_PROMPT = """
你是权签票据一致性预审助手。请从票据图片中提取可见字段，并映射到给定标准字段。

要求：
1. 只提取票面可见信息，不要补全或臆测。
2. 如果不确定，保留低置信度候选。
3. 输出严格 JSON，不要 Markdown。
4. 字段使用 normalized_field 表示标准字段。
5. 每个字段保留 raw_label、raw_value、confidence、evidence。
6. 特殊票面风险如 Not Negotiable、A/C Payee Only、不可转让，放入 special_risks。

标准字段包括：
付款方名称 payer_name，付款方账号 payer_account，付款方银行 payer_bank，收款方名称 beneficiary_name，
收款方账号 beneficiary_account，收款方银行 beneficiary_bank，SWIFT/BIC swift_code，IBAN iban，
币种 currency，金额 amount，大写金额 amount_in_words，付款日期 payment_date，付款用途 purpose，费用承担 charge_bearer。
"""


def parse_model_json(payload: dict[str, Any]) -> dict[str, Any]:
    content = payload["choices"][0]["message"]["content"]
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    match = re.search(r"\{.*\}", str(content), re.S)
    if not match:
        raise ValueError("Model response does not contain a JSON object.")
    return json.loads(match.group(0))


async def extract_with_model(image_base64: str, mime_type: str = "image/png") -> ExtractionResult:
    client = ModelClient()
    payload = await client.chat_image(EXTRACTION_PROMPT, image_base64, mime_type)
    parsed = parse_model_json(payload)
    parsed["raw_model_output"] = payload
    return ExtractionResult.model_validate(parsed)


def extraction_from_static(expected_result: dict[str, Any]) -> ExtractionResult:
    return ExtractionResult.model_validate(expected_result)
