from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from paygent.stages import Stage


@dataclass
class AccountData:
    account_id: str
    full_name: str
    dob: str
    aadhaar_last4: str
    pincode: str
    balance: Decimal

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "AccountData":
        try:
            return cls(
                account_id=str(payload.get("account_id", "")),
                full_name=str(payload.get("full_name", "")),
                dob=str(payload.get("dob", "")),
                aadhaar_last4=str(payload.get("aadhaar_last4", "")),
                pincode=str(payload.get("pincode", "")),
                balance=Decimal(str(payload.get("balance", "0"))),
            )
        except Exception:
            raise ValueError("Invalid account payload: missing or malformed fields")


@dataclass
class IdentityCandidate:
    full_name: str | None = None
    dob: str | None = None
    aadhaar_last4: str | None = None
    pincode: str | None = None

    def has_secondary(self) -> bool:
        return bool(self.dob or self.aadhaar_last4 or self.pincode)

    def clear(self) -> None:
        self.full_name = None
        self.dob = None
        self.aadhaar_last4 = None
        self.pincode = None


@dataclass
class PaymentCandidate:
    amount: Decimal | None = None
    cardholder_name: str | None = None
    card_number: str | None = None
    cvv: str | None = None
    expiry_month: int | None = None
    expiry_year: int | None = None

    def clear_sensitive(self) -> None:
        self.card_number = None
        self.cvv = None

    def clear_card_fields(self) -> None:
        self.cardholder_name = None
        self.card_number = None
        self.cvv = None
        self.expiry_month = None
        self.expiry_year = None

    def clear(self) -> None:
        self.amount = None
        self.clear_card_fields()


@dataclass
class ApiResult:
    ok: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    message: str | None = None
    retryable: bool = False


@dataclass
class ConversationState:
    stage: Stage = Stage.START
    account_id: str | None = None
    account: AccountData | None = None
    identity: IdentityCandidate = field(default_factory=IdentityCandidate)
    payment: PaymentCandidate = field(default_factory=PaymentCandidate)
    lookup_attempts: int = 0
    verification_attempts: int = 0
    name_mismatch_attempts: int = 0
    payment_attempts: int = 0
    verified: bool = False
    balance_shown: bool = False
    pending_payment_amount: Decimal | None = None
    last_diagnostics: dict[str, bool | None] = field(default_factory=dict)
    local_payment_validation_failures: dict[str, int] = field(default_factory=dict)
    transaction_id: str | None = None
    last_error_code: str | None = None
    terminal_message: str | None = None

    def reset_for_new_account(self, account_id: str | None = None, *, reset_lookup_attempts: bool = False) -> None:
        self.account_id = account_id
        self.account = None
        self.identity.clear()
        self.payment.clear()
        if reset_lookup_attempts:
            self.lookup_attempts = 0
        self.verification_attempts = 0
        self.name_mismatch_attempts = 0
        self.payment_attempts = 0
        self.verified = False
        self.balance_shown = False
        self.pending_payment_amount = None
        self.last_diagnostics = {}
        self.local_payment_validation_failures = {}
        self.transaction_id = None
        self.last_error_code = None
        self.terminal_message = None
