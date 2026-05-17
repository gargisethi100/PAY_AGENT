from paygent.stages import Stage


def test_out_of_order_fields_stored_but_required_prompts_preserved(agent_factory):
    agent = agent_factory()

    first = agent.next(
        "Hi, account id ACC1001, my name is Nithin Jain, DOB is 1990-05-14, I want to pay 500"
    )["message"]
    second = agent.next("okay")["message"]

    assert "account ID" in first
    assert "full name" in second
    assert agent._core.state.payment.amount is not None
    assert not agent._core.state.verified
    assert "1,250.75" not in first
    assert "1,250.75" not in second


def test_no_balance_before_verification(agent_factory):
    agent = agent_factory()

    messages = [
        agent.next("Hi")["message"],
        agent.next("ACC1001")["message"],
        agent.next("Nithin Jain")["message"],
    ]

    assert all("1,250.75" not in message for message in messages)


def test_no_payment_before_verification(agent_factory, fake_api_client):
    agent = agent_factory()

    agent.next("Hi")
    agent.next("ACC1001")
    response = agent.next(
        "pay 500 card number 4532015112830366 expires 12/27 CVV 123"
    )["message"]

    assert "full legal name" in response
    assert fake_api_client.payment_calls == []


def test_early_card_details_before_verification_not_stored_or_processed(agent_factory, fake_api_client):
    agent = agent_factory()

    agent.next("Hi")
    agent.next("ACC1001")
    response = agent.next(
        "cardholder name Nithin Jain card number 4532015112830366 expires 12/27 CVV 123"
    )["message"]

    assert "full legal name" in response
    assert fake_api_client.payment_calls == []
    assert agent._core.state.payment.card_number is None
    assert agent._core.state.payment.cvv is None
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
