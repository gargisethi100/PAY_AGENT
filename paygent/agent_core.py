from __future__ import annotations

from collections.abc import Callable
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import re

<<<<<<< HEAD
from paygent.config import default_today
from paygent.extraction import ExtractedFields
from paygent.llm_extraction import (
    LLMExtractionProvider,
    default_llm_extractor,
    is_llm_required,
    understand_fields,
)
=======
import logging
import os

from paygent.config import NAME_MISMATCH_ATTEMPT_LIMIT, default_today
from paygent.extraction import ExtractedFields, extract_fields as extract_rule_fields
from paygent.llm_extraction import extract_fields_with_llm_fallback
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
from paygent.policy import (
    AccountChangeDecision,
    account_change_decision,
    is_cancellation,
)
from paygent.responses import (
    account_switch_started,
    account_not_found,
    api_unavailable,
    ask_account_id,
    ask_card_details,
    ask_full_name,
    ask_missing_card_fields,
    ask_secondary_factor,
    cancelled,
<<<<<<< HEAD
    identity_field_error,
=======
    card_validation_errors,
    confirm_relative_amount,
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
    invalid_account_id,
    invalid_amount,
    invalid_dob_format,
    name_mismatch_prompt,
    partial_verification_prompt,
    payment_failed_terminal,
    payment_field_error,
    payment_success,
    show_balance,
    terminal_acknowledgement,
    terminal_closed_flow,
    terminal_zero_balance_acknowledgement,
    verification_failed,
    zero_balance,
)
from paygent.stages import TERMINAL_STAGES, Stage
from paygent.state import AccountData, ApiResult, ConversationState
from paygent.tools.api_client import PaymentApiClient
from paygent.validators import (
    validate_account_id,
    validate_amount,
    validate_card_number_detail,
    validate_cardholder_name,
    validate_cvv,
    validate_expiry,
)
from paygent.verification import verify_identity


_DEBUG = os.environ.get("PAYGENT_DEBUG", "").lower() in {"1", "true", "yes"}

_BLUE = "\033[94m"
_CYAN = "\033[96m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_DIM = "\033[2m"
_RESET = "\033[0m"


def _mask_for_debug(value: str | None, keep: int = 4) -> str | None:
    """Mask sensitive values for debug output."""
    if value is None:
        return None
    if len(value) <= keep:
        return "****"
    return value[:keep] + "****"


class PaymentAgentCore:
    def __init__(
        self,
        api_client=None,
        today_provider: Callable[[], date] | None = None,
<<<<<<< HEAD
        llm_extractor: LLMExtractionProvider | None = None,
    ):
        self.api_client = api_client or PaymentApiClient()
        self.today_provider = today_provider or default_today
        self.llm_extractor = llm_extractor if llm_extractor is not None else default_llm_extractor()
        self.llm_required = False if llm_extractor is not None else is_llm_required()
=======
        llm_extractor=None,
    ):
        self.api_client = api_client or PaymentApiClient()
        self.today_provider = today_provider or default_today
        self.llm_extractor = llm_extractor
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
        self.state = ConversationState()
        self._debug = _DEBUG
        self._turn = 0

    def _log_debug(self, label: str, info: str) -> None:
        if self._debug:
            print(f"  {_DIM}{label}:{_RESET} {info}")

    def _log_extraction(self, extracted: ExtractedFields) -> None:
        if not self._debug:
            return
        fields = {}
        if extracted.account_id:
            fields["account_id"] = extracted.account_id
        if extracted.account_change_requested:
            fields["account_change"] = True
        if extracted.full_name:
            fields["name"] = extracted.full_name
        if extracted.alias_name_attempt:
            fields["alias_attempt"] = True
        if extracted.dob:
            fields["dob"] = "****"
        if extracted.aadhaar_last4:
            fields["aadhaar"] = "****"
        if extracted.pincode:
            fields["pincode"] = "****"
        if extracted.amount is not None:
            fields["amount"] = str(extracted.amount)
        if extracted.relative_amount_fraction is not None:
            fields["relative_amount"] = str(extracted.relative_amount_fraction)
        if extracted.full_amount_requested:
            fields["full_amount"] = True
        if extracted.cardholder_name:
            fields["cardholder"] = extracted.cardholder_name
        if extracted.card_number:
            fields["card"] = _mask_for_debug(extracted.card_number)
        if extracted.cvv:
            fields["cvv"] = "***"
        if extracted.expiry_month:
            fields["expiry_m"] = extracted.expiry_month
        if extracted.expiry_year:
            fields["expiry_y"] = extracted.expiry_year
        if extracted.invalid_cvv_attempt:
            fields["invalid_cvv"] = True
        if extracted.invalid_expiry_attempt:
            fields["invalid_expiry"] = True
        if extracted.invalid_dob_attempt:
            fields["invalid_dob"] = True

        if fields:
            parts = [f"{k}={v}" for k, v in fields.items()]
            self._log_debug("Extracted", ", ".join(parts))
        else:
            self._log_debug("Extracted", "(nothing)")

    def next(self, user_input: str) -> str:
        text = user_input or ""
        self._turn += 1

        if self._debug:
            print(f"\n{_BLUE}[Turn {self._turn}]{_RESET} {_CYAN}Stage={self.state.stage.value}{_RESET}")
            # Show user input but redact long digit sequences
            display = re.sub(r"(\d[\s-]*){10,}", "****", text)
            print(f"  {_DIM}Input:{_RESET} {display!r}")

        if self.state.stage in TERMINAL_STAGES:
            response = self._handle_terminal_input(text)
            self._log_response(response)
            return response

        if self.llm_required and self.llm_extractor is None:
            return self._close(Stage.API_UNAVAILABLE_CLOSE, api_unavailable())

        if self.state.stage == Stage.START:
<<<<<<< HEAD
            extracted = understand_fields(text, self.state.stage, self.llm_extractor)
=======
            extracted = self._extract_fields(text)
            self._log_extraction(extracted)
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
            self._merge_pre_verification_candidates(extracted)
            self.state.stage = Stage.AWAIT_ACCOUNT_ID
            response = ask_account_id()
            self._log_response(response)
            return response

        if is_cancellation(text):
            self._log_debug("Action", "Cancellation detected")
            self.state.payment.clear_sensitive()
            response = self._close(Stage.CANCELLED_CLOSE, cancelled())
            self._log_response(response)
            return response

        extracted = self._extract_fields(text)
        self._log_extraction(extracted)

        if extracted.account_change_requested:
            self._log_debug("Action", "Account change requested")
            response = self._start_account_switch(extracted)
            self._log_response(response)
            return response

<<<<<<< HEAD
        extracted = understand_fields(text, self.state.stage, self.llm_extractor)
=======
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
        decision = account_change_decision(self.state, extracted)
        if decision == AccountChangeDecision.RESET_TO_NEW_ACCOUNT:
            self._log_debug("Action", "Account switch (new ID detected)")
            response = self._start_account_switch(extracted)
            self._log_response(response)
            return response

        if self.state.stage == Stage.AWAIT_ACCOUNT_ID:
            response = self._handle_account_id(text, extracted)
        elif self.state.stage == Stage.AWAIT_FULL_NAME:
            response = self._handle_full_name(extracted)
        elif self.state.stage == Stage.AWAIT_SECONDARY_FACTOR:
            response = self._handle_secondary_factor(extracted)
        elif self.state.stage == Stage.AWAIT_PAYMENT_AMOUNT:
            response = self._handle_payment_amount(text, extracted)
        elif self.state.stage == Stage.AWAIT_CARD_DETAILS:
            response = self._handle_card_details(extracted)
        else:
            response = ask_account_id()

        self._log_response(response)
        return response

    def _log_response(self, response: str) -> None:
        if self._debug:
            stage_after = self.state.stage.value
            print(f"  {_DIM}Stage->{_RESET} {_GREEN}{stage_after}{_RESET}")
            # Truncate long responses for readability
            display = response[:120] + "..." if len(response) > 120 else response
            print(f"  {_YELLOW}Response:{_RESET} {display}")

    def _handle_account_id(self, text: str, extracted: ExtractedFields) -> str:
        if extracted.account_id:
            self.state.account_id = extracted.account_id

        if not self.state.account_id:
            if _looks_like_account_attempt(text):
                return invalid_account_id()
            return ask_account_id()

        if not validate_account_id(self.state.account_id):
            self.state.account_id = None
            return invalid_account_id()

        result = self.api_client.lookup_account(self.state.account_id)
        if result.retryable:
            return self._close(Stage.API_UNAVAILABLE_CLOSE, api_unavailable())
        if not result.ok:
            self.state.lookup_attempts += 1
            remaining = 3 - self.state.lookup_attempts
            self.state.reset_for_new_account()
            if remaining <= 0:
                return self._close(Stage.ACCOUNT_LOOKUP_FAILED_CLOSE, account_not_found(remaining))
            return account_not_found(remaining)

        try:
            self.state.account = AccountData.from_payload(result.data or {})
        except (ValueError, TypeError):
            return self._close(Stage.API_UNAVAILABLE_CLOSE, api_unavailable())
        self.state.account_id = self.state.account.account_id
        self.state.stage = Stage.AWAIT_FULL_NAME
        return ask_full_name()

    def _handle_full_name(self, extracted: ExtractedFields) -> str:
        if extracted.alias_name_attempt and not extracted.full_name:
            self.state.identity.full_name = None
            self.state.last_diagnostics["alias_name_mismatch"] = True
            return partial_verification_prompt(missing_name=True, missing_secondary=False)
        self._merge_identity_candidates(extracted)
        if extracted.full_name:
            self.state.last_diagnostics["full_name_detected"] = True
        if not self.state.identity.full_name:
            return partial_verification_prompt(missing_name=True, missing_secondary=False)
        if self.state.account and self.state.identity.full_name.strip() != self.state.account.full_name:
            self.state.identity.full_name = None
            self.state.name_mismatch_attempts += 1
            self.state.stage = Stage.AWAIT_FULL_NAME
            self.state.last_diagnostics["alias_name_mismatch"] = True
            self.state.last_diagnostics["full_name_exact_match"] = False
            self.state.last_diagnostics["name_mismatch"] = True
            if self.state.name_mismatch_attempts >= NAME_MISMATCH_ATTEMPT_LIMIT:
                return self._close(Stage.VERIFICATION_FAILED_CLOSE, verification_failed(0))
            return name_mismatch_prompt()
        self.state.last_diagnostics["full_name_exact_match"] = True
        self.state.stage = Stage.AWAIT_SECONDARY_FACTOR
        return ask_secondary_factor()

    def _handle_secondary_factor(self, extracted: ExtractedFields) -> str:
        invalid_secondary = extracted.invalid_fields.intersection({"dob", "aadhaar_last4", "pincode"})
        if invalid_secondary:
            return identity_field_error(sorted(invalid_secondary)[0])

        self._merge_identity_candidates(extracted)
        if extracted.dob or extracted.aadhaar_last4 or extracted.pincode:
            self.state.last_diagnostics["secondary_factor_detected"] = True
        # If user tried to provide a DOB but the date was invalid, give clear feedback
        if extracted.invalid_dob_attempt and not extracted.dob:
            return invalid_dob_format()
        result = verify_identity(self.state.account, self.state.identity) if self.state.account else None
        if result is None:
            return self._close(Stage.API_UNAVAILABLE_CLOSE, api_unavailable())
        if not result.complete_attempt:
            return partial_verification_prompt(
                missing_name="full_name" in result.missing_fields,
                missing_secondary="secondary_factor" in result.missing_fields,
            )
        if result.verified:
            self.state.verified = True
            self.state.balance_shown = True
            balance = self.state.account.balance
            if balance == Decimal("0.00"):
                self.state.last_diagnostics["zero_balance_close_reached"] = True
                return self._close(Stage.ZERO_BALANCE_CLOSE, zero_balance())
            self.state.stage = Stage.AWAIT_PAYMENT_AMOUNT
            return show_balance(balance)

        self.state.verification_attempts += 1
        remaining = 3 - self.state.verification_attempts
        self.state.identity.clear()
        if remaining <= 0:
            return self._close(Stage.VERIFICATION_FAILED_CLOSE, verification_failed(remaining))
        self.state.stage = Stage.AWAIT_FULL_NAME
        return verification_failed(remaining)

    def _handle_payment_amount(self, text: str, extracted: ExtractedFields) -> str:
        account = self.state.account
        if not account or not self.state.verified:
            return ask_account_id()

        if extracted.full_amount_requested:
            self.state.pending_payment_amount = None
            return self._accept_payment_amount(account.balance)
        if extracted.amount is not None:
            self.state.pending_payment_amount = None
            return self._validate_and_accept_payment_amount(extracted.amount, account.balance)
        if extracted.relative_amount_fraction is not None:
            amount = (account.balance * extracted.relative_amount_fraction).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
            valid, reason = validate_amount(amount, account.balance)
            if not valid:
                return invalid_amount(reason or "Please enter a valid amount.")
            self.state.pending_payment_amount = amount
            return confirm_relative_amount(amount)
        if self.state.pending_payment_amount is not None:
            if _is_affirmative(text):
                amount = self.state.pending_payment_amount
                self.state.pending_payment_amount = None
                return self._accept_payment_amount(amount)
            if _is_negative(text):
                self.state.pending_payment_amount = None
                # Check if user also provided a new amount in the same message (e.g. "no, 1700")
                inline_amount = _extract_bare_number(text)
                if inline_amount is not None:
                    return self._validate_and_accept_payment_amount(inline_amount, account.balance)
                return invalid_amount("Please tell me how much you would like to pay.")

        amount = extracted.amount
        if amount is None:
            return invalid_amount("Please tell me how much you would like to pay.")

        return self._validate_and_accept_payment_amount(amount, account.balance)

    def _validate_and_accept_payment_amount(self, amount: Decimal, balance: Decimal) -> str:
        valid, reason = validate_amount(amount, balance)
        if not valid:
            return invalid_amount(reason or "Please enter a valid amount.")
        return self._accept_payment_amount(amount)

    def _accept_payment_amount(self, amount: Decimal) -> str:
        self.state.payment.clear_card_fields()
        self.state.last_diagnostics = {}
        self.state.local_payment_validation_failures = {}
        self.state.payment.amount = amount
        self.state.stage = Stage.AWAIT_CARD_DETAILS
        return ask_card_details()

    def _handle_card_details(self, extracted: ExtractedFields) -> str:
        invalid_card_fields = extracted.invalid_fields.intersection(
            {"cardholder_name", "card_number", "cvv", "expiry"}
        )
        if invalid_card_fields:
            return payment_field_error(sorted(invalid_card_fields)[0])

        self._merge_card_candidates(extracted)
<<<<<<< HEAD
        if self.state.payment.cardholder_name and not validate_cardholder_name(self.state.payment.cardholder_name):
            return payment_field_error("cardholder_name")

=======
        self._update_payment_diagnostics(extracted)

        # Track invalid format attempts — clear the bad value and note the issue
        format_hints: list[str] = []
        if extracted.invalid_cvv_attempt:
            self.state.payment.cvv = None
            self.state.last_diagnostics["cvv_format_valid"] = False
            format_hints.append("CVV must be 3 digits, or 4 for Amex")
        if extracted.invalid_expiry_attempt:
            self.state.payment.expiry_month = None
            self.state.payment.expiry_year = None
            self.state.last_diagnostics["expiry_valid"] = False
            format_hints.append("Expiry should be in MM/YY or MM/YYYY format")

        # Re-validate stored CVV against new card type (Amex needs 4 digits, others 3)
        if extracted.card_number and self.state.payment.cvv:
            if not validate_cvv(self.state.payment.cvv, self.state.payment.card_number):
                self.state.payment.cvv = None
                self.state.last_diagnostics["cvv_format_valid"] = False

        # Collect all missing fields first — don't validate until everything is present
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
        missing = self._missing_card_fields()
        if missing:
            return ask_missing_card_fields(missing, self.state.payment, format_hints=format_hints)

        # All fields present — now validate them all together
        errors: list[str] = []

        card_ok, normalized_card, card_error = validate_card_number_detail(self.state.payment.card_number)
        if not card_ok:
            self.state.payment.card_number = None
<<<<<<< HEAD
            return payment_field_error("card_number_luhn" if card_error == "luhn" else "card_number")
=======
            self.state.last_diagnostics["card_number_valid"] = False
            self._record_local_payment_failure("card_number")
            errors.append("card number")
        else:
            self._clear_local_payment_failure("card_number")
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

        expiry_ok, month, year = validate_expiry(
            self.state.payment.expiry_month,
            self.state.payment.expiry_year,
            self.today_provider(),
        )
        if not expiry_ok:
            self.state.payment.expiry_month = None
            self.state.payment.expiry_year = None
            self.state.last_diagnostics["expiry_valid"] = False
            self._record_local_payment_failure("expiry")
            errors.append("expiry")
        else:
            self._clear_local_payment_failure("expiry")

        cvv_valid = validate_cvv(
            self.state.payment.cvv, normalized_card if card_ok else self.state.payment.card_number
        )
        if not cvv_valid:
            self.state.payment.cvv = None
            self.state.last_diagnostics["cvv_format_valid"] = False
            self._record_local_payment_failure("cvv")
            errors.append("CVV")
        else:
            self._clear_local_payment_failure("cvv")

        if errors:
            return card_validation_errors(errors)

        if not validate_cardholder_name(self.state.payment.cardholder_name):
<<<<<<< HEAD
            return payment_field_error("cardholder_name")
=======
            return ask_missing_card_fields(["cardholder name"], self.state.payment)
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d

        payload = {
            "account_id": self.state.account_id,
            "amount": float(self.state.payment.amount.quantize(Decimal("0.01"))),
            "payment_method": {
                "type": "card",
                "card": {
                    "cardholder_name": self.state.payment.cardholder_name.strip(),
                    "card_number": normalized_card,
                    "cvv": self.state.payment.cvv,
                    "expiry_month": month,
                    "expiry_year": year,
                },
            },
        }

        card_last4 = normalized_card[-4:] if normalized_card else None
        self.state.payment_attempts += 1
        result = self.api_client.process_payment(payload)
        if result.retryable:
            self.state.payment.clear_sensitive()
            return self._close(Stage.API_UNAVAILABLE_CLOSE, api_unavailable())
        if result.ok:
            self.state.payment.clear_sensitive()
            transaction_id = (result.data or {}).get("transaction_id", "")
            self.state.transaction_id = transaction_id
            return self._close(
                Stage.SUCCESS_CLOSE,
                payment_success(
                    self.state.payment.amount or Decimal("0.00"),
                    transaction_id,
                    card_last4=card_last4,
                ),
            )
        return self._handle_payment_failure(result)

    def _handle_payment_failure(self, result: ApiResult) -> str:
        self.state.last_error_code = result.error_code
        if self.state.payment_attempts >= 3:
            self.state.payment.clear_sensitive()
            return self._close(Stage.PAYMENT_FAILED_CLOSE, payment_failed_terminal())

        if result.error_code == "invalid_card":
            self.state.payment.card_number = None
            return payment_field_error("invalid_card_api")
        if result.error_code == "invalid_cvv":
            self.state.payment.cvv = None
            return payment_field_error("invalid_cvv_api")
        if result.error_code == "invalid_expiry":
            self.state.payment.expiry_month = None
            self.state.payment.expiry_year = None
            return payment_field_error("invalid_expiry_api")
        if result.error_code == "insufficient_balance":
            self.state.payment.clear()
            self.state.stage = Stage.AWAIT_PAYMENT_AMOUNT
            return payment_field_error("insufficient_balance")
        if result.error_code == "invalid_amount":
            self.state.payment.clear()
            self.state.stage = Stage.AWAIT_PAYMENT_AMOUNT
            return payment_field_error("amount")
        self.state.payment.clear_sensitive()
        return payment_field_error("payment")

    def _merge_pre_verification_candidates(self, extracted: ExtractedFields) -> None:
        if extracted.account_id:
            self.state.account_id = extracted.account_id
        self._merge_identity_candidates(extracted)
        if extracted.amount is not None:
            self.state.payment.amount = extracted.amount

    def _merge_identity_candidates(self, extracted: ExtractedFields) -> None:
        if extracted.full_name:
            self.state.identity.full_name = extracted.full_name
        if extracted.dob:
            self.state.identity.dob = extracted.dob
        if extracted.aadhaar_last4:
            self.state.identity.aadhaar_last4 = extracted.aadhaar_last4
        if extracted.pincode:
            self.state.identity.pincode = extracted.pincode

    def _merge_card_candidates(self, extracted: ExtractedFields) -> None:
        if extracted.cardholder_name:
            self.state.payment.cardholder_name = extracted.cardholder_name
        if extracted.card_number:
            self.state.payment.card_number = extracted.card_number
        if extracted.cvv:
            self.state.payment.cvv = extracted.cvv
        if extracted.expiry_month:
            self.state.payment.expiry_month = extracted.expiry_month
        if extracted.expiry_year:
            self.state.payment.expiry_year = extracted.expiry_year

    def _update_payment_diagnostics(self, extracted: ExtractedFields) -> None:
        diagnostics = dict(self.state.last_diagnostics)
        if extracted.card_number:
            diagnostics["card_number_detected"] = True
        if extracted.cvv or extracted.invalid_cvv_attempt:
            diagnostics["cvv_detected"] = True
        if extracted.bare_cvv_detected:
            diagnostics["bare_cvv_detected"] = True
        if extracted.expiry_month or extracted.expiry_year or extracted.invalid_expiry_attempt:
            diagnostics["expiry_detected"] = True
        if self.state.payment.card_number:
            diagnostics.setdefault("card_number_valid", True)
        if self.state.payment.cvv:
            diagnostics.setdefault("cvv_format_valid", True)
        if self.state.payment.expiry_month and self.state.payment.expiry_year:
            diagnostics.setdefault("expiry_valid", True)
        self.state.last_diagnostics = diagnostics

    def _handle_terminal_input(self, text: str) -> str:
        extracted = extract_rule_fields(text, Stage.AWAIT_ACCOUNT_ID)
        if extracted.account_change_requested or extracted.account_id or _is_new_account_request(text):
            return self._start_account_switch(extracted, from_terminal=True)

        self.state.last_diagnostics["terminal_followup_detected"] = True
        if _is_terminal_acknowledgement(text):
            if _as_stage(self.state.stage) == Stage.ZERO_BALANCE_CLOSE:
                return terminal_zero_balance_acknowledgement()
            return terminal_acknowledgement()

        return terminal_closed_flow()

    def _start_account_switch(self, extracted: ExtractedFields, *, from_terminal: bool = False) -> str:
        account_id = extracted.account_id
        self.state.reset_for_new_account(account_id, reset_lookup_attempts=True)
        self.state.last_diagnostics["account_switch_requested"] = True
        self.state.last_diagnostics["account_reset_performed"] = True
        if from_terminal:
            self.state.last_diagnostics["terminal_account_switch_requested"] = True
        self.state.stage = Stage.AWAIT_ACCOUNT_ID
        if account_id:
            return self._handle_account_id("", extracted)
        return account_switch_started()

    def _record_local_payment_failure(self, field: str) -> int:
        failures = self.state.local_payment_validation_failures.get(field, 0) + 1
        self.state.local_payment_validation_failures[field] = failures
        self.state.last_diagnostics[f"{field}_local_failures"] = True
        return failures

    def _clear_local_payment_failure(self, field: str) -> None:
        self.state.local_payment_validation_failures.pop(field, None)

    def _missing_card_fields(self) -> list[str]:
        missing = []
        if not validate_cardholder_name(self.state.payment.cardholder_name):
            missing.append("cardholder name")
        if not self.state.payment.card_number:
            missing.append("card number")
        if not self.state.payment.cvv:
            missing.append("CVV")
        if not self.state.payment.expiry_month or not self.state.payment.expiry_year:
            missing.append("expiry")
        return missing

    def _extract_fields(self, text: str) -> ExtractedFields:
        return extract_fields_with_llm_fallback(text, self.state.stage, self.llm_extractor)

    def _close(self, stage: Stage, message: str) -> str:
        self.state.stage = stage
        self.state.terminal_message = message
        return message


def _looks_like_account_attempt(text: str) -> bool:
    stripped = text.strip()
    if re.fullmatch(r"\d{3,}", stripped):
        return True
    if re.search(r"\baccount\b", text, re.I):
        return True
    return bool(re.search(r"\b[A-Z]{2,5}\s*-?\s*\d{3,}\b", text, re.I))


def _is_affirmative(text: str) -> bool:
    return bool(re.fullmatch(r"\s*(yes|y|yeah|yep|ok|okay|confirm|confirmed|haan|ha)\s*[.!]?\s*", text, re.I))


def _is_negative(text: str) -> bool:
    return bool(re.search(r"\b(no|nope|nah|nahi|cancel)\b", text, re.I))


def _is_terminal_acknowledgement(text: str) -> bool:
    return bool(
        re.fullmatch(
            r"\s*(thanks?|thank you|cool thanks?|cool|ok|okay|great|nice|awesome|perfect|fine|got it|done)\s*[.!]?\s*",
            text,
            re.I,
        )
    )


def _is_new_account_request(text: str) -> bool:
    return bool(re.search(r"\b(?:new|another|different)\s+account(?:\s+flow)?\b", text, re.I))


def _as_stage(stage: Stage | str) -> Stage | None:
    try:
        return Stage(stage)
    except ValueError:
        return None


def _extract_bare_number(text: str) -> Decimal | None:
    """Extract a standalone number from text, ignoring non-numeric words."""
    match = re.search(r"\b(\d[\d,]*(?:\.\d+)?)\b", text)
    if match:
        try:
            return Decimal(match.group(1).replace(",", ""))
        except Exception:
            return None
    return None


def _valid_cvv_shape(cvv: str | None) -> bool:
    return bool(cvv and cvv.isdigit() and len(cvv) in {3, 4})
