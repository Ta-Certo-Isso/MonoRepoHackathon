import argparse
import asyncio
import math
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

from openai import OpenAI

from src.core.config import BASE_DIR, settings
from src.core.database import get_db, init_db
from src.core.logging import get_logger, setup_logging
from src.models.db_models import DBProposition, DBScript, DBVideo
from src.models.schemas import Proposition
from src.services.collector_service import collector_service
from src.services.sora_service import sora_video_service
from src.services.tiktok_service import tiktok_service


logger = get_logger(__name__)


class MontoyaCLI:
    """
    Aggregates the previous run_* scripts under a single POO-style interface.
    Each public method can be triggered through the CLI entry point or reused programmatically.
    """

    def __init__(self) -> None:
        setup_logging()
        init_db()
        sys.stdout.reconfigure(encoding="utf-8")

    @contextmanager
    def _db_session(self):
        db = next(get_db())
        try:
            yield db
        finally:
            db.close()

    # ------------------------------------------------------------------ Collectors
    def collect(self, days_back: int = 5, limit: int = 5) -> None:
        logger.info("Running collector: days_back=%s limit=%s", days_back, limit)
        with self._db_session() as db:
            summary = asyncio.run(collector_service.run_collection(days_back=days_back, limit=limit, db=db))
            print(summary)

    # ------------------------------------------------------------------ Scripts
    def regenerate_scripts(self) -> None:
        with self._db_session() as db:
            propositions = db.query(DBProposition).order_by(DBProposition.id.asc()).all()
            print(f"Reescrevendo scripts para {len(propositions)} proposições")

            for prop in propositions:
                if not prop:
                    continue

                deleted = db.query(DBScript).filter(DBScript.proposition_id == prop.id).delete()
                if deleted:
                    db.commit()
                    print(f"Removidos {deleted} roteiros antigos de '{prop.title}'")

                schema = Proposition(
                    title=prop.title,
                    description=prop.description,
                    content=prop.content,
                    link=prop.link,
                    date=prop.date,
                    source=prop.source,
                    level=prop.level,
                    collection_type=prop.collection_type,
                    relevance_score=None,
                )
                script = tiktok_service.generate_script(schema, style="informative", db=db)
                preview = (script or "")[:120].replace("\n", " ")
                print(f"Novo script para '{prop.title}': {preview}...")

    def print_first_script(self) -> None:
        with self._db_session() as db:
            prop = db.query(DBProposition).order_by(DBProposition.id.asc()).first()
            if not prop:
                raise SystemExit("Nenhuma proposição disponível no banco.")

            schema = Proposition(
                title=prop.title,
                description=prop.description,
                content=prop.content,
                link=prop.link,
                date=prop.date,
                source=prop.source,
                level=prop.level,
                collection_type=prop.collection_type,
                relevance_score=None,
            )
            script = tiktok_service.generate_script(schema, style="informative", db=db)
            print(script)

    # ------------------------------------------------------------------ Video generation (Sora)
    def generate_video(
        self,
        proposition_id: Optional[int] = None,
        level: str = "municipal",
        source: Optional[str] = None,
        output_root: Optional[Path] = None,
    ) -> Path:
        if sora_video_service is None:
            raise SystemExit("Serviço do Sora indisponível. Verifique o .env.")

        output_root = output_root or (BASE_DIR / "output" / "videos" / "sora")
        with self._db_session() as db:
            proposition = self._get_target_proposition(db, proposition_id, level, source)
            script = self._get_latest_script(db, proposition.id)
            raw_segments = self._parse_script_segments(script.content)
            segments = self._ensure_segment_count([seg for seg in raw_segments if seg["audio"]], desired=2)

            if not any(seg["audio"] for seg in segments):
                raise SystemExit("O script não contém trechos válidos em [AUDIO]. Gere novamente.")

            run_dir = self._select_run_directory(Path(output_root))
            base_name = self._slugify(proposition.title)[:50]

            total_audio_chars = sum(len(seg["audio"]) for seg in segments)
            logger.info(
                "Gerando vídeo para '%s' (roteiro %s chars) em %s",
                proposition.title,
                total_audio_chars,
                run_dir,
            )

            final_path = sora_video_service.generate_video_from_script(
                segments,
                base_filename=base_name,
                output_dir=run_dir,
                max_segments=2,
                segment_duration=12,
            )

            self._persist_video_record(db, script, Path(final_path), status="completed")
            print(f"Vídeo final gerado em: {final_path}")
            return Path(final_path)

    # ------------------------------------------------------------------ Sora smoke test
    def test_sora(self, prompt: str = "A video of a cat", size: str = "720x1280", seconds: int = 4) -> None:
        endpoint = settings.AZURE_OPENAI_VIDEOS_ENDPOINT or settings.OPENAI_API_KEY
        api_key = settings.AZURE_OPENAI_VIDEOS_API_KEY or settings.AZURE_OPENAI_API_KEY

        if not endpoint or not api_key:
            raise SystemExit("Configure AZURE_OPENAI_VIDEOS_ENDPOINT e AZURE_OPENAI_VIDEOS_API_KEY.")

        client = OpenAI(
            api_key=api_key,
            base_url=self._normalize_base_url(endpoint),
            default_headers={"api-key": api_key},
        )

        try:
            resp = client.videos.create(
                model=settings.AZURE_OPENAI_VIDEOS_MODEL or "sora-2",
                prompt=prompt,
                size=size,
                seconds=str(seconds),
            )
            print("Requisição enviada com sucesso:")
            print(resp)
        except Exception as exc:
            print("Falha ao chamar a API:", exc)
            raise

    # ------------------------------------------------------------------ Helpers (previous free functions)
    @staticmethod
    def _slugify(value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower() or "video"

    @staticmethod
    def _parse_script_segments(raw: str) -> List[Dict[str, str]]:
        cleaned = raw.replace("```plaintext", "").replace("```", "")
        segments: List[Dict[str, str]] = []
        current_audio: List[str] = []
        current_visual: List[str] = []
        mode: Optional[str] = None

        def flush():
            if current_audio or current_visual:
                segments.append(
                    {
                        "audio": " ".join(current_audio).strip(),
                        "visual": " ".join(current_visual).strip(),
                    }
                )

        for line in cleaned.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r"^\[\d+\s*-\s*\d+s\]", stripped):
                flush()
                current_audio.clear()
                current_visual.clear()
                mode = None
                continue
            tag_match = re.match(r"^\[(AUDIO|VISUAL)\]\s*(.*)$", stripped, re.IGNORECASE)
            if tag_match:
                mode = tag_match.group(1).lower()
                content = tag_match.group(2).strip()
                if mode == "audio" and content:
                    current_audio.append(content)
                elif mode == "visual" and content:
                    current_visual.append(content)
                continue
            if stripped.startswith("[") and not tag_match:
                continue
            if mode == "audio":
                current_audio.append(stripped)
            elif mode == "visual":
                current_visual.append(stripped)

        flush()
        parsed = [seg for seg in segments if seg.get("audio")]
        if parsed:
            return parsed

        fallback = re.sub(r"\[[^\]]+\]", " ", cleaned)
        fallback = re.sub(r"\s+", " ", fallback).strip()
        if fallback:
            return [{"audio": fallback, "visual": ""}]
        return []

    @staticmethod
    def _split_text_evenly(text: str, parts: int) -> List[str]:
        words = text.split()
        if not words:
            return ["" for _ in range(parts)]
        chunk_size = math.ceil(len(words) / parts)
        result = [" ".join(words[i : i + chunk_size]).strip() for i in range(0, len(words), chunk_size)]
        while len(result) < parts:
            result.append("")
        return result[:parts]

    def _ensure_segment_count(self, segments: List[Dict[str, str]], desired: int) -> List[Dict[str, str]]:
        if not segments:
            return [{"audio": "", "visual": ""} for _ in range(desired)]

        if len(segments) == desired:
            return segments

        if len(segments) > desired:
            chunk_size = math.ceil(len(segments) / desired)
            merged: List[Dict[str, str]] = []
            for idx in range(0, len(segments), chunk_size):
                group = segments[idx : idx + chunk_size]
                merged.append(
                    {
                        "audio": " ".join(seg.get("audio", "") for seg in group).strip(),
                        "visual": " ".join(seg.get("visual", "") for seg in group).strip(),
                    }
                )
                if len(merged) == desired:
                    break
            return merged

        combined_audio = " ".join(seg.get("audio", "") for seg in segments).strip()
        combined_visual = " ".join(seg.get("visual", "") for seg in segments).strip()
        audio_parts = self._split_text_evenly(combined_audio, desired)
        visual_base = combined_visual if combined_visual else combined_audio
        visual_parts = self._split_text_evenly(visual_base, desired)
        return [{"audio": audio_parts[i], "visual": visual_parts[i]} for i in range(desired)]

    @staticmethod
    def _select_run_directory(base_dir: Path) -> Path:
        base_dir.mkdir(parents=True, exist_ok=True)
        run_pattern = re.compile(r"^run\s+(\d+)$", re.IGNORECASE)
        runs: List[int] = []

        for child in base_dir.iterdir():
            if child.is_dir():
                match = run_pattern.match(child.name)
                if match:
                    runs.append(int(match.group(1)))

        if not runs:
            target = base_dir / "run 1"
            target.mkdir(parents=True, exist_ok=True)
            return target

        last_run = max(runs)
        last_dir = base_dir / f"run {last_run}"
        if not any(last_dir.iterdir()):
            return last_dir

        target = base_dir / f"run {last_run + 1}"
        target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def _get_target_proposition(
        db,
        proposition_id: Optional[int],
        level: Optional[str],
        source: Optional[str],
    ) -> DBProposition:
        query = db.query(DBProposition)
        if proposition_id:
            prop = query.filter(DBProposition.id == proposition_id).first()
        else:
            if level:
                query = query.filter(DBProposition.level == level)
            if source:
                query = query.filter(DBProposition.source == source)
            prop = query.order_by(DBProposition.id.desc()).first()

        if not prop:
            raise SystemExit("Nenhuma proposição encontrada para gerar o vídeo.")
        return prop

    @staticmethod
    def _get_latest_script(db, proposition_id: int) -> DBScript:
        script = (
            db.query(DBScript)
            .filter(DBScript.proposition_id == proposition_id)
            .order_by(DBScript.id.desc())
            .first()
        )
        if not script:
            raise SystemExit("Nenhum script encontrado para esta proposição. Gere os scripts antes.")
        return script

    @staticmethod
    def _persist_video_record(db, script: DBScript, local_path: Path, status: str, error_message: Optional[str] = None):
        video = DBVideo(
            script_id=script.id,
            local_path=str(local_path),
            status=status,
            error_message=error_message,
        )
        db.add(video)
        db.commit()

    @staticmethod
    def _normalize_base_url(url: str) -> str:
        u = url.strip().rstrip("/")
        if u.endswith("/videos"):
            u = u[: -len("/videos")]
        if not u.endswith("/openai/v1"):
            if u.endswith("/openai"):
                u = f"{u}/v1"
            else:
                u = f"{u}/openai/v1"
        return u + "/"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Utilitários CLI para o módulo Montoya.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Executa a coleta para todas as fontes.")
    collect_parser.add_argument("--days-back", type=int, default=5)
    collect_parser.add_argument("--limit", type=int, default=5)

    subparsers.add_parser("regenerate-scripts", help="Recria todos os roteiros no banco.")
    subparsers.add_parser("print-script", help="Gera e imprime um roteiro informativo para a primeira proposição.")

    video_parser = subparsers.add_parser("generate-video", help="Gera vídeo com o Sora.")
    video_parser.add_argument("--proposition-id", type=int)
    video_parser.add_argument("--level", type=str, default="municipal")
    video_parser.add_argument("--source", type=str, help="Filtro de fonte (ex.: camara_deputados)")
    video_parser.add_argument("--output-dir", type=Path, default=BASE_DIR / "output" / "videos" / "sora")

    test_parser = subparsers.add_parser("test-sora", help="Teste rápido do endpoint do Sora.")
    test_parser.add_argument("--prompt", type=str, default="A video of a cat")
    test_parser.add_argument("--size", type=str, default="720x1280")
    test_parser.add_argument("--seconds", type=int, default=4)

    return parser


def main() -> None:
    cli = MontoyaCLI()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "collect":
        cli.collect(days_back=args.days_back, limit=args.limit)
    elif args.command == "regenerate-scripts":
        cli.regenerate_scripts()
    elif args.command == "print-script":
        cli.print_first_script()
    elif args.command == "generate-video":
        cli.generate_video(
            proposition_id=args.proposition_id,
            level=args.level,
            source=args.source,
            output_root=args.output_dir,
        )
    elif args.command == "test-sora":
        cli.test_sora(prompt=args.prompt, size=args.size, seconds=args.seconds)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

