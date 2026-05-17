from paygent.stages import Stage


def test_account_not_found_retries_then_closes(agent_factory, fake_api_client):
    agent = agent_factory()
    agent.next("Hi")

    first = agent.next("ACC9999")["message"]
    second = agent.next("ACC9998")["message"]
    third = agent.next("ACC9997")["message"]

    assert "again" in first
    assert "again" in second
    assert "support" in third
    assert agent._core.state.stage == Stage.ACCOUNT_LOOKUP_FAILED_CLOSE
    assert fake_api_client.payment_calls == []


def test_invalid_account_format_does_not_call_lookup(agent_factory, fake_api_client):
    agent = agent_factory()
    agent.next("Hi")

    response = agent.next("1001")["message"]
    assert "valid account ID" in response
    response = agent.next("ABC1001")["message"]
    assert "valid account ID" in response

    assert fake_api_client.lookup_calls == []


def test_account_change_before_verification_resets_state(agent_factory, fake_api_client):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")

    response = agent.next("actually use ACC1004")["message"]

    assert "full name" in response
    assert fake_api_client.lookup_calls == ["ACC1001", "ACC1004"]
    assert agent._core.state.account_id == "ACC1004"
    assert agent._core.state.identity.full_name is None


def test_account_change_intent_without_new_id_resets_unverified_flow(agent_factory, fake_api_client):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("my acc id is acc1002")

    response = agent.next("i want to change my account id")["message"]

    assert "account ID" in response
    assert agent._core.state.stage == Stage.AWAIT_ACCOUNT_ID
    assert agent._core.state.account_id is None
    assert agent._core.state.account is None
    assert fake_api_client.lookup_calls == ["ACC1002"]


def test_account_change_after_verification_starts_fresh_flow(agent_factory, fake_api_client):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")

    response = agent.next("i want to change my account id")["message"]

    assert "account ID" in response
    assert agent._core.state.stage == Stage.AWAIT_ACCOUNT_ID
    assert agent._core.state.account_id is None
    assert agent._core.state.account is None
    assert agent._core.state.verified is False
    assert agent._core.state.balance_shown is False
    assert agent._core.state.payment.amount is None
    assert fake_api_client.lookup_calls == ["ACC1001"]

    next_response = agent.next("ACC1004")["message"]

    assert "full name" in next_response
    assert fake_api_client.lookup_calls == ["ACC1001", "ACC1004"]


def test_account_change_after_verification_with_new_id_switches_immediately(agent_factory, fake_api_client):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")

    response = agent.next("actually use ACC1004")["message"]

    assert "full name" in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.account_id == "ACC1004"
    assert agent._core.state.verified is False
    assert agent._core.state.balance_shown is False
    assert fake_api_client.lookup_calls == ["ACC1001", "ACC1004"]
