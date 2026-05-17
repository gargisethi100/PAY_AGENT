from paygent.stages import Stage


def prepare_verified_payment(agent):
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")


def prepare_card_collection(agent):
    prepare_verified_payment(agent)
    agent.next("pay 500")


def test_invalid_dob_prompt_is_specific_and_safe(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1004")
    agent.next("Rahul Mehta")

    response = agent.next("DOB is 1988-02-30")["message"]

    assert "YYYY-MM-DD" in response
    assert "1988-02-30" not in response
    assert agent._core.state.stage == Stage.AWAIT_SECONDARY_FACTOR
    assert agent._core.state.verification_attempts == 0


def test_invalid_aadhaar_and_pincode_prompts_are_specific(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")

    aadhaar_response = agent.next("Aadhaar last 4 is 321")["message"]
    pincode_response = agent.next("pincode is 40001")["message"]

    assert "exactly 4 digits" in aadhaar_response
    assert "exactly 6 digits" in pincode_response
    assert "321" not in aadhaar_response
    assert "40001" not in pincode_response
    assert agent._core.state.verification_attempts == 0


def test_invalid_card_length_and_cvv_prompts_are_specific(agent_factory, fake_api_client):
    agent = agent_factory()
    prepare_card_collection(agent)

    card_response = agent.next(
        "cardholder name Nithin Jain, card number 453201511283036, expires 12/27, CVV 123"
    )["message"]
    cvv_response = agent.next(
        "cardholder name Nithin Jain, card number 4532015112830366, expires 12/27, CVV 1234"
    )["message"]

    assert "16-digit card number" in card_response
    assert "3-digit CVV" in cvv_response
    assert fake_api_client.payment_calls == []


def test_invalid_cardholder_name_prompt_is_specific(agent_factory, fake_api_client):
    agent = agent_factory()
    prepare_card_collection(agent)

    response = agent.next(
        "cardholder name Nithin123, card number 4532015112830366, expires 12/27, CVV 123"
    )["message"]

    assert "letters and spaces only" in response
    assert fake_api_client.payment_calls == []
