"""Stress test harness for the Payment Agent.

Uses the Agent.next() interface exactly as specified in the assignment.
Runs diverse conversation scenarios with messy, real-world-like inputs
to verify robustness.

Usage:
    python eval/stress_test.py
    python eval/stress_test.py --verbose
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
        return ApiResult(ok=True, data={"success": True, "transaction_id": "txn_stress_test_ok"})


VALID_CARD = "cardholder name Nithin Jain, card number 4532 0151 1283 0366, expires 12/27, CVV 123"

SCENARIOS = [
    # ── Happy paths ──────────────────────────────────────────
    {
        "name": "Happy path: clean inputs",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "DOB is 1990-05-14",
            "full amount",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
        "expect_none": ["1990-05-14", "4321", "400001"],
    },
    {
        "name": "Happy path: messy conversational inputs",
        "turns": [
            "hey there",
            "yeah my account number is ACC1001 I think",
            "i am nithin, Nithin Jain",
            "I was born on 14th May 1990",
            "I want to pay a thousand rupees",
            "cardholder name Nithin Jain, card 4532 0151 1283 0366, expires December 2027, CVV one two three",
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Happy path: word-form aadhaar",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "aadhar last four digits are four three two one",
            "500",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Happy path: bare digits for secondary factor",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "4321",
            "500",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Happy path: 'all of it' full amount",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "pincode 400001",
            "all of it",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Happy path: slash-separated DOB",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "my dob is 14/05/1990",
            "1000",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Happy path: leap year DOB (ACC1004)",
        "turns": [
            "Hi",
            "ACC1004",
            "Rahul Mehta",
            "my dob is 29th february 1988",
            "1000",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Happy path: card details one by one",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "DOB is 1990-05-14",
            "500",
            "name is Nithin Jain",
            "card number is 4532 0151 1283 0366",
            "123",
            "12/27",
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Happy path: multi-line card input",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "DOB is 1990-05-14",
            "500",
            "name is Nithin Jain\ncard number is 4532 0151 1283 0366\nCVV 123\nexpiry is 12/27",
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    # ── Name handling ────────────────────────────────────────
    {
        "name": "Name: trailing filler stripped",
        "turns": [
            "Hi",
            "ACC1001",
            "i am Nithin Jain i guess",
            "4321",
            "500",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Name: long name with alias",
        "turns": [
            "Hi",
            "ACC1002",
            "you can call me Raja but my full name is Rajarajeswari Balasubramaniam",
            "Aadhaar last 4 is 9876",
            "full amount",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    # ── Amount handling ──────────────────────────────────────
    {
        "name": "Amount: reject then provide in same message",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "4321",
            "half of it",
            "no, 700",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Amount: word form 'five hundred'",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "4321",
            "five hundred rupees",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Amount: exceeds balance, then valid",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "4321",
            "5000",
            "500",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
        "expect_step": {4: "greater than"},
    },
    # ── Verification failures ────────────────────────────────
    {
        "name": "Verification: wrong name then correct",
        "turns": [
            "Hi",
            "ACC1001",
            "John Smith",
            "Nithin Jain",
            "DOB is 1990-05-14",
            "500",
            VALID_CARD,
        ],
        "expect_any": ["txn_stress_test_ok"],
    },
    {
        "name": "Verification: wrong secondary factor",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "DOB is 1990-01-01",
        ],
        "expect_any": ["could not verify"],
    },
    {
        "name": "Verification: invalid DOB gives feedback",
        "turns": [
            "Hi",
            "ACC1004",
            "Rahul Mehta",
            "my dob is 30th february 1988",
        ],
        "expect_any": ["not appear to be valid", "date"],
    },
    {
        "name": "Verification: exhausted retries",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "DOB is 1990-01-01",
            "Nithin Jain",
            "DOB is 1990-01-02",
            "Nithin Jain",
            "DOB is 1990-01-03",
        ],
        "expect_any": ["contact support"],
    },
    # ── Zero balance ─────────────────────────────────────────
    {
        "name": "Zero balance: no payment needed",
        "turns": [
            "Hi",
            "ACC1003",
            "Priya Agarwal",
            "DOB is 1992-08-10",
        ],
        "expect_any": ["no outstanding balance"],
    },
    # ── Account not found ────────────────────────────────────
    {
        "name": "Account: not found",
        "turns": ["Hi", "ACC9999"],
        "expect_any": ["could not find"],
    },
    # ── Cancellation ─────────────────────────────────────────
    {
        "name": "Cancellation: bare cancel",
        "turns": ["Hi", "ACC1001", "cancel"],
        "expect_any": ["cancelled"],
    },
    {
        "name": "Cancellation: negation doesn't cancel",
        "turns": ["Hi", "ACC1001", "don't cancel the payment"],
        "expect_none": ["cancelled"],
    },
    # ── Account change ───────────────────────────────────────
    {
        "name": "Account change: during name stage",
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
        "expect_any": ["txn_stress_test_ok"],
    },
    # ── Terminal state ───────────────────────────────────────
    {
        "name": "Terminal: new account after success",
        "turns": [
            "Hi",
            "ACC1001",
            "Nithin Jain",
            "4321",
            "500",
            VALID_CARD,
            "new account",
            "ACC1004",
        ],
        "expect_any": ["full name"],
    },
]


def run_scenario(scenario: dict, verbose: bool = False) -> tuple[bool, str]:
    name = scenario["name"]
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

    # Check expect_any
    for expected in scenario.get("expect_any", []):
        if expected.lower() not in joined.lower():
            return False, f"Expected '{expected}' not found in any response"

    # Check expect_none
    for forbidden in scenario.get("expect_none", []):
        if forbidden.lower() in joined.lower():
            return False, f"Forbidden '{forbidden}' found in response"

    # Check expect_step
    for step_idx, expected in scenario.get("expect_step", {}).items():
        if step_idx < len(messages) and expected.lower() not in messages[step_idx].lower():
            return False, f"Step {step_idx}: expected '{expected}' not found"

    if verbose:
        print(f"\n{'='*60}")
        print(f"  {name}")
        print(f"{'='*60}")
        for i, (turn, msg) in enumerate(zip(scenario["turns"], messages)):
            print(f"  User: {turn}")
            print(f"  Agent: {msg}")
            print()

    return True, "OK"


def main():
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    passed = 0
    failed = 0
    errors = []

    for scenario in SCENARIOS:
        ok, reason = run_scenario(scenario, verbose=verbose)
        if ok:
            passed += 1
            print(f"  PASS  {scenario['name']}")
        else:
            failed += 1
            errors.append((scenario["name"], reason))
            print(f"  FAIL  {scenario['name']}: {reason}")

    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed out of {len(SCENARIOS)} scenarios")
    print(f"{'='*60}")

    if errors:
        print("\nFailed scenarios:")
        for name, reason in errors:
            print(f"  - {name}: {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
