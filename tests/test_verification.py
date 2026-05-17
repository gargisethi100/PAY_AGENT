from decimal import Decimal

from paygent.state import AccountData, IdentityCandidate
from paygent.verification import verify_identity


def account():
    return AccountData(
        account_id="ACC1001",
        full_name="Nithin Jain",
        dob="1990-05-14",
        aadhaar_last4="4321",
        pincode="400001",
        balance=Decimal("1250.75"),
    )


def test_strict_name_lowercase_fails_exact_passes():
    result = verify_identity(
        account(),
        IdentityCandidate(full_name="nithin jain", dob="1990-05-14"),
    )
    assert result.complete_attempt
    assert not result.verified

    result = verify_identity(
        account(),
        IdentityCandidate(full_name="Nithin Jain", dob="1990-05-14"),
    )
    assert result.verified


def test_no_internal_whitespace_normalization():
    result = verify_identity(
        account(),
        IdentityCandidate(full_name="Nithin  Jain", dob="1990-05-14"),
    )
    assert result.complete_attempt
    assert not result.verified


def test_partial_verification_is_not_complete_attempt():
    result = verify_identity(account(), IdentityCandidate(full_name="Nithin Jain"))
    assert not result.complete_attempt
    assert "secondary_factor" in result.missing_fields

    result = verify_identity(account(), IdentityCandidate(dob="1990-05-14"))
    assert not result.complete_attempt
    assert "full_name" in result.missing_fields


def test_any_secondary_factor_can_verify():
    assert verify_identity(account(), IdentityCandidate(full_name="Nithin Jain", dob="1990-05-14")).verified
    assert verify_identity(account(), IdentityCandidate(full_name="Nithin Jain", aadhaar_last4="4321")).verified
    assert verify_identity(account(), IdentityCandidate(full_name="Nithin Jain", pincode="400001")).verified
