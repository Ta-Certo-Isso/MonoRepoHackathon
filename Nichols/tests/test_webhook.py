from typing import Any, Dict, Optional

import pytest
from fastapi.testclient import TestClient

from Nichols import main


class DummyEvolutionClient:
    def __init__(self) -> None:
        self.sent_text: Optional[Dict[str, Any]] = None
        self.sent_audio: Optional[Dict[str, Any]] = None

    async def send_text(
        self, number: str, text: str, instance: Optional[str] = None
    ) -> Dict[str, Any]:
        self.sent_text = {"number": number, "text": text, "instance": instance}
        return {"status": 200}

    async def send_audio(
        self, number: str, audio_bytes: bytes, instance: Optional[str] = None
    ) -> Dict[str, Any]:
        self.sent_audio = {
            "number": number,
            "audio_bytes": audio_bytes,
            "instance": instance,
        }
        return {"status": 200}

    async def fetch_media(self, url: str) -> bytes:
        return b"audio-bytes"


class DummyTTS:
    def __init__(self) -> None:
        self.transcribed: Optional[str] = None
        self.synth_calls: int = 0

    async def synthesize(self, text: str) -> bytes:
        self.synth_calls += 1
        return b"tts-bytes"

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.ogg") -> str:
        self.transcribed = audio_bytes.decode("utf-8", errors="ignore") or "transcribed"
        return self.transcribed


@pytest.fixture(autouse=True)
def restore_clients(monkeypatch):
    original_evo = main.evolution_client
    original_tts = main.tts_client
    original_process = main.process_message_content
    yield
    main.evolution_client = original_evo
    main.tts_client = original_tts
    main.process_message_content = original_process


def test_api_ask(monkeypatch):
    async def fake_process(question: str, session_id: str) -> str:
        return f"reply:{question}:{session_id}"

    main.process_message_content = fake_process  # type: ignore[assignment]

    client = TestClient(main.app)
    resp = client.post("/api/ask", json={"question": "oi", "session_id": "abc"})
    assert resp.status_code == 200
    assert resp.json()["answer"] == "reply:oi:abc"


def test_webhook_text_flow(monkeypatch):
    evo = DummyEvolutionClient()
    tts = DummyTTS()

    async def fake_process(question: str, session_id: str) -> str:
        return "resposta texto"

    main.evolution_client = evo
    main.tts_client = tts
    main.process_message_content = fake_process  # type: ignore[assignment]

    payload = {
        "data": {
            "messages": [
                {
                    "key": {"remoteJid": "5511999999999@s.whatsapp.net"},
                    "message": {"conversation": "Pergunta teste"},
                }
            ]
        }
    }

    client = TestClient(main.app)
    resp = client.post("/webhook/evolution", json=payload)

    assert resp.status_code == 200
    assert evo.sent_text == {
        "number": "5511999999999",
        "text": "resposta texto",
        "instance": None,
    }
    assert evo.sent_audio is None  # não deve enviar áudio quando entrada é texto
    assert tts.synth_calls == 0


def test_webhook_audio_flow(monkeypatch):
    evo = DummyEvolutionClient()
    tts = DummyTTS()

    async def fake_process(question: str, session_id: str) -> str:
        return "resposta audio"

    main.evolution_client = evo
    main.tts_client = tts
    main.process_message_content = fake_process  # type: ignore[assignment]

    payload = {
        "data": {
            "messages": [
                {
                    "key": {"remoteJid": "5511888888888@s.whatsapp.net"},
                    "message": {"audioMessage": {"url": "http://fake/audio.ogg"}},
                }
            ]
        }
    }

    client = TestClient(main.app)
    resp = client.post("/webhook/evolution", json=payload)

    assert resp.status_code == 200
    assert evo.sent_text is not None
    assert evo.sent_audio is not None
    assert evo.sent_audio["number"] == "5511888888888"
    assert tts.synth_calls == 1


def test_webhook_greeting_intro(monkeypatch):
    evo = DummyEvolutionClient()
    tts = DummyTTS()

    main.evolution_client = evo
    main.tts_client = tts

    payload = {
        "data": {
            "messages": [
                {
                    "key": {"remoteJid": "5511777777777@s.whatsapp.net"},
                    "message": {"conversation": "oi"},
                }
            ]
        }
    }

    client = TestClient(main.app)
    resp = client.post("/webhook/evolution", json=payload)

    assert resp.status_code == 200
    assert evo.sent_text is not None
    assert evo.sent_audio is None
    assert "oi" in resp.json()["echo"].lower()
