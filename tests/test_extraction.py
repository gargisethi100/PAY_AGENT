from decimal import Decimal

from paygent.extraction import extract_fields
from paygent.stages import Stage


def test_extract_account_id_variants():
    assert extract_fields("yeah my account number is ACC1001 I think").account_id == "ACC1001"
    assert extract_fields("it's ACC 1001").account_id == "ACC1001"
    assert extract_fields("account id: acc1001").account_id == "ACC1001"


def test_extract_full_name_variants():
    assert extract_fields("Nithin Jain", Stage.AWAIT_FULL_NAME).full_name == "Nithin Jain"
    assert extract_fields("my name is Nithin Jain").full_name == "Nithin Jain"
    assert extract_fields("hey my name is Nithin Jain", Stage.AWAIT_FULL_NAME).full_name == "Nithin Jain"
    assert extract_fields("full name is Nithin Jain").full_name == "Nithin Jain"
    assert extract_fields("it's Nithin, Nithin Jain").full_name == "Nithin Jain"
    assert extract_fields('"it\'s Nithin, Nithin Jain"').full_name == "Nithin Jain"
    text = "you can call me Raja but my full name is Rajarajeswari Balasubramaniam"
    assert extract_fields(text).full_name == "Rajarajeswari Balasubramaniam"
    assert extract_fields("mera naam Nithin Jain hai", Stage.AWAIT_FULL_NAME).full_name == "Nithin Jain"
    assert extract_fields("mera naam nithin jain hai", Stage.AWAIT_FULL_NAME).full_name == "nithin jain"


def test_rejects_alias_or_single_token_as_full_name():
    assert extract_fields("you can call me Raja", Stage.AWAIT_FULL_NAME).full_name is None
    assert extract_fields("call me Raja", Stage.AWAIT_FULL_NAME).full_name is None
    assert extract_fields("Raja", Stage.AWAIT_FULL_NAME).full_name is None
    assert extract_fields("Nithin", Stage.AWAIT_FULL_NAME).full_name is None
    assert extract_fields("my name is gargi", Stage.AWAIT_FULL_NAME).full_name is None
    assert extract_fields("hey my name is gargi", Stage.AWAIT_FULL_NAME).full_name is None


def test_extract_dob_variants():
    assert extract_fields("I was born on 14th May 1990").dob == "1990-05-14"
    assert extract_fields("DOB is May 14, 90").dob == "1990-05-14"
    assert extract_fields("14-05-1990").dob == "1990-05-14"


def test_extract_aadhaar_pincode_amount_and_card():
    assert extract_fields("last four of my Aadhaar is 4321").aadhaar_last4 == "4321"
    assert extract_fields("Aadhaar last 4 is 1357").aadhaar_last4 == "1357"
    assert extract_fields("Aadhaar last four is 1357").aadhaar_last4 == "1357"
    assert extract_fields("last 4 of Aadhaar is 1357").aadhaar_last4 == "1357"
    assert extract_fields("last four of my Aadhaar is 1357").aadhaar_last4 == "1357"
    assert extract_fields("Aadhaar ends with 1357").aadhaar_last4 == "1357"
    assert extract_fields("pincode? it's 4 0 0 0 0 1").pincode == "400001"
    assert extract_fields("400001 is the pincode").pincode == "400001"
    assert extract_fields("I want to pay a thousand rupees").amount == Decimal("1000.00")
    assert extract_fields("can I do 500 for now?").amount == Decimal("500")
    assert extract_fields("just clear the full amount").full_amount_requested is True
    fields = extract_fields("the card number is 4532 0151 1283 0366")
    assert fields.card_number == "4532015112830366"
    assert extract_fields("expires December 2027").expiry_month == 12
    assert extract_fields("expires 12/27").expiry_year == 2027
    assert extract_fields("CVV is one two three").cvv == "123"


def test_extract_stage_aware_payment_amounts():
    assert extract_fields("500", Stage.AWAIT_PAYMENT_AMOUNT).amount == Decimal("500")
    assert extract_fields("500.00", Stage.AWAIT_PAYMENT_AMOUNT).amount == Decimal("500.00")
    assert extract_fields("1,000", Stage.AWAIT_PAYMENT_AMOUNT).amount == Decimal("1000")
    assert extract_fields("500", Stage.AWAIT_ACCOUNT_ID).amount is None
    assert extract_fields("500", Stage.AWAIT_SECONDARY_FACTOR).amount is None
    assert extract_fields("i pay 500", Stage.AWAIT_PAYMENT_AMOUNT).amount == Decimal("500")
    assert extract_fields("i would like to pay rs 500", Stage.AWAIT_PAYMENT_AMOUNT).amount == Decimal("500")
