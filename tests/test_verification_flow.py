from paygent.stages import Stage


def test_partial_verification_inputs_do_not_count_failed_attempts(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")

    agent.next("DOB is 1990-05-14")
    assert agent._core.state.verification_attempts == 0

    agent.next("Nithin Jain")
    assert agent._core.state.verification_attempts == 0

    response = agent.next("DOB is 1990-01-01")["message"]
    assert "could not verify" in response
    assert agent._core.state.verification_attempts == 1


def test_agent_strict_name_lowercase_fails_then_exact_passes(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")
    response = agent.next("nithin jain")["message"]

    assert "full legal name" in response
    assert "change account ID" in response
    assert "date of birth" not in response
    assert "Aadhaar" not in response
    assert "pincode" not in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.verification_attempts == 0

    agent.next("Nithin Jain")
    response = agent.next("DOB is 1990-05-14")["message"]

    assert "Identity verified" in response


def test_acc1004_lowercase_name_with_correct_pincode_fails_then_exact_succeeds(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1004")
    response = agent.next("rahul mehta")["message"]

    assert "full legal name" in response
    assert "change account ID" in response
    assert "date of birth" not in response
    assert "Aadhaar" not in response
    assert "pincode" not in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.verification_attempts == 0

    response = agent.next("pincode is 400004")["message"]

    assert "full legal name" in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.verification_attempts == 0

    agent.next("Rahul Mehta")
    response = agent.next("pincode is 400004")["message"]

    assert "Identity verified" in response


def test_agent_extracts_conversational_repeated_name(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("yeah my account number is ACC1001 I think")

    response = agent.next('"it\'s Nithin, Nithin Jain"')["message"]

    assert "verification detail" in response
    assert "full name" not in response
    assert agent._core.state.identity.full_name == "Nithin Jain"


def test_agent_rejects_alias_only_name(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1001")

    response = agent.next("you can call me Raja")["message"]

    assert "full legal name" in response
    assert "verification detail" not in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.identity.full_name is None


def test_agent_rejects_single_token_conversational_name(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1003")

    response = agent.next("hey my name is gargi")["message"]

    assert "full legal name" in response
    assert "verification detail" not in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.identity.full_name is None


def test_agent_accepts_full_name_with_greeting(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1003")

    response = agent.next("hey my name is Priya Agarwal")["message"]

    assert "verification detail" in response
    assert agent._core.state.stage == Stage.AWAIT_SECONDARY_FACTOR
    assert agent._core.state.identity.full_name == "Priya Agarwal"


def test_agent_accepts_i_am_full_name_phrase(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1003")

    response = agent.next("i am Priya Agarwal")["message"]

    assert "verification detail" in response
    assert agent._core.state.stage == Stage.AWAIT_SECONDARY_FACTOR
    assert agent._core.state.identity.full_name == "Priya Agarwal"
    assert agent._core.state.last_diagnostics["full_name_detected"] is True
    assert agent._core.state.last_diagnostics["full_name_exact_match"] is True


def test_agent_accepts_common_self_intro_full_name_phrases(agent_factory):
    for phrase in ["I'm Priya Agarwal", "this is Priya Agarwal", "myself Priya Agarwal"]:
        agent = agent_factory()
        agent.next("Hi")
        agent.next("ACC1003")

        response = agent.next(phrase)["message"]

        assert "verification detail" in response
        assert agent._core.state.identity.full_name == "Priya Agarwal"


def test_agent_accepts_long_full_name_with_alias_phrase(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1002")

    response = agent.next(
        "you can call me Raja but my full name is Rajarajeswari Balasubramaniam"
    )["message"]

    assert "verification detail" in response
    assert agent._core.state.stage == Stage.AWAIT_SECONDARY_FACTOR
    assert agent._core.state.identity.full_name == "Rajarajeswari Balasubramaniam"


def test_wrong_name_is_rejected_before_secondary_prompt(agent_factory, fake_api_client):
    agent = agent_factory()
    messages = [
        agent.next("Hi")["message"],
        agent.next("ACC1004")["message"],
        agent.next("aditya sethi")["message"],
    ]

    assert "could not be verified for this account" in messages[-1]
    assert "change account ID" in messages[-1]
    assert "date of birth" not in messages[-1]
    assert "Aadhaar" not in messages[-1]
    assert "pincode" not in messages[-1]
    assert "Rahul Mehta" not in messages[-1]
    assert agent._core.state.verification_attempts == 0
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert all("3,200.50" not in message for message in messages)
    assert fake_api_client.payment_calls == []


def test_wrong_case_name_gets_mismatch_guidance_without_retry(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1003")

    response = agent.next("my name is Priya agarwal")["message"]

    assert "could not be verified for this account" in response
    assert "change account ID" in response
    assert "Priya Agarwal" not in response
    assert agent._core.state.verification_attempts == 0
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.last_diagnostics["full_name_detected"] is True
    assert agent._core.state.last_diagnostics["full_name_exact_match"] is False
    assert agent._core.state.last_diagnostics["name_mismatch"] is True


def test_secondary_only_after_rejected_name_does_not_increment_retry(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent.next("ACC1004")
    agent.next("aditya sethi")

    response = agent.next("Aadhaar last 4 is 1357")["message"]

    assert "full legal name" in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
    assert agent._core.state.verification_attempts == 0


def test_verification_failure_limit_closes_without_balance_or_payment(agent_factory, fake_api_client):
    agent = agent_factory()
    messages = []
    messages.append(agent.next("Hi")["message"])
    messages.append(agent.next("ACC1001")["message"])

    for _ in range(3):
        messages.append(agent.next("Nithin Jain")["message"])
        messages.append(agent.next("DOB is 1990-01-01")["message"])

    assert agent._core.state.stage == Stage.VERIFICATION_FAILED_CLOSE
    assert all("1,250.75" not in message for message in messages)
    assert fake_api_client.payment_calls == []
