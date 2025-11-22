import pytest

from Nichols import main


class DummyAssistant:
    def __init__(self, reply=("resposta curta", ["Fonte Bonita"])):
        self.reply = reply
        self.calls = []

    async def run(self, question: str, session_id: str):
        self.calls.append((question, session_id))
        return self.reply


@pytest.fixture(autouse=True)
def restore_assistant(monkeypatch):
    original = main.assistant
    yield
    main.assistant = original


@pytest.mark.asyncio
async def test_process_message_content_success(monkeypatch):
    dummy = DummyAssistant()
    main.assistant = dummy

    reply = await main.process_message_content("conteúdo teste", session_id="123")

    assert "Fonte Bonita" in reply
    assert dummy.calls[0][1] == "123"


@pytest.mark.asyncio
async def test_process_message_content_failure(monkeypatch):
    class FailingAssistant:
        async def run(self, question: str, session_id: str):
            raise RuntimeError("boom")

    main.assistant = FailingAssistant()

    reply = await main.process_message_content("qualquer coisa", session_id="321")

    assert "pane" in reply
