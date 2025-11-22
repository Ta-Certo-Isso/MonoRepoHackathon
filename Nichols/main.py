import asyncio
import base64
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from langchain_community.chat_message_histories.sql import SQLChatMessageHistory
from langchain_community.vectorstores import Chroma
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel, SecretStr


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("nichols")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


@dataclass
class Settings:
    openai_api_key: str = _env("OPENAI_API_KEY", "") or ""
    openai_model: str = _env("OPENAI_MODEL", "gpt-4o-mini") or ""
    openai_tts_model: str = _env("OPENAI_TTS_MODEL", "tts-1") or ""
    openai_tts_voice: str = _env("OPENAI_TTS_VOICE", "alloy") or ""
    openai_embeddings_model: str = (
        _env("OPENAI_EMBEDDINGS_MODEL", "text-embedding-3-small") or ""
    )
    evolution_base_url: str = _env("EVOLUTION_BASE_URL", "") or ""
    evolution_api_key: str = _env("EVOLUTION_API_KEY", "") or ""
    evolution_instance: str = _env("EVOLUTION_INSTANCE", "") or ""
    webhook_token: Optional[str] = _env("WEBHOOK_TOKEN")
    data_dir: str = _env("DATA_DIR", "data") or ""
    history_db: str = _env("HISTORY_DB", "data/history.db") or ""

    def validate(self) -> None:
        missing = [
            ("OPENAI_API_KEY", self.openai_api_key),
            ("EVOLUTION_BASE_URL", self.evolution_base_url),
            ("EVOLUTION_API_KEY", self.evolution_api_key),
            ("EVOLUTION_INSTANCE", self.evolution_instance),
        ]
        missing_keys = [name for name, value in missing if not value]
        if missing_keys:
            joined = ", ".join(missing_keys)
            raise RuntimeError(f"Missing required environment variables: {joined}")


settings = Settings()
settings.validate()  # valida cedo para evitar clientes com chaves vazias


class OpenAITTSClient:
    def __init__(self, api_key: str, model: str, voice: str) -> None:
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self._client = httpx.AsyncClient(timeout=30.0)

    async def synthesize(self, text: str) -> bytes:
        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "voice": self.voice,
            "input": text,
        }
        response = await self._client.post(url, json=payload, headers=headers)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAI TTS error: %s | %s", exc, response.text)
            raise
        return response.content

    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.ogg") -> str:
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        files: Dict[str, tuple[Optional[str], bytes | str, Optional[str]]] = {
            "file": (filename, audio_bytes, "application/octet-stream"),
            "model": (None, "whisper-1", None),
            "language": (None, "pt", None),
        }
        response = await self._client.post(url, headers=headers, files=files)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("OpenAI STT error: %s | %s", exc, response.text)
            raise
        data = response.json()
        return data.get("text", "")

    async def aclose(self) -> None:
        await self._client.aclose()


class EvolutionAPIClient:
    def __init__(self, base_url: str, api_key: str, default_instance: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_instance = default_instance
        self._client = httpx.AsyncClient(timeout=30.0)

    def _headers(self) -> Dict[str, str]:
        return {
            "apikey": self.api_key,
            "Content-Type": "application/json",
        }

    def _instance_path(self, instance: Optional[str]) -> str:
        return instance or self.default_instance

    async def send_text(
        self, number: str, text: str, instance: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/message/sendText/{self._instance_path(instance)}"
        payload = {"number": number, "text": text}
        response = await self._client.post(url, json=payload, headers=self._headers())
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error("Evolution sendText error: %s | %s", exc, response.text)
            raise
        return response.json()

    async def send_audio(
        self, number: str, audio_bytes: bytes, instance: Optional[str] = None
    ) -> Dict[str, Any]:
        url = (
            f"{self.base_url}/message/sendWhatsAppAudio/{self._instance_path(instance)}"
        )
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        payload = {"number": number, "audio": audio_b64}
        response = await self._client.post(url, json=payload, headers=self._headers())
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Evolution sendWhatsAppAudio error: %s | %s", exc, response.text
            )
            raise
        return response.json()

    async def fetch_media(self, url: str) -> bytes:
        response = await self._client.get(url, headers=self._headers())
        response.raise_for_status()
        return response.content

    async def aclose(self) -> None:
        await self._client.aclose()


def load_corpus(data_dir: Path) -> List[Tuple[str, str, str]]:
    """Return list of (doc_id, title, text) from .txt files (primeira linha como título)."""
    docs: List[Tuple[str, str, str]] = []
    if not data_dir.exists():
        return docs
    for path in data_dir.glob("*.txt"):
        try:
            raw = path.read_text(encoding="utf-8")
            lines = raw.splitlines()
            title = lines[0].strip() if lines else path.stem
            text = "\n".join(lines[1:]).strip() if len(lines) > 1 else raw
            docs.append((path.stem, title, text))
        except Exception as exc:  # pragma: no cover - log + continue
            logger.warning("Failed to read %s: %s", path, exc)
    return docs


class RetrievedContext(NamedTuple):
    text: str
    sources: List[str]


SYSTEM_PROMPT = """
Você é um assistente cívico. Regras fixas:
- Não use um nome próprio.
- Fale em português simples, com empatia e frases curtas.
- Comece pelo impacto prático no bolso/vida cotidiana.
- Contexto > opinião. Cite a fonte se houver, no fim: (Fonte: ...).
- Se não houver contexto, diga que vai buscar e faça uma resposta curta sem inventar.
- Não prometa ações que não pode cumprir. Não peça login.
- Se receber áudio, já converta mentalmente para texto antes de responder.
- Se a pergunta pedir “como fazer”, responda passo a passo enxuto.
- Evite juridiquês; traduza termos complexos.
- Não recomende voto ou apoio a candidato/partido. Se houver controvérsia, explique os dois lados de forma neutra.
- Quando identificar boato/fake news, explique por que é improvável e cite fonte oficial para conferir.
- FORMATO DA RESPOSTA:
- 1) Uma frase começando com "Em resumo: ..." em até 2 frases.
- 2) Em seguida, uma explicação mais detalhada em até 2 parágrafos curtos.
"""


class AssistantPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.llm = ChatOpenAI(
            api_key=SecretStr(settings.openai_api_key),
            model=settings.openai_model,
            temperature=0.2,
        )
        self.embeddings = OpenAIEmbeddings(
            api_key=SecretStr(settings.openai_api_key),
            model=settings.openai_embeddings_model,
        )
        self.vectorstore = self._init_vectorstore()
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("system", "Contexto recuperado:\n{context}"),
                ("human", "{question}"),
            ]
        )
        history_db_path = Path(settings.history_db)
        history_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.history_db = history_db_path

    def _init_vectorstore(self) -> Optional[Chroma]:
        data_dir = Path(self.settings.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        docs = load_corpus(data_dir)
        if not docs:
            logger.info("Nenhum documento em %s; RAG ficará vazio", data_dir)
            return None
        texts = [text for _, _, text in docs]
        metadatas = [{"id": doc_id, "title": title} for doc_id, title, _ in docs]
        store = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
            persist_directory=str(data_dir / "chroma"),
        )
        logger.info("Vectorstore carregado com %s documentos", len(texts))
        return store

    def _retrieve_context(self, question: str, k: int = 3) -> RetrievedContext:
        if not self.vectorstore:
            return RetrievedContext(text="", sources=[])
        docs = self.vectorstore.similarity_search(question, k=k)
        parts = []
        sources: List[str] = []
        for d in docs:
            source = d.metadata.get("title") or d.metadata.get("id", "desconhecido")
            sources.append(source)
            parts.append(f"[{source}] {d.page_content}")
        return RetrievedContext(text="\n\n".join(parts), sources=sources)

    def _history(self, session_id: str) -> SQLChatMessageHistory:
        return SQLChatMessageHistory(
            session_id=session_id,
            connection_string=f"sqlite:///{self.history_db}",
        )

    async def run(self, question: str, session_id: str) -> Tuple[str, List[str]]:
        ctx = self._retrieve_context(question)
        history = self._history(session_id)

        # Sliding window: mantém apenas os últimos 6 turnos para evitar custo e estouro de contexto
        recent_messages = history.messages[-6:]
        prompt_messages = self.prompt.format_messages(
            context=ctx.text, question=question
        )
        messages: List[BaseMessage] = [*recent_messages, *prompt_messages]

        ai_message: AIMessage = await self.llm.ainvoke(messages)  # type: ignore[assignment]
        content = (
            ai_message.content
            if isinstance(ai_message.content, str)
            else str(ai_message.content)
        )
        history.add_user_message(question)
        history.add_ai_message(content)
        return content, ctx.sources


tts_client = OpenAITTSClient(
    api_key=settings.openai_api_key,
    model=settings.openai_tts_model,
    voice=settings.openai_tts_voice,
)
evolution_client = EvolutionAPIClient(
    base_url=settings.evolution_base_url,
    api_key=settings.evolution_api_key,
    default_instance=settings.evolution_instance,
)
assistant = AssistantPipeline(settings)


app = FastAPI(
    title="MVP WhatsApp Bot",
    version="0.2.0",
)


@app.on_event("startup")
async def startup_event() -> None:
    logger.info("Bot iniciado. Instancia padrao=%s", settings.evolution_instance)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await asyncio.gather(
        tts_client.aclose(),
        evolution_client.aclose(),
    )


@dataclass
class IncomingMessage:
    text: Optional[str]
    number: str
    instance: Optional[str] = None
    audio_url: Optional[str] = None


def normalize_number(jid: Optional[str]) -> str:
    """Remove sufixos do JID do WhatsApp (ex: @s.whatsapp.net)."""
    if not jid:
        return ""
    return jid.split("@")[0]


def extract_text(message_block: Dict[str, Any]) -> Optional[str]:
    """Extrai texto de estruturas comuns da Evolution/Baileys."""
    direct_text = (
        message_block.get("text")
        or message_block.get("body")
        or message_block.get("content")
    )
    if isinstance(direct_text, str) and direct_text.strip():
        return direct_text.strip()

    message = message_block.get("message", {})
    if isinstance(message, dict):
        if "conversation" in message:
            return str(message["conversation"]).strip()
        extended = message.get("extendedTextMessage", {})
        if isinstance(extended, dict) and "text" in extended:
            return str(extended["text"]).strip()
        image = message.get("imageMessage", {})
        if isinstance(image, dict) and "caption" in image:
            return str(image["caption"]).strip()
        video = message.get("videoMessage", {})
        if isinstance(video, dict) and "caption" in video:
            return str(video["caption"]).strip()

    return None


def extract_audio_url(message_block: Dict[str, Any]) -> Optional[str]:
    message = message_block.get("message")
    if isinstance(message, dict):
        audio = message.get("audioMessage", {})
        if isinstance(audio, dict) and "url" in audio:
            return str(audio["url"])
    media_url = message_block.get("mediaUrl") or message_block.get("audioUrl")
    return str(media_url) if media_url else None


def parse_incoming(payload: Dict[str, Any]) -> Optional[IncomingMessage]:
    """Try to extract message text or audio URL + number from Evolution webhook payloads."""
    container = payload.get("data") if isinstance(payload, dict) else None
    if isinstance(container, dict):
        base = container
    else:
        base = payload if isinstance(payload, dict) else {}

    instance = (
        payload.get("instance")
        or payload.get("instanceName")
        or base.get("instanceName")
        or base.get("sessionId")
        or base.get("instanceId")
    )

    message_candidates = []
    if isinstance(base.get("messages"), list):
        message_candidates.extend(base["messages"])
    if isinstance(base, dict):
        message_candidates.append(base)

    for candidate in message_candidates:
        if not isinstance(candidate, dict):
            continue
        key_data = candidate.get("key", {})
        if isinstance(key_data, dict) and key_data.get("fromMe"):
            continue  # ignore echoes
        number = normalize_number(
            key_data.get("remoteJid")
            or candidate.get("chatId")
            or candidate.get("remoteJid")
            or candidate.get("from")
        )
        text = extract_text(candidate)
        audio_url = extract_audio_url(candidate)
        if (text or audio_url) and number:
            return IncomingMessage(
                text=text, number=number, instance=instance, audio_url=audio_url
            )

    return None


async def verify_webhook_token(x_webhook_token: Optional[str] = Header(None)) -> None:
    if settings.webhook_token and settings.webhook_token != x_webhook_token:
        raise HTTPException(status_code=401, detail="Invalid webhook token")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


async def handle_tools(text: str) -> str:
    """Placeholder para futuras function callings (API de leis, cálculos, etc.)."""
    lowered = text.lower()
    if any(
        x in lowered
        for x in ["é verdade", "isso é verdade", "fake", "mentira", "boato"]
    ):
        return f"[INTENÇÃO: checagem_de_boato]\n{text}"
    if any(
        x in lowered for x in ["pl ", "projeto de lei", "lei ", "constituição", "art. "]
    ):
        return f"[INTENÇÃO: duvida_sobre_lei]\n{text}"
    return f"[INTENÇÃO: geral]\n{text}"


async def process_message_content(content: str, session_id: str) -> str:
    enriched_question = await handle_tools(content)
    intent = "geral"
    if enriched_question.startswith("[INTENÇÃO:"):
        intent = enriched_question.split("]")[0].split(":")[1].strip()

    try:
        reply, sources = await assistant.run(enriched_question, session_id=session_id)
    except Exception as exc:
        logger.exception("Falha no core de IA: %s", exc)
        return (
            "Dei uma pane aqui na IA 😔\n"
            "Tenta de novo em alguns minutos ou consulta diretamente o site da Câmara dos Deputados."
        )

    if sources:
        fontes = ", ".join(sources[:3])
        reply = f"{reply}\n\n(Fonte: {fontes})"
    logger.info(
        "session=%s intent=%s rag_used=%s sources=%s question=%r",
        session_id,
        intent,
        bool(sources),
        ", ".join(sources[:3]) if sources else "-",
        content[:160],
    )
    return reply


@app.post("/webhook/evolution")
async def handle_evolution_webhook(
    request: Request,
    _: None = Depends(verify_webhook_token),
) -> JSONResponse:
    payload: Dict[str, Any] = await request.json()
    incoming = parse_incoming(payload)

    if not incoming:
        logger.info("Ignored webhook: unable to extract text/number")
        return JSONResponse({"status": "ignored", "reason": "no_message"})

    user_text = incoming.text
    if not user_text and incoming.audio_url:
        try:
            audio_bytes = await evolution_client.fetch_media(incoming.audio_url)
            user_text = await tts_client.transcribe(audio_bytes)
            logger.info("Transcribed audio to: %s", user_text)
        except Exception as exc:  # pragma: no cover - external failure
            logger.error("Falha no STT: %s", exc)

    if not user_text:
        return JSONResponse({"status": "ignored", "reason": "empty_message"})

    # Onboarding simples para saudações curtas
    greeting = user_text.strip().lower()
    if greeting in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"}:
        intro = (
            "Oi! Eu ajudo a explicar leis, projetos e boatos políticos em linguagem simples. "
            'Exemplos: "É verdade que vão taxar o Pix?" ou "O que é o PL 2338 sobre IA?".'
        )
        await evolution_client.send_text(incoming.number, intro, incoming.instance)
        logger.info("session=%s sent_intro=True", incoming.number)
        return JSONResponse({"status": "ok", "echo": user_text})

    reply_text = await process_message_content(user_text, session_id=incoming.number)

    try:
        await evolution_client.send_text(incoming.number, reply_text, incoming.instance)
    except Exception as exc:  # pragma: no cover - operational path
        logger.exception("Failed to send text: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to send reply") from exc

    try:
        # Envia áudio apenas se a entrada foi áudio para evitar custo/ruído em texto simples
        if incoming.audio_url:
            audio_bytes = await tts_client.synthesize(reply_text)
            await evolution_client.send_audio(
                incoming.number, audio_bytes, incoming.instance
            )
    except Exception as exc:  # pragma: no cover - operational path
        logger.exception("Failed to send audio: %s", exc)

    logger.info(
        "session=%s instance=%s text=%r sent_audio=%s",
        incoming.number,
        incoming.instance or settings.evolution_instance,
        user_text[:160],
        bool(incoming.audio_url),
    )

    return JSONResponse({"status": "ok", "echo": user_text})


@app.get("/")
async def root() -> Dict[str, str]:
    return {
        "message": "Bot está no ar",
        "instance": settings.evolution_instance or "",
    }


class AskRequest(BaseModel):
    question: str
    session_id: str


class AskResponse(BaseModel):
    answer: str


@app.post("/api/ask", response_model=AskResponse)
async def api_ask(req: AskRequest) -> AskResponse:
    session_id = req.session_id.strip() or "anon"
    answer = await process_message_content(req.question, session_id=session_id)
    return AskResponse(answer=answer)
