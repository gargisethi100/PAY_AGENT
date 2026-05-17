from decimal import Decimal

from paygent.stages import Stage


def verify_zero_balance(agent):
    agent.next("Hi")
    agent.next("ACC1003")
    agent.next("Priya Agarwal")
    return agent.next("DOB is 1992-08-10")["message"]


def complete_successful_payment(agent, valid_card_text):
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")
    agent.next("full amount")
    return agent.next(valid_card_text)["message"]


def test_zero_balance_terminal_acknowledgement_does_not_repeat_zero_balance(agent_factory):
    agent = agent_factory()
    zero_balance_message = verify_zero_balance(agent)

    response = agent.next("cool thanks")["message"]

    assert "You're welcome" in response
    assert response != zero_balance_message
    assert "no outstanding balance" in response
    assert agent._core.state.stage == Stage.ZERO_BALANCE_CLOSE
    assert agent._core.state.last_diagnostics["terminal_followup_detected"] is True


def test_zero_balance_terminal_change_account_without_id_starts_fresh_flow(agent_factory):
    agent = agent_factory()
    verify_zero_balance(agent)

    response = agent.next("i want to change my account id")["message"]

    assert "new account ID" in response
    assert agent._core.state.stage == Stage.AWAIT_ACCOUNT_ID
    assert agent._core.state.account_id is None
    assert agent._core.state.account is None
    assert agent._core.state.verified is False
    assert agent._core.state.balance_shown is False
    assert agent._core.state.payment.amount is None
    assert agent._core.state.terminal_message is None
    assert agent._core.state.last_diagnostics["terminal_account_switch_requested"] is True


def test_zero_balance_terminal_new_account_id_switches_immediately(agent_factory, fake_api_client):
    agent = agent_factory()
    verify_zero_balance(agent)

    response = agent.next("my account id is acc1001")["message"]

    assert "full name" in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.account_id == "ACC1001"
    assert agent._core.state.verified is False
    assert agent._core.state.terminal_message is None
    assert fake_api_client.lookup_calls == ["ACC1003", "ACC1001"]


def test_success_terminal_change_account_with_id_starts_fresh_lookup(
    agent_factory,
    fake_api_client,
    valid_card_text,
):
    agent = agent_factory()
    complete_successful_payment(agent, valid_card_text)

    response = agent.next("change account id to acc1003")["message"]

    assert "full name" in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.account_id == "ACC1003"
    assert agent._core.state.verified is False
    assert agent._core.state.balance_shown is False
    assert agent._core.state.payment.amount is None
    assert agent._core.state.payment.card_number is None
    assert agent._core.state.payment.cvv is None
    assert agent._core.state.transaction_id is None
    assert agent._core.state.terminal_message is None
    assert fake_api_client.lookup_calls == ["ACC1001", "ACC1003"]


def test_unrelated_terminal_input_returns_generic_closed_flow_message_without_raw_card(agent_factory):
    agent = agent_factory()
    verify_zero_balance(agent)

    response = agent.next("card number 4532015112830366 cvv 123")["message"]

    assert "closed" in response.lower()
    assert "new account flow" in response
    assert "4532015112830366" not in response
    assert "123" not in response
    assert agent._core.state.stage == Stage.ZERO_BALANCE_CLOSE


def test_terminal_reset_clears_prior_payment_amount_and_diagnostics(agent_factory, valid_card_text):
    agent = agent_factory()
    complete_successful_payment(agent, valid_card_text)

    assert agent._core.state.stage == Stage.SUCCESS_CLOSE

    agent.next("new account acc1003")

    assert agent._core.state.payment.amount is None
    assert agent._core.state.pending_payment_amount is None
    assert agent._core.state.payment_attempts == 0
    assert agent._core.state.local_payment_validation_failures == {}
    assert agent._core.state.last_diagnostics["terminal_account_switch_requested"] is True
    assert Decimal(str(agent._core.state.account.balance)) == Decimal("0.00")
