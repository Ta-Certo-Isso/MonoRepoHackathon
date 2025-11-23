import asyncio
import base64
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
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
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from pydantic import BaseModel, SecretStr


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("whatsappchatbot")
if not logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    logger.addHandler(stream_handler)
logger.setLevel(logging.INFO)
logger.propagate = False


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    return os.environ.get(name, default)


def _parse_msisdn(raw: str) -> str:
    """Keep only digits to normalize phone numbers."""
    digits = "".join(ch for ch in raw if ch.isdigit())
    return digits


def _env_phone_list(name: str) -> List[str]:
    raw = os.environ.get(name, "")
    if not raw:
        return []
    numbers = []
    for chunk in raw.split(","):
        digits = _parse_msisdn(chunk.strip())
        if digits:
            numbers.append(digits)
    return numbers


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
    mongo_connection_uri: Optional[str] = _env("MONGO_CONNECTION_URI")
    mongo_db_name: str = _env("MONGO_DB_NAME", "whatsappchatbot") or "whatsappchatbot"
    mongo_collection_name: str = (
        _env("MONGO_COLLECTION_NAME", "interactions") or "interactions"
    )
    allowed_numbers: List[str] = field(default_factory=list)

    def validate(self) -> None:
        self.allowed_numbers = self.allowed_numbers or _env_phone_list(
            "ALLOWED_WHATSAPP_NUMBERS"
        )
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


ReferenceSource = NamedTuple(
    "ReferenceSource", [("keywords", Tuple[str, ...]), ("label", str), ("url", str)]
)

REFERENCE_LINKS: List[ReferenceSource] = [
    ReferenceSource(
        keywords=("pix", "pagamento instantâneo", "taxar o pix"),
        label="Banco Central do Brasil - Pix",
        url="https://www.bcb.gov.br/estabilidadefinanceira/pix",
    ),
    ReferenceSource(
        keywords=("pl ", "projeto de lei", "pl ", "lei ", "senado"),
        label="Portal da Câmara dos Deputados",
        url="https://www.camara.leg.br/busca",
    ),
    ReferenceSource(
        keywords=("imposto de renda", "irpf", "receita federal"),
        label="Receita Federal - IRPF",
        url="https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda",
    ),
    ReferenceSource(
        keywords=("benefício", "bolsa família", "auxílio"),
        label="Portal Gov.br de benefícios sociais",
        url="https://www.gov.br/cidadania/pt-br/auxilio-brasil",
    ),
    ReferenceSource(
        keywords=("fake news", "boato", "desinformação"),
        label="Saiba Mais - Ministério da Justiça",
        url="https://www.gov.br/mj/pt-br/assuntos/fakenews",
    ),
]


SYSTEM_PROMPT = """
Você é o assistente oficial da iniciativa cívica "Tá Certo Isso?". Objetivo:
- ajudar qualquer pessoa a entender leis, políticas públicas e boatos, sempre com foco prático no bolso/vida cotidiana;
- combater desinformação com empatia e linguagem acessível;
- representar o tom institucional da Tá Certo Isso?, sem opinião partidária.

Regras fixas:
- Identifique-se como assistente da Tá Certo Isso? na primeira frase, mas sem repetir em excesso.
- Use português simples, frases curtas, e evite repetir a mesma ideia.
- Comece com uma frase-resumo de até 2 frases, sem utilizar a expressão "Em resumo".
- Depois do resumo, entregue no máximo dois parágrafos curtos com detalhes e passos acionáveis.
- Se não houver dados suficientes, avise e sugira onde buscar.
- Não prometa ações que não pode cumprir, nem peça dados pessoais.
- Se detectar boato/fake news, explique calmamente por que é improvável e indique fonte oficial.
- Sempre que citar fonte, use um link confiável real.
- Nunca incentive voto ou posição partidária.
"""
def select_reference_link(question: str, sources: List[str]) -> Optional[str]:
    """Best-effort mapping from topic keywords to trusted URLs."""
    combined = f"{question} {' '.join(sources)}".lower()
    for entry in REFERENCE_LINKS:
        if any(keyword in combined for keyword in entry.keywords):
            return f"{entry.label} - {entry.url}"
    return None


def sanitize_reply_text(reply: str) -> str:
    """Remove prefixos repetidos como 'Em resumo:' que o modelo possa inserir."""
    trimmed = reply.strip()
    prefix = "em resumo:"
    lower = trimmed.lower()
    if lower.startswith(prefix):
        without = trimmed[len(prefix) :].lstrip(" -:\n\t")
        trimmed = without or trimmed
    return trimmed




class AssistantPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.history_limit = 8
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
                ("system", "{conversation_instructions}"),
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
        history_messages = history.messages
        recent_messages = history_messages[-self.history_limit :]
        conversation_instructions = (
            "Primeira interação desta sessão. Faça um cumprimento curto, apresente-se como assistente da Tá Certo Isso? e explique em uma frase como pode ajudar."
            if not history_messages
            else "Conversa em andamento. Não se reapresente; vá direto à resposta usando o histórico como contexto."
        )
        prompt_messages = self.prompt.format_messages(
            context=ctx.text,
            question=question,
            conversation_instructions=conversation_instructions,
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
mongo_client: Optional[AsyncIOMotorClient] = None
mongo_collection: Optional[AsyncIOMotorCollection] = None
PROCESSED_MESSAGE_LIMIT = 512
_processed_messages: OrderedDict[str, float] = OrderedDict()
def _is_duplicate_message(message_id: Optional[str]) -> bool:
    if not message_id:
        return False
    if message_id in _processed_messages:
        return True
    _processed_messages[message_id] = time.time()
    if len(_processed_messages) > PROCESSED_MESSAGE_LIMIT:
        _processed_messages.popitem(last=False)
    return False


app = FastAPI(
    title="MVP WhatsApp Bot",
    version="0.2.0",
)


@app.on_event("startup")
async def startup_event() -> None:
    global mongo_client, mongo_collection
    logger.info("Bot iniciado. Instancia padrao=%s", settings.evolution_instance)
    if settings.mongo_connection_uri:
        try:
            mongo_client = AsyncIOMotorClient(settings.mongo_connection_uri)
            database = mongo_client[settings.mongo_db_name]
            await database.command("ping")
            mongo_collection = database[settings.mongo_collection_name]
            logger.info(
                "MongoDB conectado db=%s collection=%s",
                settings.mongo_db_name,
                settings.mongo_collection_name,
            )
        except Exception as exc:  # pragma: no cover - ambiente externo
            logger.exception("Falha ao conectar no MongoDB: %s", exc)
            if mongo_client:
                mongo_client.close()
            mongo_client = None
            mongo_collection = None


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await asyncio.gather(
        tts_client.aclose(),
        evolution_client.aclose(),
    )
    if mongo_client:
        mongo_client.close()


@dataclass
class IncomingMessage:
    text: Optional[str]
    number: str
    instance: Optional[str] = None
    audio_url: Optional[str] = None
    message_id: Optional[str] = None


def normalize_number(jid: Optional[str]) -> str:
    """Remove sufixos e caracteres não numéricos do JID do WhatsApp."""
    if not jid:
        return ""
    base = jid.split("@")[0]
    digits = _parse_msisdn(base)
    return digits or base


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
    def extract_url(container: Any) -> Optional[str]:
        if isinstance(container, dict):
            if "url" in container and container["url"]:
                return str(container["url"])
            if "directPath" in container and container["directPath"]:
                return str(container["directPath"])
        return None

    message = message_block.get("message")
    if isinstance(message, dict):
        for key in ("audioMessage", "pttMessage", "voiceMessage"):
            url = extract_url(message.get(key))
            if url:
                return url
    for key in ("audio", "voice", "media", "document"):
        url = extract_url(message_block.get(key))
        if url:
            return url
    media_url = (
        message_block.get("mediaUrl")
        or message_block.get("audioUrl")
        or message_block.get("downloadUrl")
    )
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

    message_candidates: List[Dict[str, Any]] = []
    if isinstance(base.get("messages"), list):
        for candidate in base["messages"]:
            if isinstance(candidate, dict):
                message_candidates.append(candidate)
    if not message_candidates and isinstance(base, dict):
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
        message_id = (
            key_data.get("id")
            or candidate.get("id")
            or candidate.get("messageId")
            or candidate.get("messageID")
        )
        if (text or audio_url) and number:
            return IncomingMessage(
                text=text,
                number=number,
                instance=instance,
                audio_url=audio_url,
                message_id=message_id,
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


async def process_message_content(
    content: str, session_id: str, *, metadata: Optional[Dict[str, Any]] = None
) -> str:
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

    reply = sanitize_reply_text(reply)
    unique_sources = []
    for src in sources:
        if src not in unique_sources:
            unique_sources.append(src)

    reference_link = select_reference_link(question=content, sources=unique_sources)
    if reference_link:
        reply = f"{reply}\n\n(Fonte: {reference_link})"
    elif unique_sources:
        fontes = ", ".join(unique_sources[:3])
        reply = f"{reply}\n\n(Fonte: {fontes})"
    logger.info(
        "session=%s intent=%s rag_used=%s sources=%s question=%r reference=%s",
        session_id,
        intent,
        bool(sources),
        ", ".join(sources[:3]) if sources else "-",
        content[:160],
        reference_link or "-",
    )

    await persist_interaction(
        session_id=session_id,
        question=content,
        answer=reply,
        sources=sources,
        intent=intent,
        metadata=metadata or {},
        reference_link=reference_link,
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

    if _is_duplicate_message(incoming.message_id):
        logger.info(
            "Ignored webhook: duplicate message_id=%s",
            incoming.message_id,
        )
        return JSONResponse({"status": "ignored", "reason": "duplicate"})

    if settings.allowed_numbers and incoming.number not in settings.allowed_numbers:
        logger.info(
            "Ignored webhook: number %s not in allow-list", incoming.number
        )
        return JSONResponse({"status": "ignored", "reason": "unauthorized_sender"})

    user_text = incoming.text
    if not user_text and incoming.audio_url:
        try:
            audio_bytes = await evolution_client.fetch_media(incoming.audio_url)
            user_text = await tts_client.transcribe(audio_bytes)
            logger.info("Transcribed audio to: %s", user_text)
        except Exception as exc:  # pragma: no cover - external failure
            logger.exception("Falha no STT: %s", exc)

    if not user_text:
        fallback_text = (
            "Não consegui entender o áudio desta vez. "
            "Pode tentar repetir ou mandar a pergunta em texto?"
        )
        try:
            await evolution_client.send_text(
                incoming.number, fallback_text, incoming.instance
            )
        except Exception as exc:
            logger.exception("Falha ao enviar fallback: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to send fallback") from exc
        logger.warning(
            "session=%s sem conteúdo compreensível; fallback enviado",
            incoming.number,
        )
        return JSONResponse({"status": "ignored", "reason": "empty_message"})

    logger.info(
        "session=%s mensagem recebida audio=%s chars=%s",
        incoming.number,
        bool(incoming.audio_url),
        len(user_text),
    )

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

    metadata = {
        "channel": "evolution",
        "audio_input": bool(incoming.audio_url),
        "instance": incoming.instance or settings.evolution_instance,
    }
    reply_text = await process_message_content(
        user_text, session_id=incoming.number, metadata=metadata
    )

    audio_sent = False
    try:
        # Envia áudio apenas se a entrada foi áudio para evitar custo/ruído em texto simples
        if incoming.audio_url:
            logger.info("session=%s iniciando resposta em áudio", incoming.number)
            audio_bytes = await tts_client.synthesize(reply_text)
            await evolution_client.send_audio(
                incoming.number, audio_bytes, incoming.instance
            )
            audio_sent = True
            logger.info(
                "session=%s áudio entregue com %s bytes",
                incoming.number,
                len(audio_bytes),
            )
    except Exception as exc:  # pragma: no cover - operational path
        logger.exception("Failed to send audio: %s", exc)
        audio_sent = False

    should_send_text = not incoming.audio_url or not audio_sent
    if should_send_text:
        try:
            await evolution_client.send_text(
                incoming.number, reply_text, incoming.instance
            )
        except Exception as exc:  # pragma: no cover - operational path
            logger.exception("Failed to send text: %s", exc)
            raise HTTPException(status_code=500, detail="Failed to send reply") from exc
    else:
        logger.info("session=%s resposta enviada apenas em áudio", incoming.number)

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
    answer = await process_message_content(
        req.question, session_id=session_id, metadata={"channel": "api"}
    )
    return AskResponse(answer=answer)


async def persist_interaction(
    session_id: str,
    question: str,
    answer: str,
    sources: List[str],
    intent: str,
    metadata: Dict[str, Any],
    reference_link: Optional[str] = None,
) -> None:
    if not mongo_collection:
        return
    document = {
        "sessionId": session_id,
        "question": question,
        "answer": answer,
        "sources": sources,
        "intent": intent,
        "metadata": metadata,
        "timestamp": datetime.now(timezone.utc),
    }
    if reference_link:
        document["referenceLink"] = reference_link
    try:
        await mongo_collection.insert_one(document)
    except Exception as exc:  # pragma: no cover - depende do cluster
        logger.warning("Falha ao salvar interação no MongoDB: %s", exc)
