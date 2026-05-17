from __future__ import annotations

<<<<<<< HEAD
import json
import os
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol

import httpx

from paygent.config import load_env_file
from paygent.extraction import ExtractedFields, extract_fields
from paygent.stages import Stage
from paygent.validators import validate_account_id, validate_full_name_format


OPENAI_CHAT_COMPLETIONS_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_LLM_MODEL = "gpt-4o-mini"


class LLMExtractionProvider(Protocol):
    def extract(self, text: str, stage: Stage) -> dict | str | None:
        ...


@dataclass(frozen=True)
class RedactedForLLM:
    text: str
    redacted: bool


class OpenAILLMExtractionProvider:
    def __init__(self, api_key: str, model: str = DEFAULT_LLM_MODEL, timeout_seconds: float = 8.0):
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def extract(self, text: str, stage: Stage) -> dict | str | None:
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract only structured payment-agent fields from the user message. "
                        "Return a JSON object with only these optional keys: account_id, full_name, "
                        "amount, full_amount_requested, cardholder_name. Use null when unsure. "
                        "The user message may contain placeholders like [DOB], [AADHAAR_LAST4], "
                        "[PINCODE], [CARD_NUMBER], [CVV], or [EXPIRY]; never infer the hidden values. "
                        "Do not include explanations."
                    ),
                },
                {
                    "role": "user",
                    "content": f"stage={stage.value}\nmessage={text}",
                },
            ],
        }
        response = httpx.post(
            OPENAI_CHAT_COMPLETIONS_URL,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)


def default_llm_extractor() -> LLMExtractionProvider | None:
    load_env_file()
    mode = llm_mode()
    if mode == "off":
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAILLMExtractionProvider(
        api_key=api_key,
        model=os.getenv("PAYGENT_LLM_MODEL", DEFAULT_LLM_MODEL),
    )


def llm_mode() -> str:
    load_env_file()
    mode = os.getenv("PAYGENT_LLM_MODE")
    if mode:
        normalized = mode.strip().lower()
        return normalized if normalized in {"required", "optional", "off"} else "off"
    if os.getenv("PAYGENT_LLM_FALLBACK") == "1":
        return "optional"
    return "off"


def is_llm_required() -> bool:
    return llm_mode() == "required"


def understand_fields(
    text: str,
    stage: Stage | None,
    provider: LLMExtractionProvider | None,
) -> ExtractedFields:
    extracted = extract_fields(text, stage)
    if not provider or not stage:
        return extracted

    redacted = redact_for_llm(text)

    try:
        raw = provider.extract(redacted.text, stage)
    except Exception:
        return extracted

    payload = _coerce_json_object(raw)
    if payload is None:
        return extracted
    return _merge_valid_llm_fields(extracted, payload, stage)


def apply_llm_fallback(
    text: str,
    stage: Stage | None,
    extracted: ExtractedFields,
    provider: LLMExtractionProvider | None,
) -> ExtractedFields:
    if provider is None:
        return extracted
    understood = understand_fields(text, stage, provider)
    return _merge_local_sensitive_fields(understood, extracted)


def redact_for_llm(text: str) -> RedactedForLLM:
    redacted = text
    redacted = re.sub(
        r"\b(?:dob|date of birth|born(?:\s+on)?)\b\s*(?:is|:)?\s*[^,.;\n]+",
        lambda match: _keep_label_with_placeholder(match.group(0), "[DOB]"),
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b",
        "[DOB]",
        redacted,
    )
    redacted = re.sub(
        r"(\b(?:aadhaar|aadhar)\b[^,.;\n]*?)(\d(?:[\s-]*\d){3,})",
        r"\1[AADHAAR_LAST4]",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"(\b(?:pin\s*code|pincode|pin)\b[^,.;\n]*?)(\d(?:[\s-]*\d){5})",
        r"\1[PINCODE]",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(r"\b(?:\d[\s-]*){13,19}\b", "[CARD_NUMBER]", redacted)
    redacted = re.sub(
        r"(\bcvv\b[^,.;\n]*?)(\d{3,4}|(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)(?:\s+(?:zero|oh|one|two|three|four|five|six|seven|eight|nine)){2,3})",
        r"\1[CVV]",
        redacted,
        flags=re.I,
    )
    redacted = re.sub(
        r"(\b(?:expir(?:y|es)?)\b[^,.;\n]*?)(\d{1,2}\s*/\s*\d{2,4}|(?:jan|january|feb|february|mar|march|apr|april|may|jun|june|jul|july|aug|august|sep|sept|september|oct|october|nov|november|dec|december)\s+\d{2,4})",
        r"\1[EXPIRY]",
        redacted,
        flags=re.I,
    )
    return RedactedForLLM(text=redacted, redacted=redacted != text)


def _coerce_json_object(raw: dict | str | None) -> dict | None:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def _merge_valid_llm_fields(extracted: ExtractedFields, payload: dict, stage: Stage) -> ExtractedFields:
    if stage == Stage.AWAIT_ACCOUNT_ID:
        account_id = _optional_str(payload.get("account_id"))
        if account_id:
            normalized = account_id.replace(" ", "").replace("-", "").upper()
            if validate_account_id(normalized):
                extracted.account_id = normalized

    if stage == Stage.AWAIT_FULL_NAME:
        full_name = _optional_str(payload.get("full_name"))
        if validate_full_name_format(full_name):
            extracted.full_name = full_name.strip()
            extracted.invalid_fields.discard("full_name")

    if stage == Stage.AWAIT_PAYMENT_AMOUNT:
        amount = _to_decimal(payload.get("amount"))
        if amount is not None:
            extracted.amount = amount
        if payload.get("full_amount_requested") is True:
            extracted.full_amount_requested = True

    if stage == Stage.AWAIT_CARD_DETAILS:
        cardholder_name = _optional_str(payload.get("cardholder_name"))
        if validate_full_name_format(cardholder_name):
            extracted.cardholder_name = cardholder_name.strip()
            extracted.invalid_fields.discard("cardholder_name")

    return extracted


def _merge_local_sensitive_fields(target: ExtractedFields, local: ExtractedFields) -> ExtractedFields:
    target.dob = local.dob
    target.aadhaar_last4 = local.aadhaar_last4
    target.pincode = local.pincode
    target.card_number = local.card_number
    target.cvv = local.cvv
    target.expiry_month = local.expiry_month
    target.expiry_year = local.expiry_year
    target.invalid_fields.update(
        field
        for field in local.invalid_fields
        if field in {"dob", "aadhaar_last4", "pincode", "card_number", "cvv", "expiry"}
    )
    return target


def _keep_label_with_placeholder(value: str, placeholder: str) -> str:
    label = re.match(r"\s*(?:dob|date of birth|born(?:\s+on)?)\b", value, re.I)
    return f"{label.group(0)} {placeholder}" if label else placeholder


def _optional_str(value) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
=======
from dataclasses import asdict
from decimal import Decimal, InvalidOperation
import json
import re
from typing import Any

from paygent.extraction import ExtractedFields, extract_fields
from paygent.stages import Stage
from paygent.validators import normalize_expiry_year, validate_account_id, validate_dob


ACCEPTED_CONFIDENCE = {"medium", "high"}


def extract_fields_with_llm_fallback(
    text: str,
    stage: Stage | str | None,
    llm_extractor=None,
) -> ExtractedFields:
    rule_fields = extract_fields(text, stage)
    if llm_extractor is None:
        return rule_fields

    normalized_stage = Stage(stage) if stage and not isinstance(stage, Stage) else stage
    expected_fields = expected_fields_for_stage(normalized_stage, rule_fields)
    if not expected_fields:
        return rule_fields

    raw_result = _call_llm_extractor(llm_extractor, text, normalized_stage, expected_fields)
    llm_fields = parse_llm_extraction(raw_result, expected_fields)
    if llm_fields is None:
        return rule_fields
    return merge_missing_fields(rule_fields, llm_fields, expected_fields)


def expected_fields_for_stage(stage: Stage | None, fields: ExtractedFields) -> list[str]:
    if stage in {Stage.START, Stage.AWAIT_ACCOUNT_ID}:
        return [] if fields.account_id else ["account_id"]
    if stage == Stage.AWAIT_FULL_NAME:
        return [] if fields.full_name else ["full_name"]
    if stage == Stage.AWAIT_SECONDARY_FACTOR:
        if fields.dob or fields.aadhaar_last4 or fields.pincode:
            return []
        return ["dob", "aadhaar_last4", "pincode"]
    if stage == Stage.AWAIT_PAYMENT_AMOUNT:
        if fields.amount is not None or fields.full_amount_requested:
            return []
        return ["amount", "full_amount_requested"]
    if stage == Stage.AWAIT_CARD_DETAILS:
        expected = []
        if not fields.cardholder_name:
            expected.append("cardholder_name")
        if not fields.card_number:
            expected.append("card_number")
        if not fields.cvv:
            expected.append("cvv")
        if not fields.expiry_month or not fields.expiry_year:
            expected.extend(["expiry_month", "expiry_year"])
        return expected
    return []


def parse_llm_extraction(raw_result: Any, allowed_fields: list[str]) -> ExtractedFields | None:
    payload = _coerce_payload(raw_result)
    if payload is None:
        return None

    confidence = str(payload.get("confidence", "")).lower()
    if confidence not in ACCEPTED_CONFIDENCE:
        return None

    sanitized = ExtractedFields()
    allowed = set(allowed_fields)
    if "account_id" in allowed:
        sanitized.account_id = _sanitize_account_id(payload.get("account_id"))
    if "full_name" in allowed:
        sanitized.full_name = _sanitize_full_name(payload.get("full_name"))
    if "dob" in allowed:
        sanitized.dob = _sanitize_dob(payload.get("dob"))
    if "aadhaar_last4" in allowed:
        sanitized.aadhaar_last4 = _sanitize_fixed_digits(payload.get("aadhaar_last4"), 4)
    if "pincode" in allowed:
        sanitized.pincode = _sanitize_fixed_digits(payload.get("pincode"), 6)
    if "amount" in allowed:
        sanitized.amount = _sanitize_amount(payload.get("amount"))
    if "full_amount_requested" in allowed:
        sanitized.full_amount_requested = payload.get("full_amount_requested") is True
    if "cardholder_name" in allowed:
        sanitized.cardholder_name = _sanitize_nonempty_string(payload.get("cardholder_name"))
    if "card_number" in allowed:
        sanitized.card_number = _sanitize_card_number(payload.get("card_number"))
    if "cvv" in allowed:
        sanitized.cvv = _sanitize_cvv(payload.get("cvv"))
    if "expiry_month" in allowed:
        sanitized.expiry_month = _sanitize_expiry_month(payload.get("expiry_month"))
    if "expiry_year" in allowed:
        sanitized.expiry_year = _sanitize_expiry_year(payload.get("expiry_year"))
    return sanitized


def merge_missing_fields(
    rule_fields: ExtractedFields,
    llm_fields: ExtractedFields,
    allowed_fields: list[str],
) -> ExtractedFields:
    merged = ExtractedFields(**asdict(rule_fields))
    for field in allowed_fields:
        rule_value = getattr(merged, field)
        llm_value = getattr(llm_fields, field)
        if field == "full_amount_requested":
            if not rule_value and llm_value:
                setattr(merged, field, llm_value)
            continue
        if rule_value in {None, ""} and llm_value not in {None, ""}:
            setattr(merged, field, llm_value)
    return merged


def _call_llm_extractor(llm_extractor, text: str, stage: Stage | None, expected_fields: list[str]):
    try:
        if hasattr(llm_extractor, "extract"):
            return llm_extractor.extract(text=text, stage=stage, expected_fields=expected_fields)
        return llm_extractor(text=text, stage=stage, expected_fields=expected_fields)
    except Exception:
        return None


def _coerce_payload(raw_result: Any) -> dict[str, Any] | None:
    if raw_result is None:
        return None
    if isinstance(raw_result, ExtractedFields):
        return asdict(raw_result) | {"confidence": "high"}
    if isinstance(raw_result, str):
        try:
            raw_result = json.loads(raw_result)
        except json.JSONDecodeError:
            return None
    if not isinstance(raw_result, dict):
        return None
    return raw_result


def _sanitize_account_id(value: Any) -> str | None:
    if value is None:
        return None
    candidate = re.sub(r"[\s-]", "", str(value)).upper()
    return candidate if validate_account_id(candidate) else None


def _sanitize_full_name(value: Any) -> str | None:
    candidate = _sanitize_nonempty_string(value)
    if not candidate or any(ch.isdigit() for ch in candidate):
        return None
    if re.search(r"\b(?:dob|aadhaar|aadhar|pincode|card|cvv|account|amount|pay)\b", candidate, re.I):
        return None
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", candidate)
    if len(tokens) < 2:
        return None
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,80}", candidate):
        return None
    return candidate


def _sanitize_dob(value: Any) -> str | None:
    candidate = _sanitize_nonempty_string(value)
    return candidate if validate_dob(candidate) else None


def _sanitize_amount(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
<<<<<<< HEAD
=======


def _sanitize_fixed_digits(value: Any, length: int) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"\D", "", str(value))
    return digits if len(digits) == length else None


def _sanitize_nonempty_string(value: Any) -> str | None:
    if value is None:
        return None
    candidate = str(value).strip()
    return candidate or None


def _sanitize_card_number(value: Any) -> str | None:
    if value is None:
        return None
    digits = re.sub(r"[\s-]", "", str(value))
    if not digits.isdigit() or not 13 <= len(digits) <= 19:
        return None
    return digits


def _sanitize_cvv(value: Any) -> str | None:
    if value is None:
        return None
    digits = str(value).strip()
    if not digits.isdigit() or len(digits) not in {3, 4}:
        return None
    return digits


def _sanitize_expiry_month(value: Any) -> int | None:
    try:
        month = int(str(value))
    except (TypeError, ValueError):
        return None
    return month if 1 <= month <= 12 else None


def _sanitize_expiry_year(value: Any) -> int | None:
    try:
        year = int(str(value))
    except (TypeError, ValueError):
        return None
    return normalize_expiry_year(year)
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
