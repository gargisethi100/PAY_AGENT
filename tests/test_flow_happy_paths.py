from decimal import Decimal

from paygent.stages import Stage


def test_happy_path_full_payment_transaction_id_shown(agent_factory, fake_api_client, valid_card_text):
    agent = agent_factory()

    messages = [
        agent.next("Hi")["message"],
        agent.next("ACC1001")["message"],
        agent.next("Nithin Jain")["message"],
        agent.next("DOB is 1990-05-14")["message"],
        agent.next("full amount")["message"],
        agent.next(valid_card_text)["message"],
    ]

    assert "txn_test_success" in messages[-1]
    assert fake_api_client.payment_calls[0]["amount"] == 1250.75
    assert agent._core.state.stage == Stage.SUCCESS_CLOSE


def test_happy_path_partial_payment_payload_amount(agent_factory, fake_api_client, valid_card_text):
    agent = agent_factory()

    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("last four of my Aadhaar is 4321")
    agent.next("I want to pay 500")
    agent.next(valid_card_text)

    assert Decimal(str(fake_api_client.payment_calls[0]["amount"])) == Decimal("500.0")


def test_bare_amount_after_verification_moves_to_card_details(agent_factory, fake_api_client):
    agent = agent_factory()

    agent.next("Hi")
    agent.next("ACC1004")
    agent.next("Rahul Mehta")
    agent.next("pincode is 400004")
    response = agent.next("500")["message"]

    assert "cardholder name" in response
    assert agent._core.state.stage == Stage.AWAIT_CARD_DETAILS
    assert agent._core.state.payment.amount == Decimal("500")
    assert fake_api_client.payment_calls == []


def test_zero_balance_does_not_collect_card(agent_factory, fake_api_client):
    agent = agent_factory()

    agent.next("Hi")
    agent.next("ACC1003")
    agent.next("Priya Agarwal")
    response = agent.next("DOB is 1992-08-10")["message"]

    assert "no outstanding balance" in response
    assert agent._core.state.stage == Stage.ZERO_BALANCE_CLOSE
    assert fake_api_client.payment_calls == []


def test_leap_year_dob_acc1004_succeeds(agent_factory):
    agent = agent_factory()

    agent.next("Hi")
    agent.next("ACC1004")
    agent.next("Rahul Mehta")
    response = agent.next("DOB is 1988-02-29")["message"]

    assert "Identity verified" in response


def test_wrong_nearby_leap_year_date_fails(agent_factory):
    agent = agent_factory()

    agent.next("Hi")
    agent.next("ACC1004")
    agent.next("Rahul Mehta")
    response = agent.next("DOB is 1988-02-28")["message"]

    assert "could not verify" in response
    assert agent._core.state.verification_attempts == 1
