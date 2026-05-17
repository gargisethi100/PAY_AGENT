from paygent.stages import Stage


def prepare_payment(agent):
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")
    agent.next("pay 500")


def test_invalid_card_api_error_asks_for_card_number(agent_factory, fake_api_client, valid_card_text):
    fake_api_client.payment_error_queue = ["invalid_card"]
    agent = agent_factory()
    prepare_payment(agent)

    response = agent.next(valid_card_text)["message"]

    assert "card number" in response


def test_invalid_cvv_api_error_asks_for_cvv(agent_factory, fake_api_client, valid_card_text):
    fake_api_client.payment_error_queue = ["invalid_cvv"]
    agent = agent_factory()
    prepare_payment(agent)

    response = agent.next(valid_card_text)["message"]

    assert "CVV" in response


def test_invalid_expiry_api_error_asks_for_expiry(agent_factory, fake_api_client, valid_card_text):
    fake_api_client.payment_error_queue = ["invalid_expiry"]
    agent = agent_factory()
    prepare_payment(agent)

    response = agent.next(valid_card_text)["message"]

    assert "expiry" in response


def test_insufficient_balance_api_error_asks_for_lower_amount(agent_factory, fake_api_client, valid_card_text):
    fake_api_client.payment_error_queue = ["insufficient_balance"]
    agent = agent_factory()
    prepare_payment(agent)

    response = agent.next(valid_card_text)["message"]

    assert "lower amount" in response
    assert agent._core.state.stage == Stage.AWAIT_PAYMENT_AMOUNT


def test_invalid_amount_api_error_asks_for_corrected_amount(agent_factory, fake_api_client, valid_card_text):
    fake_api_client.payment_error_queue = ["invalid_amount"]
    agent = agent_factory()
    prepare_payment(agent)

    response = agent.next(valid_card_text)["message"]

    assert "corrected amount" in response
    assert agent._core.state.stage == Stage.AWAIT_PAYMENT_AMOUNT


def test_three_payment_failures_close_cleanly(agent_factory, fake_api_client, valid_card_text):
    fake_api_client.payment_error_queue = ["invalid_card", "invalid_card", "invalid_card"]
    agent = agent_factory()
    prepare_payment(agent)

    first = agent.next(valid_card_text)["message"]
    second = agent.next(valid_card_text)["message"]
    third = agent.next(valid_card_text)["message"]

    assert "card number" in first
    assert "card number" in second
    assert "multiple attempts" in third
    assert agent._core.state.stage == Stage.PAYMENT_FAILED_CLOSE
