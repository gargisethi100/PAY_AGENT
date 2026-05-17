from paygent.agent_core import PaymentAgentCore


class Agent:
    def __init__(self, api_client=None, today_provider=None, llm_extractor=None):
        self._core = PaymentAgentCore(
            api_client=api_client,
            today_provider=today_provider,
            llm_extractor=llm_extractor,
        )

    def next(self, user_input: str) -> dict:
        message = self._core.next(user_input if user_input is not None else "")
        return {"message": message}
