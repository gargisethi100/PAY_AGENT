"""Evaluation scenario runner for the Payment Agent.

Runs predefined conversation scenarios through Agent.next() and checks
for expected outcomes. Used for automated evaluation and regression testing.

Usage:
    python eval/run_scenarios.py
    python eval/run_scenarios.py --verbose
"""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent import Agent
from paygent.state import ApiResult


class FakeApiClient:
    """Mock API client for evaluation. Contains all 4 test accounts."""

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
        self.payment_error_queue: list[str] = []

    def lookup_account(self, account_id: str) -> ApiResult:
        if account_id not in self.accounts:
            return ApiResult(ok=False, error_code="account_not_found")
        return ApiResult(ok=True, data=self.accounts[account_id])

    def process_payment(self, payload: dict) -> ApiResult:
        if self.payment_error_queue:
            return ApiResult(ok=False, error_code=self.payment_error_queue.pop(0))
        return ApiResult(ok=True, data={"success": True, "transaction_id": "txn_eval_success"})


VALID_CARD = "cardholder name Nithin Jain, card 4532 0151 1283 0366, expires 12/27, CVV 123"

SCENARIOS = [
    # ── Happy paths ──────────────────────────────────────────
    {
        "name": "happy_path_clean",
        "description": "Clean inputs, full payment",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "DOB is 1990-05-14",
            "full amount",
            VALID_CARD,
        ],
        "checks": {
            "must_contain": ["txn_eval_success", "1,250.75"],
            "must_not_contain": ["1990-05-14", "4321", "400001"],
        },
    },
    {
        "name": "happy_path_messy",
        "description": "Messy natural language inputs",
        "turns": [
            "hey there",
            "yeah my account number is ACC1001 I think",
            "i am nithin, Nithin Jain",
            "I was born on 14th May 1990",
            "I want to pay a thousand rupees",
            "cardholder name Nithin Jain, card 4532 0151 1283 0366, expires December 2027, CVV one two three",
        ],
        "checks": {
            "must_contain": ["txn_eval_success"],
        },
    },
    {
        "name": "happy_path_word_aadhaar",
        "description": "Word-form Aadhaar digits",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "aadhar last four digits are four three two one",
            "500",
            VALID_CARD,
        ],
        "checks": {
            "must_contain": ["txn_eval_success"],
        },
    },
    {
        "name": "happy_path_slash_dob",
        "description": "DOB with slash separator",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "my dob is 14/05/1990",
            "1000",
            VALID_CARD,
        ],
        "checks": {
            "must_contain": ["txn_eval_success"],
        },
    },
    {
        "name": "happy_path_leap_year",
        "description": "ACC1004 leap year DOB",
        "turns": [
            "Hi",
            "ACC1004",
            "Rahul Mehta",
            "my dob is 29th february 1988",
            "1000",
            VALID_CARD,
        ],
        "checks": {
            "must_contain": ["txn_eval_success"],
        },
    },
    {
        "name": "happy_path_long_name",
        "description": "ACC1002 long name with alias",
        "turns": [
            "Hi",
            "ACC1002",
            "you can call me Raja but my full name is Rajarajeswari Balasubramaniam",
            "Aadhaar last 4 is 9876",
            "full amount",
            VALID_CARD,
        ],
        "checks": {
            "must_contain": ["txn_eval_success", "540.00"],
        },
    },
    {
        "name": "happy_path_incremental_card",
        "description": "Card details provided one by one",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "4321",
            "five hundred",
            "name is Nithin Jain",
            "card number is 4532 0151 1283 0366",
            "123",
            "12/27",
        ],
        "checks": {
            "must_contain": ["txn_eval_success", "****0366"],
        },
    },
    # ── Amount handling ──────────────────────────────────────
    {
        "name": "amount_all_of_it",
        "description": "Colloquial 'all of it' for full amount",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "pincode 400001",
            "all of it",
            VALID_CARD,
        ],
        "checks": {
            "must_contain": ["txn_eval_success", "1,250.75"],
        },
    },
    {
        "name": "amount_reject_then_new",
        "description": "Reject relative amount, provide new in same message",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "4321",
            "half of it",
            "no, 700",
            VALID_CARD,
        ],
        "checks": {
            "must_contain": ["txn_eval_success", "700.00"],
        },
    },
    # ── Verification failures ────────────────────────────────
    {
        "name": "verification_failure",
        "description": "Exhausted verification retries",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "DOB is 1990-01-01",
            "Nithin Jain",
            "DOB is 1985-03-15",
            "Nithin Jain",
            "pincode 999999",
        ],
        "checks": {
            "must_contain": ["contact support"],
            "must_not_contain": ["1,250.75"],
        },
    },
    {
        "name": "invalid_dob_feedback",
        "description": "Invalid date gives clear feedback",
        "turns": [
            "Hi",
            "ACC1004",
            "Rahul Mehta",
            "my dob is 30th february 1988",
        ],
        "checks": {
            "must_contain": ["not appear to be valid"],
        },
    },
    # ── Zero balance ─────────────────────────────────────────
    {
        "name": "zero_balance",
        "description": "No payment needed for zero balance",
        "turns": ["Hi", "ACC1003", "Priya Agarwal", "DOB is 1992-08-10"],
        "checks": {
            "must_contain": ["no outstanding balance"],
        },
    },
    # ── Account not found ────────────────────────────────────
    {
        "name": "account_not_found",
        "description": "Invalid account ID",
        "turns": ["Hi", "ACC9999"],
        "checks": {
            "must_contain": ["could not find"],
        },
    },
    # ── Cancellation ─────────────────────────────────────────
    {
        "name": "cancellation",
        "description": "User cancels mid-flow",
        "turns": ["Hi", "ACC1001", "cancel"],
        "checks": {
            "must_contain": ["cancelled"],
        },
    },
    {
        "name": "cancellation_negation",
        "description": "Negation prevents accidental cancellation",
        "turns": ["Hi", "ACC1001", "don't cancel the payment"],
        "checks": {
            "must_not_contain": ["cancelled"],
        },
    },
    # ── Account change ───────────────────────────────────────
    {
        "name": "account_change",
        "description": "Switch account during name stage",
        "turns": [
            "Hi",
            "ACC1001",
            "would like to change my acc id",
            "ACC1004",
            "Rahul Mehta",
            "pincode 400004",
            "500",
            VALID_CARD,
        ],
        "checks": {
            "must_contain": ["txn_eval_success"],
        },
    },
]


def run_scenario(scenario: dict, verbose: bool = False) -> tuple[bool, str]:
    api = FakeApiClient()
    if "payment_errors" in scenario:
        api.payment_error_queue = list(scenario["payment_errors"])

    agent = Agent(
        api_client=api,
        today_provider=lambda: date(2026, 5, 15),
    )

    messages = []
    for turn in scenario["turns"]:
        result = agent.next(turn)
        messages.append(result["message"])

    joined = "\n".join(messages)
    checks = scenario.get("checks", {})

    for expected in checks.get("must_contain", []):
        if expected.lower() not in joined.lower():
            return False, f"Expected '{expected}' not found"

    for forbidden in checks.get("must_not_contain", []):
        if forbidden.lower() in joined.lower():
            return False, f"Forbidden '{forbidden}' found"

    if verbose:
        print(f"\n  {'='*56}")
        print(f"  {scenario['name']}: {scenario.get('description', '')}")
        print(f"  {'='*56}")
        for turn, msg in zip(scenario["turns"], messages):
            print(f"    User:  {turn}")
            print(f"    Agent: {msg}")
            print()

    return True, "OK"


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    passed = 0
    failed = 0
    errors = []

    print(f"\n  Running {len(SCENARIOS)} evaluation scenarios...\n")

    for scenario in SCENARIOS:
        ok, reason = run_scenario(scenario, verbose=verbose)
        if ok:
            passed += 1
            print(f"  PASS  {scenario['name']}")
        else:
            failed += 1
            errors.append((scenario["name"], reason))
            print(f"  FAIL  {scenario['name']}: {reason}")

    print(f"\n  {'='*56}")
    print(f"  Results: {passed} passed, {failed} failed out of {len(SCENARIOS)}")
    print(f"  {'='*56}")

    if errors:
        print("\n  Failed:")
        for name, reason in errors:
            print(f"    - {name}: {reason}")
        sys.exit(1)
    else:
        print("\n  All scenarios passed.")


if __name__ == "__main__":
    main()
