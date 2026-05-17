from datetime import date
from decimal import Decimal

from paygent.validators import (
    validate_aadhaar_last4,
    validate_account_id,
    validate_amount,
    validate_card_number,
    validate_cvv,
    validate_dob,
    validate_expiry,
    validate_full_name_format,
    validate_pincode,
)


def test_validate_account_id_and_dob():
    assert validate_account_id("ACC1001")
    assert not validate_account_id("1001")
    assert not validate_account_id("ABC1001")
    assert validate_dob("1988-02-29")
    assert not validate_dob("1989-02-29")


def test_validate_name_aadhaar_and_pincode_formats():
    assert validate_full_name_format("Nithin Jain")
    assert validate_full_name_format("Rajarajeswari Balasubramaniam")
    assert not validate_full_name_format("Nithin")
    assert not validate_full_name_format("Nithin Jain2")
    assert not validate_full_name_format("Nithin-Jain")
    assert validate_aadhaar_last4("4 3 2 1")
    assert not validate_aadhaar_last4("432")
    assert not validate_aadhaar_last4("43210")
    assert validate_pincode("4 0 0 0 0 1")
    assert not validate_pincode("40001")
    assert not validate_pincode("4000012")


def test_validate_amount_rules():
    balance = Decimal("1250.75")
    assert validate_amount(Decimal("500.00"), balance)[0]
    assert not validate_amount(Decimal("0"), balance)[0]
    assert not validate_amount(Decimal("-1"), balance)[0]
    assert not validate_amount(Decimal("1.234"), balance)[0]
    assert not validate_amount(Decimal("1250.76"), balance)[0]


def test_validate_card_number_cvv_and_expiry():
    ok, normalized = validate_card_number("4532-0151-1283-0366")
    assert ok
    assert normalized == "4532015112830366"
    assert not validate_card_number("4532015112830367")[0]
    assert not validate_card_number("378282246310005")[0]
    assert not validate_card_number("45320151128303667")[0]
    assert validate_cvv("123", normalized)
    assert not validate_cvv("12", normalized)
    assert not validate_cvv("1234", normalized)
    assert validate_expiry(12, 27, date(2026, 5, 15)) == (True, 12, 2027)
    assert validate_expiry(1, 2020, date(2026, 5, 15))[0] is False
