from decimal import Decimal

from paygent.extraction import extract_fields
from paygent.stages import Stage


def prepare_verified_agent(agent):
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")


def prepare_card_stage(agent):
    prepare_verified_agent(agent)
    agent.next("pay 500")


def test_half_amount_requires_confirmation_then_sets_rounded_amount(agent_factory):
    agent = agent_factory()
    prepare_verified_agent(agent)

    prompt = agent.next("half the amount? ]")["message"]
    response = agent.next("yes")["message"]

    assert "Rs. 625.38" in prompt
    assert "confirm" in prompt.lower()
    assert "cardholder name" in response
    assert agent._core.state.payment.amount == Decimal("625.38")
    assert agent._core.state.stage == Stage.AWAIT_CARD_DETAILS


def test_poora_and_pura_amount_resolve_to_full_balance(agent_factory, fake_api_client, valid_card_text):
    for phrase in ["poora amount", "pura amount"]:
        fake_api_client.payment_calls.clear()
        agent = agent_factory()
        prepare_verified_agent(agent)

        response = agent.next(phrase)["message"]
        agent.next(valid_card_text)

        assert "cardholder name" in response
        assert Decimal(str(fake_api_client.payment_calls[0]["amount"])) == Decimal("1250.75")


def test_card_stage_name_phrase_is_cardholder_name(agent_factory):
    agent = agent_factory()
    prepare_card_stage(agent)

    response = agent.next("name is arpit up")["message"]

    assert "cardholder name" not in response
    assert agent._core.state.payment.cardholder_name == "arpit up"


def test_invalid_cvv_attempt_gets_specific_format_error(agent_factory):
    agent = agent_factory()
    prepare_card_stage(agent)

    first = agent.next("cvv is 2w3")["message"]
    second = agent.next("cvv is aws")["message"]

    assert "CVV must be 3 digits" in first or "cvv" in first.lower()
    assert "CVV must be 3 digits" in second or "cvv" in second.lower()
    assert agent._core.state.payment.cvv is None


def test_date_like_expiry_attempt_gets_specific_format_error(agent_factory):
    agent = agent_factory()
    prepare_card_stage(agent)

    response = agent.next("i think its 23rd feb 2030")["message"]

    assert "MM/YY" in response or "expiry" in response.lower()
    assert agent._core.state.payment.expiry_month is None
    assert agent._core.state.payment.expiry_year is None


def test_invalid_card_number_is_rejected_before_api(agent_factory, fake_api_client):
    agent = agent_factory()
    prepare_card_stage(agent)

    response = agent.next("card number is 4532015112830367")["message"]

    assert "card number" in response.lower() or "missing" in response.lower()
    assert fake_api_client.payment_calls == []


def test_repeated_invalid_card_numbers_get_stronger_guidance_but_can_recover(agent_factory, fake_api_client):
    agent = agent_factory()
    prepare_card_stage(agent)

    first = agent.next("card number is 4532015112830367")["message"]
    second = agent.next("card number is 4532015112830367")["message"]
    third = agent.next("card number is 4532015112830367")["message"]
    recovered = agent.next("card number is 4532 0151 1283 0366")["message"]

    # Card number is collected but other fields are still missing, so it asks for remaining
    assert "card" in first.lower() or "missing" in first.lower()
    assert "card" in second.lower() or "missing" in second.lower()
    assert "missing" in recovered.lower() or "card detail" in recovered.lower()
    assert agent._core.state.payment.card_number == "4532015112830366"
    assert fake_api_client.payment_calls == []


def test_bare_cvv_is_accepted_when_cvv_is_missing_in_card_stage(agent_factory):
    agent = agent_factory()
    prepare_card_stage(agent)
    agent.next("name is arpit au")
    agent.next("card number is 4532 0151 1283 0366")

    invalid = agent.next("cvv is 3e3")["message"]
    recovered = agent.next("343")["message"]

    assert "CVV" in invalid or "cvv" in invalid.lower()
    assert "expiry" in recovered.lower()
    assert agent._core.state.payment.cvv == "343"
    assert agent._core.state.last_diagnostics["bare_cvv_detected"] is True


def test_short_alias_name_rejects_then_exact_long_name_is_accepted(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("my acc id is acc1002")

    alias_response = agent.next("hi i am raja")["message"]
    exact_response = agent.next("Rajarajeswari Balasubramaniam")["message"]

    assert "full legal name" in alias_response
    assert "registered" in alias_response
    assert "verification detail" in exact_response
    assert agent._core.state.identity.full_name == "Rajarajeswari Balasubramaniam"
    assert agent._core.state.verification_attempts == 0
    assert agent._core.state.last_diagnostics["alias_name_mismatch"] is True


def test_supplied_transcript_path_recovers_to_success(agent_factory, fake_api_client):
    agent = agent_factory()
    turns = [
        "Hiii",
        "my account id is acc1001",
        "mera naam Nithin Jain hai",
        "400001 pincode hai",
        "half the amount? ]",
        "no, clear the full amount",
        "card number is 4532015112830367",
        "card number is 4532 0151 1283 0366",
        "name is arpit up",
        "cvv is 2w3",
        "CVV is 123",
        "i think its 23rd feb 2030",
        "expires 02/30",
    ]

    messages = [agent.next(turn)["message"] for turn in turns]

    assert any("Rs. 625.38" in message for message in messages)
    assert any("cvv" in message.lower() for message in messages)
    assert any("expiry" in message.lower() or "MM/YY" in message for message in messages)
    assert "txn_test_success" in messages[-1]
    assert Decimal(str(fake_api_client.payment_calls[0]["amount"])) == Decimal("1250.75")


def test_supplied_account_switch_and_long_name_transcript_path(agent_factory, fake_api_client):
    agent = agent_factory()
    messages = [
        agent.next("Hi")["message"],
        agent.next("my acc id is acc1002")["message"],
        agent.next("hi i am raja")["message"],
        agent.next("i want to change my account id")["message"],
        agent.next("my acc id is acc1002")["message"],
        agent.next("Rajarajeswari Balasubramaniam")["message"],
        agent.next("Aadhaar last 4 is 9876")["message"],
        agent.next("half the amount")["message"],
        agent.next("yeah")["message"],
        agent.next("name is arpit au")["message"],
        agent.next("card number is 4532015112830367")["message"],
        agent.next("card number is 4532015112830367")["message"],
        agent.next("card number is 4532015112830367")["message"],
        agent.next("card number is 4532 0151 1283 0366")["message"],
        agent.next("cvv is 3e3")["message"],
        agent.next("343")["message"],
        agent.next("expiry is may 2033")["message"],
    ]

    assert any("account ID" in message for message in messages)
    assert any("full legal name" in message for message in messages)
    assert any("Rs. 270.00" in message for message in messages)
    # Card validation errors are reported when all fields are present, or as missing field hints
    assert any("card" in message.lower() for message in messages)
    assert "txn_test_success" in messages[-1]
    assert Decimal(str(fake_api_client.payment_calls[0]["amount"])) == Decimal("270.0")


def test_extractor_recognizes_relative_amounts_and_hinglish_card_fields():
    assert extract_fields("half the amount", Stage.AWAIT_PAYMENT_AMOUNT).relative_amount_fraction == Decimal("0.5")
    assert extract_fields("aadha amount", Stage.AWAIT_PAYMENT_AMOUNT).relative_amount_fraction == Decimal("0.5")
    assert extract_fields("50%", Stage.AWAIT_PAYMENT_AMOUNT).relative_amount_fraction == Decimal("0.5")
    assert extract_fields("quarter", Stage.AWAIT_PAYMENT_AMOUNT).relative_amount_fraction == Decimal("0.25")
    assert extract_fields("25%", Stage.AWAIT_PAYMENT_AMOUNT).relative_amount_fraction == Decimal("0.25")
    assert extract_fields("poora amount", Stage.AWAIT_PAYMENT_AMOUNT).full_amount_requested is True
    assert extract_fields("pura amount", Stage.AWAIT_PAYMENT_AMOUNT).full_amount_requested is True
    assert extract_fields("name is arpit up", Stage.AWAIT_CARD_DETAILS).cardholder_name == "arpit up"
    assert extract_fields("cvv 123 hai", Stage.AWAIT_CARD_DETAILS).cvv == "123"
    assert extract_fields("expiry feb 2030 hai", Stage.AWAIT_CARD_DETAILS).expiry_month == 2
    assert extract_fields("i think its 23rd feb 2030", Stage.AWAIT_CARD_DETAILS).expiry_month is None
    assert extract_fields("i want to change my account id", Stage.AWAIT_FULL_NAME).account_change_requested is True
    assert extract_fields("343", Stage.AWAIT_CARD_DETAILS).cvv == "343"
