from paygent.stages import Stage


def test_cancel_during_verification_closes(agent_factory, fake_api_client):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")

    response = agent.next("cancel")["message"]

    assert "cancelled" in response
    assert agent._core.state.stage == Stage.CANCELLED_CLOSE
    assert fake_api_client.payment_calls == []


def test_cancel_during_payment_clears_sensitive_state(agent_factory, fake_api_client):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")
    agent.next("pay 500")
    agent.next("cardholder name Nithin Jain, card number 4532015112830366, CVV 123")

    response = agent.next("I do not want to pay now")["message"]

    assert "cancelled" in response
    assert agent._core.state.stage == Stage.CANCELLED_CLOSE
    assert agent._core.state.payment.card_number is None
    assert agent._core.state.payment.cvv is None
    assert fake_api_client.payment_calls == []


def test_cancel_phrases_supported(agent_factory):
    for phrase in ["cancel", "stop", "exit", "I do not want to continue", "I do not want to pay now"]:
        agent = agent_factory()
        agent.next("Hi")
        response = agent.next(phrase)["message"]
        assert "cancelled" in response
