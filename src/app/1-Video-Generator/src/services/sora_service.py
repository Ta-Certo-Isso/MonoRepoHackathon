from __future__ import annotations

import math
import os
import subprocess
import textwrap
import time
from pathlib import Path
from typing import List, Optional, Dict

from openai import OpenAI

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class SoraVideoService:
    """
    Encapsula a integração com o endpoint de vídeo (Sora/Azure OpenAI),
    gerando segmentos verticais com narração invisível e b-roll guiado.
    """

    ALLOWED_DURATIONS = (4, 8, 12)
    ALLOWED_SIZES = ("720x1280", "1280x720", "1024x1792", "1792x1024")

    def __init__(self) -> None:
        base_url = (
            settings.AZURE_OPENAI_VIDEOS_ENDPOINT
            or os.getenv("ENDPOINT_URL")
            or os.getenv("OPENAI_BASE_URL")
            or ""
        ).strip()
        api_key = (
            settings.AZURE_OPENAI_VIDEOS_API_KEY
            or os.getenv("AZURE_OPENAI_API_KEY")
            or settings.OPENAI_API_KEY
            or os.getenv("OPENAI_API_KEY")
            or ""
        ).strip()

        if not base_url or not api_key:
            raise RuntimeError(
                "Configure AZURE_OPENAI_VIDEOS_ENDPOINT e AZURE_OPENAI_VIDEOS_API_KEY para usar o Sora."
            )

        self.base_url = self._normalize_base_url(base_url)
        self.model = (settings.AZURE_OPENAI_VIDEOS_MODEL or "sora-2").strip()
        size_candidate = (
            getattr(settings, "AZURE_OPENAI_VIDEOS_SIZE", None)
            or os.getenv("AZURE_OPENAI_VIDEOS_SIZE")
            or "720x1280"
        )
        self.size = self._sanitize_size(size_candidate)
        self.client = OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            default_headers={"api-key": api_key},
        )

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

    def generate_video_from_script(
        self,
        segments: List[Dict[str, str]],
        base_filename: str,
        output_dir: Path,
        max_segments: int = 2,
        segment_duration: int = 12,
    ) -> Path:
        """
        Recebe uma lista de segmentos contendo áudio e orientação de cenas e produz os vídeos.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        prepared_segments = self._normalize_segments(segments, max_segments)
        if not prepared_segments:
            raise ValueError("Nenhum segmento válido para gerar o vídeo.")

        duration = self._sanitize_duration(segment_duration)
        segment_paths: List[Path] = []
        previous_video_id: Optional[str] = None

        for idx, segment in enumerate(prepared_segments, start=1):
            logger.info(
                "Gerando segmento %s/%s (áudio %s chars)",
                idx,
                len(prepared_segments),
                len(segment["audio"]),
            )
            prompt = self._build_prompt(
                segment["audio"],
                segment.get("visual", ""),
                idx,
                len(prepared_segments),
                duration,
            )
            video = self._create_and_wait(prompt, duration, previous_video_id)

            segment_path = output_dir / f"{base_filename}_s{idx:02d}.mp4"
            self._download_video(video.id, segment_path)
            segment_paths.append(segment_path)

            previous_video_id = video.id

        final_path = output_dir / f"{base_filename}_final.mp4"
        if len(segment_paths) == 1:
            final_path.write_bytes(segment_paths[0].read_bytes())
            return final_path

        if not self._concat_videos(segment_paths, final_path):
            raise RuntimeError("Falha ao concatenar os segmentos com ffmpeg.")
        return final_path

    def _create_and_wait(
        self,
        prompt: str,
        duration: int,
        remix_video_id: Optional[str] = None,
    ):
        kwargs = {
            "model": self.model,
            "prompt": prompt,
            "seconds": str(duration),
            "size": self.size,
        }

        video = self.client.videos.create(**kwargs)
        return self._poll_until_complete(video.id)

    def _poll_until_complete(self, video_id: str, sleep_seconds: int = 15):
        while True:
            video = self.client.videos.retrieve(video_id)
            status = getattr(video, "status", "unknown")
            logger.info("Vídeo %s → %s", video_id, status)
            if status in {"completed", "failed", "cancelled"}:
                if status != "completed":
                    raise RuntimeError(f"Geração {video_id} falhou com status '{status}'.")
                return video
            time.sleep(sleep_seconds)

    def _download_video(self, video_id: str, out_path: Path) -> None:
        content = self.client.videos.download_content(video_id, variant="video")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        content.write_to_file(str(out_path))
        logger.info("Vídeo %s salvo em %s", video_id, out_path)

    def _concat_videos(self, files: List[Path], output_path: Path) -> bool:
        if len(files) == 1:
            output_path.write_bytes(files[0].read_bytes())
            return True

        list_file = output_path.parent / f"{output_path.stem}_list.txt"
        with list_file.open("w", encoding="utf-8") as f:
            for file_path in files:
                f.write(f"file '{file_path.as_posix()}'\n")

        copy_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            str(output_path),
        ]

        result = subprocess.run(copy_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True

        logger.warning("ffmpeg concat copy falhou, tentando re-encode. %s", result.stderr)

        transcode_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-r",
            "24",
            "-pix_fmt",
            "yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        result = subprocess.run(transcode_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error("ffmpeg re-encode também falhou: %s", result.stderr)
            return False
        return True

    def _build_prompt(
        self,
        narration: str,
        visual_plan: str,
        index: int,
        total: int,
        duration: int,
    ) -> str:
        narration = textwrap.dedent(narration).strip()
        visual_plan = textwrap.dedent(visual_plan or "").strip()
        if not visual_plan:
            visual_plan = (
                "Use b-roll documental de ruas brasileiras, fachadas públicas e gráficos animados "
                "minimalistas para reforçar os pontos principais."
            )

        return textwrap.dedent(
            f"""
            Create a {duration} second vertical TikTok video with invisible narration only.

            Visual style:
            - Use real-world inspired Brazilian b-roll, mapas estilizados, dashboards minimalistas e ícones 3D simples.
            - Nunca mostre personagens, animais ou apresentadores. Somente cenários, objetos, gráficos ou texto estilizado.
            - Movimentos de câmera leves, cortes limpos e cor cinematográfica com contraste suave.
            - Não exiba legendas, captions ou texto na tela, a menos que seja explicitamente descrito no plano visual abaixo.

            Follow this visual plan (adicione detalhes cinematográficos coerentes):
            \"\"\"{visual_plan}\"\"\"

            Audio instructions:
            - Narração feminina brasileira, jovem/adulta (25-30 anos), energia empolgada e consistente, SEM mudar timbre entre os segmentos.
            - Fale exatamente o texto abaixo uma única vez:
            \"\"\"{narration}\"\"\"
            - Camada musical discreta e neutra.

            Garanta continuidade estética com os demais trechos do vídeo sem exibir marcas de “parte 1/2”.
            """
        ).strip()

    def _normalize_segments(self, segments: List[Dict[str, str]], max_segments: int) -> List[Dict[str, str]]:
        valid = [
            {"audio": seg.get("audio", "").strip(), "visual": seg.get("visual", "").strip()}
            for seg in segments
            if seg.get("audio", "").strip()
        ]
        if not valid:
            return []
        if len(valid) >= max_segments:
            return valid[:max_segments]

        combined_audio = " ".join(seg["audio"] for seg in valid).strip()
        combined_visual = " ".join(seg["visual"] for seg in valid).strip()
        audio_chunks = self._even_split(combined_audio, max_segments)
        visual_source = combined_visual if combined_visual else combined_audio
        visual_chunks = self._even_split(visual_source, max_segments)
        return [{"audio": audio_chunks[i], "visual": visual_chunks[i]} for i in range(max_segments)]

    @staticmethod
    def _even_split(text: str, parts: int) -> List[str]:
        words = text.split()
        if not words:
            return ["" for _ in range(parts)]
        chunk_size = math.ceil(len(words) / parts)
        chunks = [" ".join(words[i : i + chunk_size]).strip() for i in range(0, len(words), chunk_size)]
        while len(chunks) < parts:
            chunks.append("")
        return chunks[:parts]

    def _sanitize_duration(self, requested: int) -> int:
        if requested in self.ALLOWED_DURATIONS:
            return requested
        lower_or_equal = [d for d in self.ALLOWED_DURATIONS if d <= requested]
        if lower_or_equal:
            chosen = max(lower_or_equal)
        else:
            chosen = min(self.ALLOWED_DURATIONS)
        logger.warning(
            "Duração %s não suportada. Utilizando %s segundos (valores aceitos: %s).",
            requested,
            chosen,
            ", ".join(str(d) for d in self.ALLOWED_DURATIONS),
        )
        return chosen

    def _sanitize_size(self, requested: str) -> str:
        normalized = requested.strip().lower()
        if normalized in self.ALLOWED_SIZES:
            return normalized
        logger.warning(
            "Resolução '%s' não suportada. Utilizando '%s' (opções: %s).",
            requested,
            self.ALLOWED_SIZES[0],
            ", ".join(self.ALLOWED_SIZES),
        )
        return self.ALLOWED_SIZES[0]


def build_sora_service() -> SoraVideoService:
    return SoraVideoService()


try:
    sora_video_service = SoraVideoService()
except Exception as exc:
    logger.warning("SoraVideoService indisponível: %s", exc)
    sora_video_service = None
