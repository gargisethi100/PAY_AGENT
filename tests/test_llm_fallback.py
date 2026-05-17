from paygent.stages import Stage


class FakeLlmExtractor:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def extract(self, *, text, stage, expected_fields):
        self.calls.append(
            {
                "text": text,
                "stage": stage,
                "expected_fields": expected_fields,
            }
        )
        return self.result


class RaisingLlmExtractor:
    def extract(self, *, text, stage, expected_fields):
        raise TimeoutError("llm unavailable")


def test_llm_fallback_extracts_messy_name_when_rule_parser_misses(fake_api_client):
    llm = FakeLlmExtractor({"full_name": "Nithin Jain", "confidence": "high"})
    from agent import Agent

    agent = Agent(api_client=fake_api_client, llm_extractor=llm)
    agent.next("Hi")
    agent.next("ACC1001")

    response = agent.next("folks call me NJ, legal account name Nithin Jain")["message"]

    assert "verification detail" in response
    assert agent._core.state.identity.full_name == "Nithin Jain"
    assert llm.calls[-1]["stage"] == Stage.AWAIT_FULL_NAME
    assert llm.calls[-1]["expected_fields"] == ["full_name"]


def test_invalid_llm_json_is_ignored_and_agent_asks_for_clarification(fake_api_client):
    llm = FakeLlmExtractor("{not valid json")
    from agent import Agent

    agent = Agent(api_client=fake_api_client, llm_extractor=llm)
    agent.next("Hi")
    agent.next("ACC1001")

    response = agent.next("folks call me NJ, legal account name Nithin Jain")["message"]

    assert "full legal name" in response
    assert agent._core.state.identity.full_name is None


def test_low_confidence_llm_output_is_ignored(fake_api_client):
    llm = FakeLlmExtractor({"full_name": "Nithin Jain", "confidence": "low"})
    from agent import Agent

    agent = Agent(api_client=fake_api_client, llm_extractor=llm)
    agent.next("Hi")
    agent.next("ACC1001")

    response = agent.next("folks call me NJ, legal account name Nithin Jain")["message"]

    assert "full legal name" in response
    assert agent._core.state.identity.full_name is None


def test_invalid_llm_dob_is_rejected_without_counting_failed_attempt(agent_factory, fake_api_client):
    llm = FakeLlmExtractor({"dob": "1990-99-99", "confidence": "high"})
    from agent import Agent

    agent = Agent(api_client=fake_api_client, llm_extractor=llm)
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")

    response = agent.next("my birthday is the one on file")["message"]

    assert "date of birth" in response
    assert agent._core.state.identity.dob is None
    assert agent._core.state.verification_attempts == 0
    assert fake_api_client.payment_calls == []


def test_wrong_shaped_llm_card_number_is_rejected_before_api(fake_api_client):
    llm = FakeLlmExtractor(
        {
            "cardholder_name": "Nithin Jain",
            "card_number": "123",
            "cvv": "123",
            "expiry_month": 12,
            "expiry_year": 2027,
            "confidence": "high",
        }
    )
    from agent import Agent

    agent = Agent(api_client=fake_api_client, llm_extractor=llm)
    agent.next("Hi")
    agent.next("ACC1001")
    agent.next("Nithin Jain")
    agent.next("DOB is 1990-05-14")
    agent.next("pay 500")

    response = agent.next("use the card details I gave")["message"]

    assert "card number" in response
    assert agent._core.state.payment.card_number is None
    assert fake_api_client.payment_calls == []


def test_llm_card_fields_before_verification_are_ignored(fake_api_client):
    llm = FakeLlmExtractor(
        {
            "full_name": "Nithin Jain",
            "card_number": "4532015112830366",
            "cvv": "123",
            "expiry_month": 12,
            "expiry_year": 2027,
            "confidence": "high",
        }
    )
    from agent import Agent

    agent = Agent(api_client=fake_api_client, llm_extractor=llm)
    agent.next("Hi")
    agent.next("ACC1001")

    response = agent.next("folks call me NJ, legal account name Nithin Jain, use the card I typed")["message"]

    assert "verification detail" in response
    assert agent._core.state.payment.card_number is None
    assert agent._core.state.payment.cvv is None
    assert fake_api_client.payment_calls == []


def test_unavailable_llm_does_not_break_the_flow(fake_api_client):
    from agent import Agent

    agent = Agent(api_client=fake_api_client, llm_extractor=RaisingLlmExtractor())
    agent.next("Hi")
    agent.next("ACC1001")

    response = agent.next("folks call me NJ, legal account name Nithin Jain")["message"]

    assert "full legal name" in response
    assert agent._core.state.stage == Stage.AWAIT_FULL_NAME
