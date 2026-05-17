from __future__ import annotations

import re
from enum import StrEnum

from paygent.extraction import ExtractedFields
from paygent.stages import Stage
from paygent.state import ConversationState
from paygent.validators import validate_account_id


class AccountChangeDecision(StrEnum):
    NONE = "NONE"
    RESET_TO_NEW_ACCOUNT = "RESET_TO_NEW_ACCOUNT"
    RESTART_REQUIRED = "RESTART_REQUIRED"


CANCEL_PATTERNS = [
    r"^\s*(?:please\s+)?cancel\s*[.!]?\s*$",
    r"^\s*(?:please\s+)?stop\s*[.!]?\s*$",
    r"^\s*(?:please\s+)?exit\s*[.!]?\s*$",
    r"\bcancel\s+(?:this|the|my)?\s*(?:payment|flow|transaction|process)\b",
    r"\b(?:please\s+)?stop\s+(?:this|the|my)?\s*(?:payment|flow|transaction|process)\b",
    r"\bi\s+(?:want\s+to|wanna)\s+cancel\b",
    r"\bi\s+do\s+not\s+want\s+to\s+continue\b",
    r"\bi\s+don't\s+want\s+to\s+continue\b",
    r"\bi\s+do\s+not\s+want\s+to\s+pay\s+now\b",
    r"\bi\s+don't\s+want\s+to\s+pay\s+now\b",
    r"\bi\s+(?:do\s+not|don't)\s+want\s+to\s+(?:pay|proceed)\b",
    r"^\s*abort\s*[.!]?\s*$",
    r"\bnevermind\b",
    r"\bnever\s*mind\b",
]

# Negation patterns that override cancellation (e.g., "don't stop the payment")
CANCEL_NEGATION_PATTERNS = [
    r"\b(?:don't|do\s+not|dont)\s+(?:cancel|stop)\b",
    r"\b(?:no|not)\s+cancel\b",
]

SENSITIVE_KEYS = {"dob", "aadhaar_last4", "pincode", "card_number", "cvv"}


def is_cancellation(text: str) -> bool:
    if any(re.search(pattern, text, re.I) for pattern in CANCEL_NEGATION_PATTERNS):
        return False
    return any(re.search(pattern, text, re.I) for pattern in CANCEL_PATTERNS)


def account_change_decision(state: ConversationState, extracted: ExtractedFields) -> AccountChangeDecision:
    if not extracted.account_id or not validate_account_id(extracted.account_id):
        return AccountChangeDecision.NONE
    if not state.account_id or extracted.account_id == state.account_id:
        return AccountChangeDecision.NONE
    return AccountChangeDecision.RESET_TO_NEW_ACCOUNT


def can_show_balance(state: ConversationState) -> bool:
    return bool(state.verified and state.account)


def can_collect_amount(state: ConversationState) -> bool:
    return bool(state.verified and state.balance_shown and state.account)


def can_collect_card_details(state: ConversationState) -> bool:
    return bool(can_collect_amount(state) and state.payment.amount is not None)


def can_process_payment(state: ConversationState) -> bool:
    payment = state.payment
    return bool(
        can_collect_card_details(state)
        and payment.cardholder_name
        and payment.card_number
        and payment.cvv
        and payment.expiry_month
        and payment.expiry_year
    )


def redact_sensitive(value):
    if isinstance(value, dict):
        return {
            key: ("[REDACTED]" if key in SENSITIVE_KEYS else redact_sensitive(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, str):
        redacted = value
        redacted = re.sub(r"\b\d{4}-\d{1,2}-\d{1,2}\b", "[REDACTED_DATE]", redacted)
        redacted = re.sub(r"\b\d{1,2}-\d{1,2}-\d{2,4}\b", "[REDACTED_DATE]", redacted)
        redacted = re.sub(
            r"(\b(?:dob|date of birth|born on|born)\b[^\d,.;\n]*)(\d{1,4}(?:[-/]\d{1,2}){1,2})",
            r"\1[REDACTED_DATE]",
            redacted,
            flags=re.I,
        )
        redacted = re.sub(
            r"(\b(?:aadhaar|aadhar)\b[^,.;\n]*?)(\d(?:[\s-]*\d){3,})",
            r"\1[REDACTED_AADHAAR]",
            redacted,
            flags=re.I,
        )
        redacted = re.sub(
            r"(\b(?:pin\s*code|pincode|pin)\b[^\d,.;\n]*)(\d(?:[\s-]*\d){5})",
            r"\1[REDACTED_PINCODE]",
            redacted,
            flags=re.I,
        )
        redacted = re.sub(r"\b(?:\d[\s-]*){13,19}\b", "[REDACTED_CARD]", redacted)
        redacted = re.sub(
            r"(\bcvv\b[^\d,.;\n]*)(\d{3,4})",
            r"\1[REDACTED_CVV]",
            redacted,
            flags=re.I,
        )
        return redacted
    return value
