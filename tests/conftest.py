from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from agent import Agent
from paygent.state import ApiResult


class FakeApiClient:
    def __init__(self):
        self.accounts = {
            "ACC1001": {
                "account_id": "ACC1001",
                "full_name": "Nithin Jain",
                "dob": "1990-05-14",
                "aadhaar_last4": "4321",
                "pincode": "400001",
                "balance": "1250.75",
            },
            "ACC1002": {
                "account_id": "ACC1002",
                "full_name": "Rajarajeswari Balasubramaniam",
                "dob": "1985-11-23",
                "aadhaar_last4": "9876",
                "pincode": "400002",
                "balance": "540.00",
            },
            "ACC1003": {
                "account_id": "ACC1003",
                "full_name": "Priya Agarwal",
                "dob": "1992-08-10",
                "aadhaar_last4": "2468",
                "pincode": "400003",
                "balance": "0.00",
            },
            "ACC1004": {
                "account_id": "ACC1004",
                "full_name": "Rahul Mehta",
                "dob": "1988-02-29",
                "aadhaar_last4": "1357",
                "pincode": "400004",
                "balance": "3200.50",
            },
        }
        self.lookup_calls = []
        self.payment_calls = []
        self.lookup_error_codes = {}
        self.payment_error_queue = []
        self.transaction_id = "txn_test_success"

    def lookup_account(self, account_id: str) -> ApiResult:
        self.lookup_calls.append(account_id)
        if account_id in self.lookup_error_codes:
            return ApiResult(ok=False, error_code=self.lookup_error_codes[account_id])
        if account_id not in self.accounts:
            return ApiResult(ok=False, error_code="account_not_found")
        return ApiResult(ok=True, data=self.accounts[account_id])

    def process_payment(self, payload: dict) -> ApiResult:
        self.payment_calls.append(payload)
        if self.payment_error_queue:
            return ApiResult(ok=False, error_code=self.payment_error_queue.pop(0))
        return ApiResult(ok=True, data={"success": True, "transaction_id": self.transaction_id})


class NoopLLMExtractor:
    def __init__(self):
        self.calls = []

    def extract(self, text, stage):
        self.calls.append((text, stage))
        return None


@pytest.fixture
def fake_api_client():
    return FakeApiClient()


@pytest.fixture
def noop_llm_extractor():
    return NoopLLMExtractor()


@pytest.fixture
def agent_factory(fake_api_client, noop_llm_extractor):
    def make_agent(today: date | None = None):
        return Agent(
            api_client=fake_api_client,
            today_provider=(lambda: today or date(2026, 5, 15)),
            llm_extractor=noop_llm_extractor,
        )

    return make_agent


@pytest.fixture
def valid_card_text():
    return "cardholder name Nithin Jain, card number 4532 0151 1283 0366, expires 12/27, CVV one two three"


def drive(agent: Agent, turns: list[str]) -> list[str]:
    return [agent.next(turn)["message"] for turn in turns]


@pytest.fixture
def drive_turns():
    return drive


def assert_no_sensitive_values(messages: list[str]) -> None:
    forbidden = [
        "1990-05-14",
        "1988-02-29",
        "4321",
        "2468",
        "1357",
        "400001",
        "400003",
        "400004",
        "4532015112830366",
        "123",
    ]
    joined = "\n".join(messages)
    for value in forbidden:
        assert value not in joined


@pytest.fixture
def no_sensitive_values():
    return assert_no_sensitive_values


@pytest.fixture
def decimal_amount():
    return Decimal
