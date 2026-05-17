#!/usr/bin/env python3
"""Interactive CLI for the Payment Collection Agent.

Usage:
    python cli.py              # Live API (requires network)
    python cli.py --mock       # Offline with mock accounts
    python cli.py --debug      # Enable debug logging
    python cli.py --mock --debug
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _build_mock_client():
    from decimal import Decimal
    from paygent.state import ApiResult

    ACCOUNTS = {
        "ACC1001": {"account_id": "ACC1001", "full_name": "Nithin Jain", "dob": "1990-05-14", "aadhaar_last4": "4321", "pincode": "400001", "balance": "1250.75"},
        "ACC1002": {"account_id": "ACC1002", "full_name": "Rajarajeswari Balasubramaniam", "dob": "1985-11-23", "aadhaar_last4": "9876", "pincode": "400002", "balance": "540.00"},
        "ACC1003": {"account_id": "ACC1003", "full_name": "Priya Agarwal", "dob": "1992-08-10", "aadhaar_last4": "2468", "pincode": "400003", "balance": "0.00"},
        "ACC1004": {"account_id": "ACC1004", "full_name": "Rahul Mehta", "dob": "1988-02-29", "aadhaar_last4": "1357", "pincode": "400004", "balance": "3200.50"},
    }

    class MockApiClient:
        def lookup_account(self, account_id: str) -> ApiResult:
            if account_id not in ACCOUNTS:
                return ApiResult(ok=False, error_code="account_not_found")
            return ApiResult(ok=True, data=ACCOUNTS[account_id])

        def process_payment(self, payload: dict) -> ApiResult:
            import random, string, time
            txn_id = f"txn_mock_{int(time.time())}_{(''.join(random.choices(string.ascii_lowercase + string.digits, k=7)))}"
            return ApiResult(ok=True, data={"success": True, "transaction_id": txn_id})

    return MockApiClient()


def main():
    args = set(sys.argv[1:])
    if "--help" in args or "-h" in args:
        print(__doc__)
        return

    if "--debug" in args:
        os.environ["PAYGENT_DEBUG"] = "1"

    from agent import Agent

    mock = "--mock" in args
    api_client = _build_mock_client() if mock else None
    agent = Agent(api_client=api_client)

    mode = "mock" if mock else "live"
    print(f"PAYgent CLI ({mode} mode). Type 'quit' to exit.\n")

    # Initial greeting
    response = agent.next("Hi")
    print(f"Agent: {response['message']}\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit cli", "q"}:
            print("Goodbye.")
            break

        response = agent.next(user_input)
        print(f"Agent: {response['message']}\n")


if __name__ == "__main__":
    main()
