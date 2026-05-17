from agent import Agent


def test_next_returns_exact_message_dict(agent_factory):
    agent = agent_factory()
    response = agent.next("Hi")

    assert list(response.keys()) == ["message"]
    assert isinstance(response["message"], str)


def test_state_persists_across_turns(agent_factory):
    agent = agent_factory()

    first = agent.next("Hi")["message"]
    second = agent.next("My account ID is ACC1001")["message"]

    assert "account ID" in first
    assert "full name" in second


def test_independent_agent_instances(fake_api_client, noop_llm_extractor):
    agent_a = Agent(api_client=fake_api_client, llm_extractor=noop_llm_extractor)
    agent_b = Agent(api_client=fake_api_client, llm_extractor=noop_llm_extractor)

    agent_a.next("Hi")
    agent_a.next("ACC1001")
    response_b = agent_b.next("Hi")["message"]

    assert "account ID" in response_b


def test_closed_conversation_does_not_continue_flow(agent_factory):
    agent = agent_factory()
    agent.next("Hi")
    agent._core.state.stage = "CANCELLED_CLOSE"
    agent._core.state.terminal_message = "Closed."

    response = agent.next("card number 4532015112830366 cvv 123")["message"]

    assert "closed" in response.lower()
    assert "new account flow" in response
    assert "4532015112830366" not in response
    assert "123" not in response
