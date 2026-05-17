from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx


DEFAULT_AZURE_OPENAI_API_VERSION = "2025-01-01-preview"
DEFAULT_AZURE_OPENAI_DEPLOYMENT = "model-router"


@dataclass(frozen=True)
class AzureOpenAIConfig:
    endpoint: str = ""
    api_key: str = ""
    api_version: str = DEFAULT_AZURE_OPENAI_API_VERSION
    deployment: str = DEFAULT_AZURE_OPENAI_DEPLOYMENT
    timeout_seconds: float = 8.0

    def is_complete(self) -> bool:
        return bool(
            self.endpoint.strip()
            and self.api_key.strip()
            and self.api_version.strip()
            and self.deployment.strip()
        )


def load_azure_openai_config(env_path: str | Path = ".env") -> AzureOpenAIConfig:
    _load_dotenv_file(env_path)
    return AzureOpenAIConfig(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
        api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION", DEFAULT_AZURE_OPENAI_API_VERSION),
        deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT", DEFAULT_AZURE_OPENAI_DEPLOYMENT),
    )


def mask_digits(text: str) -> str:
    return "".join("9" if char.isdigit() else char for char in text)


def extract_spans_from_original(
    original_text: str,
    span_payload: dict[str, Any],
    expected_fields: list[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {"confidence": str(span_payload.get("confidence", "low")).lower()}
    allowed = set(expected_fields)
    fields = span_payload.get("fields", [])
    if not isinstance(fields, list):
        return result

    for field in fields:
        if not isinstance(field, dict):
            continue
        name = field.get("name")
        if name not in allowed:
            continue
        start = field.get("start")
        end = field.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if start < 0 or end <= start or end > len(original_text):
            continue
        value = original_text[start:end].strip()
        if value:
            result[str(name)] = value
    return result


class AzureMaskedSpanExtractor:
    def __init__(self, config: AzureOpenAIConfig, http_client=None):
        self.config = config
        self.http_client = http_client or httpx

    def extract(self, *, text: str, stage, expected_fields: list[str]) -> dict[str, Any] | None:
        if not self.config.is_complete():
            return None

        masked_text = mask_digits(text)
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You extract payment-agent fields from masked user text. "
                        "All digits in masked_text have been replaced by 9, preserving exact character positions. "
                        "Return JSON only. Do not infer real numbers. Return spans into masked_text only."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "stage": str(stage.value if hasattr(stage, "value") else stage),
                            "expected_fields": expected_fields,
                            "masked_text": masked_text,
                            "schema": {
                                "confidence": "low|medium|high",
                                "fields": [
                                    {"name": "one of expected_fields", "start": 0, "end": 0}
                                ],
                            },
                        },
                        ensure_ascii=True,
                    ),
                },
            ],
            "temperature": 0,
            "max_tokens": 200,
            "response_format": {"type": "json_object"},
        }

        try:
            response = self.http_client.post(
                self._chat_completions_url(),
                headers={"api-key": self.config.api_key, "Content-Type": "application/json"},
                json=payload,
                timeout=self.config.timeout_seconds,
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            span_payload = json.loads(content) if isinstance(content, str) else content
            if not isinstance(span_payload, dict):
                return None
            # If the LLM returned span indices, map them back to original text
            if "fields" in span_payload and isinstance(span_payload["fields"], list):
                return extract_spans_from_original(text, span_payload, expected_fields)
            # Otherwise the LLM returned direct values — pass them through
            # Ensure confidence is present (default to "high" for direct values)
            if "confidence" not in span_payload:
                span_payload["confidence"] = "high"
            return span_payload
        except Exception:
            return None

    def _chat_completions_url(self) -> str:
        endpoint = self.config.endpoint.rstrip("/")
        deployment = quote(self.config.deployment.strip(), safe="")
        api_version = quote(self.config.api_version.strip(), safe="")
        return f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"


def _load_dotenv_file(env_path: str | Path) -> None:
    path = Path(env_path)
    try:
        from dotenv import load_dotenv
    except ImportError:
        _load_dotenv_file_without_dependency(path)
        return

    load_dotenv(path, override=False)


def _load_dotenv_file_without_dependency(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
