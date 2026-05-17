from decimal import Decimal
from pathlib import Path

from agent import Agent
from paygent.llm_extraction import (
    default_llm_extractor,
    is_llm_required,
    redact_for_llm,
    understand_fields,
)
from paygent.stages import Stage


class FakeLLMExtractor:
    def __init__(self, payload_by_stage=None, default_payload=None, error: Exception | None = None):
        self.payload_by_stage = payload_by_stage or {}
        self.default_payload = default_payload
        self.error = error
        self.calls = []

    def extract(self, text: str, stage: Stage):
        self.calls.append((text, stage))
        if self.error:
            raise self.error
        return self.payload_by_stage.get(stage, self.default_payload)


def test_default_llm_is_disabled_without_env(monkeypatch):
    env_dir = Path.cwd() / ".pytest_cache" / "env-disabled"
    env_dir.mkdir(parents=True, exist_ok=True)
    env_file = env_dir / ".env"
    if env_file.exists():
        env_file.unlink()
    monkeypatch.chdir(env_dir)
    monkeypatch.delenv("PAYGENT_LLM_MODE", raising=False)
    monkeypatch.delenv("PAYGENT_LLM_FALLBACK", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    assert default_llm_extractor() is None
    assert not is_llm_required()


def test_default_llm_loads_required_key_from_env_file(monkeypatch):
    env_dir = Path.cwd() / ".pytest_cache" / "env-test"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text(
        "PAYGENT_LLM_MODE=required\nOPENAI_API_KEY=sk-test-env-file\nPAYGENT_LLM_MODEL=test-model\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(env_dir)
    monkeypatch.delenv("PAYGENT_LLM_MODE", raising=False)
    monkeypatch.delenv("PAYGENT_LLM_FALLBACK", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PAYGENT_LLM_MODEL", raising=False)

    provider = default_llm_extractor()

    assert provider is not None
    assert provider.api_key == "sk-test-env-file"
    assert provider.model == "test-model"
    assert is_llm_required()


def test_required_llm_mode_without_key_closes_cleanly(monkeypatch, fake_api_client):
    env_dir = Path.cwd() / ".pytest_cache" / "env-required-missing-key"
    env_dir.mkdir(parents=True, exist_ok=True)
    (env_dir / ".env").write_text("PAYGENT_LLM_MODE=required\n", encoding="utf-8")
    monkeypatch.chdir(env_dir)
    monkeypatch.delenv("PAYGENT_LLM_MODE", raising=False)
    monkeypatch.delenv("PAYGENT_LLM_FALLBACK", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    agent = Agent(api_client=fake_api_client)

    response = agent.next("Hi")["message"]

    assert "temporarily unavailable" in response
    assert agent._core.state.stage == Stage.API_UNAVAILABLE_CLOSE


def test_llm_first_extracts_hinglish_account_name_and_amount(fake_api_client):
    llm = FakeLLMExtractor(
        {
            Stage.AWAIT_ACCOUNT_ID: {"account_id": "ACC1001"},
            Stage.AWAIT_FULL_NAME: {"full_name": "Nithin Jain"},
            Stage.AWAIT_PAYMENT_AMOUNT: {"amount": "500"},
        }
    )
    agent = Agent(api_client=fake_api_client, llm_extractor=llm)

    agent.next("Hi")
    account_response = agent.next("meri account numbel heinnnn acc1001")["message"]
    name_response = agent.next("mera naam Nithin Jain hein")["message"]
    agent.next("Aadhaar last 4 is 4321")
    amount_response = agent.next("main 500 bharna chahta hu")["message"]

    assert "full name" in account_response
    assert "verification detail" in name_response
    assert "cardholder name" in amount_response
    assert agent._core.state.payment.amount == Decimal("500")


def test_llm_output_is_validated_before_state_change(fake_api_client):
    llm = FakeLLMExtractor({Stage.AWAIT_FULL_NAME: {"full_name": "Nithin123"}})
    agent = Agent(api_client=fake_api_client, llm_extractor=llm)

    agent.next("Hi")
    agent.next("ACC1001")
    response = agent.next("mera naam Nithin123 hai")["message"]

    assert "full legal name" in response
    assert agent._core.state.identity.full_name is None


def test_llm_runtime_failure_falls_back_to_deterministic_extraction():
    llm = FakeLLMExtractor(error=RuntimeError("network down"))

    result = understand_fields("I want to pay 500", Stage.AWAIT_PAYMENT_AMOUNT, llm)

    assert result.amount == Decimal("500")


def test_llm_invalid_json_falls_back_to_deterministic_extraction():
    llm = FakeLLMExtractor(default_payload="not json")

    result = understand_fields("I want to pay 500", Stage.AWAIT_PAYMENT_AMOUNT, llm)

    assert result.amount == Decimal("500")


def test_redact_for_llm_masks_sensitive_values():
    redacted = redact_for_llm(
        "DOB is 1990-05-14, Aadhaar last 4 is 4321, pincode is 400001, "
        "card number 4532015112830366, CVV 123, expires 12/27"
    ).text

    assert "1990-05-14" not in redacted
    assert "4321" not in redacted
    assert "400001" not in redacted
    assert "4532015112830366" not in redacted
    assert "123" not in redacted
    assert "[DOB]" in redacted
    assert "[AADHAAR_LAST4]" in redacted
    assert "[PINCODE]" in redacted
    assert "[CARD_NUMBER]" in redacted
    assert "[CVV]" in redacted
    assert "[EXPIRY]" in redacted


def test_llm_provider_receives_redacted_verification_text(fake_api_client):
    llm = FakeLLMExtractor({Stage.AWAIT_SECONDARY_FACTOR: {}})
    agent = Agent(api_client=fake_api_client, llm_extractor=llm)

    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    response = agent.next("DOB is 1990-05-14")["message"]

    assert "Identity verified" in response
    assert all("1990-05-14" not in text for text, _stage in llm.calls)


def test_llm_provider_receives_redacted_card_text(fake_api_client, valid_card_text):
    llm = FakeLLMExtractor({Stage.AWAIT_CARD_DETAILS: {}})
    agent = Agent(api_client=fake_api_client, llm_extractor=llm)

    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")
    agent.next("pay 500")
    response = agent.next(valid_card_text)["message"]

    assert "successful" in response
    rendered_calls = "\n".join(text for text, _stage in llm.calls)
    assert "4532 0151 1283 0366" not in rendered_calls
    assert "4532015112830366" not in rendered_calls
    assert "one two three" not in rendered_calls
    assert "[CARD_NUMBER]" in rendered_calls
    assert "[CVV]" in rendered_calls
