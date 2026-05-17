from __future__ import annotations

import re
from datetime import date
from decimal import Decimal


def validate_account_id(account_id: str | None) -> bool:
    return bool(account_id and re.fullmatch(r"ACC\d+", account_id))


def validate_dob(dob: str | None) -> bool:
    if not dob:
        return False
    try:
        date.fromisoformat(dob)
        return True
    except ValueError:
        return False


def validate_full_name_format(name: str | None) -> bool:
    if not name:
        return False
    stripped = name.strip()
    if not re.fullmatch(r"[A-Za-z]+(?:\s+[A-Za-z]+)+", stripped):
        return False
    return len(stripped.split()) >= 2


def validate_aadhaar_last4(value: str | None) -> bool:
    if value is None:
        return False
    return bool(re.fullmatch(r"\d{4}", re.sub(r"[\s-]", "", value)))


def validate_pincode(value: str | None) -> bool:
    if value is None:
        return False
    return bool(re.fullmatch(r"\d{6}", re.sub(r"[\s-]", "", value)))


def amount_has_max_two_decimals(amount: Decimal) -> bool:
    return abs(amount.as_tuple().exponent) <= 2


def validate_amount(amount: Decimal | None, balance: Decimal) -> tuple[bool, str | None]:
    if amount is None:
        return False, "Please provide the amount you would like to pay."
    if amount <= 0:
        return False, "Payment amount must be greater than zero."
    if not amount_has_max_two_decimals(amount):
        return False, "Payment amount can have at most 2 decimal places."
    if amount > balance:
        return False, "Payment amount cannot be greater than the outstanding balance. Please enter a lower amount."
    return True, None


def normalize_card_number(card_number: str | None) -> str | None:
    if card_number is None:
        return None
    return re.sub(r"[\s-]", "", card_number)


def luhn_valid(card_number: str) -> bool:
    total = 0
    alternate = False
    for char in reversed(card_number):
        digit = int(char)
        if alternate:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
        alternate = not alternate
    return total % 10 == 0


def validate_card_number(card_number: str | None) -> tuple[bool, str | None]:
    ok, normalized, _ = validate_card_number_detail(card_number)
    return ok, normalized


def validate_card_number_detail(card_number: str | None) -> tuple[bool, str | None, str | None]:
    normalized = normalize_card_number(card_number)
    if not normalized:
        return False, None, "missing"
    if not normalized.isdigit():
        return False, None, "digits"
    if len(normalized) != 16:
        return False, None, "length"
    if not luhn_valid(normalized):
        return False, None, "luhn"
    return True, normalized, None


def validate_cvv(cvv: str | None, card_number: str | None) -> bool:
    if not cvv or not cvv.isdigit():
        return False
    return len(cvv) == 3


def normalize_expiry_year(year: int | None) -> int | None:
    if year is None:
        return None
    return 2000 + year if year < 100 else year


def validate_expiry(month: int | None, year: int | None, today: date) -> tuple[bool, int | None, int | None]:
    year = normalize_expiry_year(year)
    if month is None or year is None:
        return False, month, year
    if month < 1 or month > 12:
        return False, month, year
    if (year, month) < (today.year, today.month):
        return False, month, year
    return True, month, year


def validate_cardholder_name(name: str | None) -> bool:
    return validate_full_name_format(name)
