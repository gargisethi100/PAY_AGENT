from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from paygent.state import PaymentCandidate


def money(amount: Decimal) -> str:
    return f"Rs. {amount:,.2f}"


def _mask_card(card_number: str | None) -> str | None:
    """Return last 4 digits of card number, masked."""
    if not card_number or len(card_number) < 4:
        return None
    return f"****{card_number[-4:]}"


def ask_account_id() -> str:
    return "Hello! Please share your account ID to get started."


def account_switch_started() -> str:
    return "I have started a fresh account flow. Please share the new account ID."


def invalid_account_id() -> str:
    return "Please provide a valid account ID in the format ACC followed by digits, for example ACC1001."


def account_not_found(remaining: int) -> str:
    if remaining <= 0:
        return "I could not find an account with those details. Please contact support for help."
    return "I could not find that account ID. Please check it and share the account ID again."


def ask_full_name() -> str:
    return "Got it. Could you please confirm your full name?"


def ask_secondary_factor() -> str:
    return "Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode."


def invalid_dob_format() -> str:
    return (
        "That date does not appear to be valid. "
        "Please provide your date of birth in a format like DD-MM-YYYY, YYYY-MM-DD, or 14th May 1990."
    )


def partial_verification_prompt(missing_name: bool, missing_secondary: bool) -> str:
    if missing_name and missing_secondary:
        return "Please provide your full name plus your date of birth, Aadhaar last 4 digits, or pincode."
    if missing_name:
        return "Please provide your full legal name using letters and spaces only, exactly as registered on the account, including capitalization."
    return "Please provide your date of birth, Aadhaar last 4 digits, or pincode to complete verification."


<<<<<<< HEAD
def identity_field_error(field: str) -> str:
    prompts = {
        "dob": "Please provide your date of birth in YYYY-MM-DD format.",
        "aadhaar_last4": "Please provide the Aadhaar last 4 digits as exactly 4 digits.",
        "pincode": "Please provide the pincode as exactly 6 digits.",
    }
    return prompts.get(field, "Please provide the requested verification detail in a valid format.")
=======
def name_mismatch_prompt() -> str:
    return (
        "That name could not be verified for this account. Please enter the exact registered full legal name, "
        'or say "change account ID" if this is the wrong account.'
    )
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d


def verification_failed(remaining: int) -> str:
    if remaining <= 0:
        return "I could not verify your identity after multiple attempts. Please contact support for help."
    return "I could not verify those details. Please try again with your full name and one verification detail."


def show_balance(balance: Decimal) -> str:
    return f"Identity verified. Your outstanding balance is {money(balance)}. How much would you like to pay today?"


def zero_balance() -> str:
    return "Identity verified. There is no outstanding balance on this account, so no payment is needed."


def terminal_acknowledgement() -> str:
    return "You're welcome. This flow is closed. You can start a new account flow if needed."


def terminal_zero_balance_acknowledgement() -> str:
    return (
        "You're welcome. This account has no outstanding balance, so this flow is closed. "
        "You can start a new account flow if needed."
    )


def terminal_closed_flow() -> str:
    return "This flow is closed. Say change account ID or share a new account ID to start a new account flow."


def ask_amount(balance: Decimal) -> str:
    return f"Your outstanding balance is {money(balance)}. How much would you like to pay today?"


def invalid_amount(reason: str = "Please enter a valid payment amount.") -> str:
    return reason


def confirm_relative_amount(amount: Decimal) -> str:
    return f"That comes to {money(amount)}. Please confirm if you want to pay this amount, or enter a different amount."


def ask_card_details() -> str:
    return "Please provide the cardholder name, card number, expiry, and CVV to process the payment."


def _card_summary(payment: PaymentCandidate | None) -> str:
    """Build a summary of card fields already collected."""
    if payment is None:
        return ""
    parts = []
    if payment.cardholder_name:
        parts.append(f"Name: {payment.cardholder_name}")
    if payment.card_number:
        parts.append(f"Card: {_mask_card(payment.card_number)}")
    if payment.expiry_month and payment.expiry_year:
        parts.append(f"Expiry: {payment.expiry_month:02d}/{payment.expiry_year}")
    if payment.cvv:
        parts.append("CVV: ***")
    if not parts:
        return ""
    return " Collected so far: " + ", ".join(parts) + "."


def ask_missing_card_fields(
    fields: list[str],
    payment: PaymentCandidate | None = None,
    format_hints: list[str] | None = None,
) -> str:
    readable = ", ".join(fields)
    summary = _card_summary(payment)
    hint_text = ""
    if format_hints:
        hint_text = " Note: " + ". ".join(format_hints) + "."
    return f"Please provide the missing card detail(s): {readable}.{summary}{hint_text}"


def card_validation_errors(invalid_fields: list[str]) -> str:
    readable = ", ".join(invalid_fields)
    return (
        f"The following detail(s) could not be accepted: {readable}. "
        "Please provide corrected values for these fields."
    )


def payment_success(amount: Decimal, transaction_id: str, card_last4: str | None = None) -> str:
    card_info = f" Card used: ****{card_last4}." if card_last4 else ""
    return (
        f"Payment of {money(amount)} was successful.{card_info} "
        f"Transaction ID: {transaction_id}. Thank you."
    )


def payment_field_error(field: str) -> str:
    prompts = {
<<<<<<< HEAD
        "cardholder_name": "Please provide the cardholder name using letters and spaces only.",
        "card_number": "Please provide a 16-digit card number.",
        "card_number_luhn": "The card number could not be accepted. Please check it and provide a valid 16-digit card number.",
        "cvv": "Please provide a 3-digit CVV.",
=======
        "card_number": "The card number could not be accepted. Please provide a different card number.",
        "card_number_repeated": "The card number still could not be accepted. Please check the digits or use a different card number.",
        "cvv": "The CVV could not be accepted. Please provide the CVV again.",
        "cvv_format": "CVV must be 3 digits, or 4 for Amex. Please provide the CVV again.",
>>>>>>> d98c0438fcfe71d2b3bc6dc910356c149d11116d
        "expiry": "The expiry could not be accepted. Please provide a valid future expiry date.",
        "expiry_format": "The expiry format could not be accepted. Use MM/YY, MM/YYYY, or month and year, for example 02/2030.",
        "amount": "The amount could not be accepted. Please provide a corrected amount.",
        "lower_amount": "That amount is higher than the outstanding balance. Please provide a lower amount.",
        "insufficient_balance": "The payment amount exceeds the outstanding balance. Please enter a lower amount.",
        "invalid_card_api": "The card was declined. Please check the card number and try again, or use a different card.",
        "invalid_cvv_api": "The CVV was declined by the payment processor. Please check the CVV and try again.",
        "invalid_expiry_api": "The card expiry was rejected. The card may be expired. Please check the expiry date or use a different card.",
    }
    return prompts.get(field, "The payment could not be processed. Please check the payment details and try again.")


def payment_failed_terminal() -> str:
    return "I could not process the payment after multiple attempts. Please contact support or try again later."


def api_unavailable() -> str:
    return "The payment service is temporarily unavailable. Please try again later."


def cancelled() -> str:
    return "No problem. I have cancelled this payment flow. You can start again whenever you are ready."


def restart_required_for_account_change() -> str:
    return "This conversation is already verified for another account. Please start a new flow to use a different account."


def already_closed() -> str:
    return "This conversation is already closed. Please start a new session if you need more help."
