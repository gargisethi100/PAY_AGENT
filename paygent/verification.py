from __future__ import annotations

from dataclasses import dataclass, field

from paygent.state import AccountData, IdentityCandidate


@dataclass
class VerificationResult:
    verified: bool
    complete_attempt: bool
    missing_fields: list[str] = field(default_factory=list)


def verify_identity(account: AccountData, candidate: IdentityCandidate) -> VerificationResult:
    missing = []
    if not candidate.full_name:
        missing.append("full_name")
    if not candidate.has_secondary():
        missing.append("secondary_factor")
    if missing:
        return VerificationResult(verified=False, complete_attempt=False, missing_fields=missing)

    name_matches = candidate.full_name.strip() == account.full_name
    secondary_matches = any(
        [
            candidate.dob == account.dob if candidate.dob else False,
            candidate.aadhaar_last4 == account.aadhaar_last4 if candidate.aadhaar_last4 else False,
            candidate.pincode == account.pincode if candidate.pincode else False,
        ]
    )
    return VerificationResult(verified=name_matches and secondary_matches, complete_attempt=True)
