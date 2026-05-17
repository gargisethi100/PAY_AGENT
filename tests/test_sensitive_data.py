import logging

from paygent.logging_utils import safe_log
from paygent.policy import redact_sensitive


def test_messages_never_contain_sensitive_data(agent_factory, valid_card_text, no_sensitive_values):
    agent = agent_factory()

    messages = [
        agent.next("Hi")["message"],
        agent.next("ACC1001")["message"],
        agent.next("Nithin Jain")["message"],
        agent.next("DOB is 1990-05-14")["message"],
        agent.next("full amount")["message"],
        agent.next(valid_card_text)["message"],
    ]

    no_sensitive_values(messages)


def test_redact_sensitive_payload_values():
    payload = {
        "dob": "1990-05-14",
        "aadhaar_last4": "4321",
        "pincode": "400001",
        "payment_method": {"card": {"card_number": "4532015112830366", "cvv": "123"}},
    }

    redacted = redact_sensitive(payload)

    assert redacted["dob"] == "[REDACTED]"
    assert redacted["aadhaar_last4"] == "[REDACTED]"
    assert redacted["pincode"] == "[REDACTED]"
    assert redacted["payment_method"]["card"]["card_number"] == "[REDACTED]"
    assert redacted["payment_method"]["card"]["cvv"] == "[REDACTED]"


def test_redaction_preserves_safe_field_labels():
    text = "Thanks. Please provide one verification detail to continue: date of birth, Aadhaar last 4 digits, or pincode."

    redacted = redact_sensitive(text)

    assert "date of birth" in redacted
    assert "Aadhaar" in redacted
    assert "pincode" in redacted
    assert "[REDACTED_DOB]" not in redacted
    assert "[REDACTED_AADHAAR]" not in redacted
    assert "[REDACTED_PINCODE]" not in redacted


def test_redaction_scrubs_sensitive_values_but_keeps_labels():
    text = "DOB is 1990-05-14, Aadhaar last 4 is 4321, pincode is 400001, card number 4532015112830366, CVV 123"

    redacted = redact_sensitive(text)

    assert "DOB is" in redacted
    assert "Aadhaar last 4 is" in redacted
    assert "pincode is" in redacted
    assert "card number" in redacted
    assert "CVV" in redacted
    assert "1990-05-14" not in redacted
    assert "4321" not in redacted
    assert "400001" not in redacted
    assert "4532015112830366" not in redacted
    assert "123" not in redacted


def test_verification_prompt_has_safe_labels_without_redaction_placeholders(agent_factory):
    agent = agent_factory()
    messages = [
        agent.next("Hi")["message"],
        agent.next("ACC1001")["message"],
    ]
    response = agent.next("Nithin Jain")["message"]
    messages.append(response)

    assert "date of birth" in response
    assert "Aadhaar" in response
    assert "pincode" in response
    assert "[REDACTED_DOB]" not in response
    assert "[REDACTED_AADHAAR]" not in response
    assert "[REDACTED_PINCODE]" not in response
    assert "1990-05-14" not in "\n".join(messages)
    assert "4321" not in "\n".join(messages)
    assert "400001" not in "\n".join(messages)


def test_logs_never_contain_sensitive_data(caplog):
    logger = logging.getLogger("paygent.test.redaction")
    caplog.set_level(logging.INFO, logger="paygent.test.redaction")

    safe_log(
        logger,
        logging.INFO,
        "payment payload",
        dob="1990-05-14",
        aadhaar_last4="4321",
        pincode="400001",
        card_number="4532015112830366",
        cvv="123",
    )

    rendered = "\n".join(record.getMessage() + str(getattr(record, "paygent_fields", "")) for record in caplog.records)
    assert "1990-05-14" not in rendered
    assert "4321" not in rendered
    assert "400001" not in rendered
    assert "4532015112830366" not in rendered
    assert "123" not in rendered


def test_card_number_and_cvv_cleared_after_payment_attempt(agent_factory, valid_card_text):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")
    agent.next("pay 500")
    agent.next(valid_card_text)

    assert agent._core.state.payment.card_number is None
    assert agent._core.state.payment.cvv is None


def test_no_continuation_after_success(agent_factory, fake_api_client, valid_card_text):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")
    agent.next("pay 500")
    agent.next(valid_card_text)
    after = agent.next(valid_card_text)["message"]

    assert "closed" in after.lower()
    assert "new account flow" in after
    assert "txn_test_success" not in after
    assert len(fake_api_client.payment_calls) == 1
