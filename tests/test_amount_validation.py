from decimal import Decimal


def verify_acc1001(agent):
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")


def test_zero_amount_rejected_before_api(agent_factory, fake_api_client):
    agent = agent_factory()
    verify_acc1001(agent)

    response = agent.next("pay 0")["message"]

    assert "greater than zero" in response
    assert fake_api_client.payment_calls == []


def test_negative_amount_rejected_before_api(agent_factory, fake_api_client):
    agent = agent_factory()
    verify_acc1001(agent)

    response = agent.next("pay -10")["message"]

    assert "greater than zero" in response
    assert fake_api_client.payment_calls == []


def test_amount_more_than_two_decimals_rejected_before_api(agent_factory, fake_api_client):
    agent = agent_factory()
    verify_acc1001(agent)

    response = agent.next("pay 10.123")["message"]

    assert "2 decimal" in response
    assert fake_api_client.payment_calls == []


def test_amount_greater_than_balance_rejected_before_api(agent_factory, fake_api_client):
    agent = agent_factory()
    verify_acc1001(agent)

    response = agent.next("pay 1250.76")["message"]

    assert "lower amount" in response
    assert fake_api_client.payment_calls == []


def test_full_amount_resolves_to_balance(agent_factory, fake_api_client, valid_card_text):
    agent = agent_factory()
    verify_acc1001(agent)

    agent.next("just clear the full amount")
    agent.next(valid_card_text)

    assert Decimal(str(fake_api_client.payment_calls[0]["amount"])) == Decimal("1250.75")
