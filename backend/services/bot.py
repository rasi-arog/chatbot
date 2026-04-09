def simple_bot(msg: str) -> str:
    if "fever" in msg.lower():
        return "You may have viral fever. Stay hydrated."
    return "Please provide more details."
