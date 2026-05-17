def test_hinglish_name_and_pincode_flow(agent_factory):
    agent = agent_factory()

    messages = [
        agent.next("Hi")["message"],
        agent.next("meri account id acc1001")["message"],
        agent.next("mera naam nithin jain hai")["message"],
        agent.next("mera naam Nithin Jain hai")["message"],
        agent.next("400001 is the pincode")["message"],
    ]

    assert "full legal name" in messages[2]
    assert "verification detail" in messages[3]
    assert "Identity verified" in messages[4]
    assert "1,250.75" in messages[4]
