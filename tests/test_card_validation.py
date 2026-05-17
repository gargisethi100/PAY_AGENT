def verify_and_set_amount(agent):
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")
    agent.next("pay 500")


def test_spaced_card_number_normalized(agent_factory, fake_api_client, valid_card_text):
    agent = agent_factory()
    verify_and_set_amount(agent)

    agent.next(valid_card_text)

    card = fake_api_client.payment_calls[0]["payment_method"]["card"]
    assert card["card_number"] == "4532015112830366"


def test_hyphenated_card_number_normalized(agent_factory, fake_api_client):
    agent = agent_factory()
    verify_and_set_amount(agent)

    agent.next("cardholder name Nithin Jain, card number 4532-0151-1283-0366, expires 12/27, CVV 123")

    card = fake_api_client.payment_calls[0]["payment_method"]["card"]
    assert card["card_number"] == "4532015112830366"


def test_luhn_invalid_card_rejected_before_api(agent_factory, fake_api_client):
    agent = agent_factory()
    verify_and_set_amount(agent)

    response = agent.next("cardholder name Nithin Jain, card number 4532015112830367, expires 12/27, CVV 123")["message"]

    assert "card number" in response
    assert fake_api_client.payment_calls == []


def test_expired_card_rejected_before_api(agent_factory, fake_api_client):
    agent = agent_factory()
    verify_and_set_amount(agent)

    response = agent.next("cardholder name Nithin Jain, card number 4532015112830366, expires 01/20, CVV 123")["message"]

    assert "expiry" in response
    assert fake_api_client.payment_calls == []


def test_invalid_cvv_rejected_before_api(agent_factory, fake_api_client):
    agent = agent_factory()
    verify_and_set_amount(agent)

    response = agent.next("cardholder name Nithin Jain, card number 4532015112830366, expires 12/27, CVV 12")["message"]

    assert "CVV" in response
    assert fake_api_client.payment_calls == []


def test_expiry_12_27_parsed_as_2027(agent_factory, fake_api_client, valid_card_text):
    agent = agent_factory()
    verify_and_set_amount(agent)

    agent.next(valid_card_text)

    card = fake_api_client.payment_calls[0]["payment_method"]["card"]
    assert card["expiry_month"] == 12
    assert card["expiry_year"] == 2027
