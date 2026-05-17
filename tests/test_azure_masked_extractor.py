import json

from paygent.azure_openai_extractor import (
    AzureMaskedSpanExtractor,
    AzureOpenAIConfig,
    extract_spans_from_original,
    load_azure_openai_config,
    mask_digits,
)
from paygent.stages import Stage


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self):
        return self.payload


class RecordingHttpClient:
    def __init__(self, response_payload):
        self.response_payload = response_payload
        self.calls = []

    def post(self, url, *, headers, json, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeResponse(self.response_payload)


def chat_payload(content):
    return {"choices": [{"message": {"content": content}}]}


def test_mask_digits_preserves_length_and_replaces_digits():
    text = "acc1001 pincode 400001 cvv 123"

    masked = mask_digits(text)

    assert masked == "acc9999 pincode 999999 cvv 999"
    assert len(masked) == len(text)


def test_span_values_are_extracted_from_original_text():
    text = "mera naam Nithin Jain hai"
    start = text.index("Nithin")
    end = start + len("Nithin Jain")

    result = extract_spans_from_original(
        text,
        {"confidence": "high", "fields": [{"name": "full_name", "start": start, "end": end}]},
        ["full_name"],
    )

    assert result == {"confidence": "high", "full_name": "Nithin Jain"}


def test_invalid_span_payload_is_ignored():
    result = extract_spans_from_original(
        "short",
        {"confidence": "high", "fields": [{"name": "full_name", "start": -1, "end": 30}]},
        ["full_name"],
    )

    assert result == {"confidence": "high"}


def test_azure_extractor_masks_digits_before_call_and_maps_spans_locally():
    text = "400001 is the pincode"
    start = text.index("400001")
    end = start + len("400001")
    http_client = RecordingHttpClient(
        chat_payload(json.dumps({"confidence": "high", "fields": [{"name": "pincode", "start": start, "end": end}]}))
    )
    extractor = AzureMaskedSpanExtractor(
        AzureOpenAIConfig(
            endpoint="https://example.openai.azure.com/",
            api_key="test-key",
            api_version="2025-01-01-preview",
            deployment="model-router",
        ),
        http_client=http_client,
    )

    result = extractor.extract(text=text, stage=Stage.AWAIT_SECONDARY_FACTOR, expected_fields=["pincode"])

    request = http_client.calls[0]
    rendered_payload = json.dumps(request["json"])
    assert "400001" not in rendered_payload
    assert "999999 is the pincode" in rendered_payload
    assert request["url"] == (
        "https://example.openai.azure.com/openai/deployments/model-router/"
        "chat/completions?api-version=2025-01-01-preview"
    )
    assert request["headers"]["api-key"] == "test-key"
    assert result["pincode"] == "400001"
    assert result["confidence"] == "high"


def test_load_azure_openai_config_from_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "AZURE_OPENAI_ENDPOINT=https://example.openai.azure.com/",
                "AZURE_OPENAI_API_KEY=from-env-file",
                "AZURE_OPENAI_API_VERSION=2025-01-01-preview",
                "AZURE_OPENAI_DEPLOYMENT=model-router",
            ]
        )
    )
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_DEPLOYMENT", raising=False)

    config = load_azure_openai_config(env_file)

    assert config.endpoint == "https://example.openai.azure.com/"
    assert config.api_key == "from-env-file"
    assert config.api_version == "2025-01-01-preview"
    assert config.deployment == "model-router"


def test_gitignore_has_env_rules():
    content = open(".gitignore", encoding="utf-8").read()

    assert ".env" in content
    assert ".env.*" in content
    assert "!.env.example" in content
