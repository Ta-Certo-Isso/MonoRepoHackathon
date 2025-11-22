import asyncio
from pathlib import Path

import pytest

from Nichols import main


def test_normalize_number_strips_suffix():
    assert main.normalize_number("5511999999999@s.whatsapp.net") == "5511999999999"
    assert main.normalize_number("5511888888888@c.us") == "5511888888888"
    assert main.normalize_number(None) == ""


def test_extract_text_prefers_direct_fields():
    block = {"text": " oi  "}
    assert main.extract_text(block) == "oi"

    block = {"message": {"conversation": "hello"}, "text": ""}
    assert main.extract_text(block) == "hello"

    block = {"message": {"extendedTextMessage": {"text": "extended"}}}
    assert main.extract_text(block) == "extended"

    block = {"message": {"imageMessage": {"caption": "img cap"}}}
    assert main.extract_text(block) == "img cap"

    block = {"message": {"videoMessage": {"caption": "vid cap"}}}
    assert main.extract_text(block) == "vid cap"

    assert main.extract_text({}) is None


def test_load_corpus_uses_first_line_as_title(tmp_path: Path):
    doc = tmp_path / "pl_2338.txt"
    doc.write_text("PL 2338/2023 – IA no Brasil\nlinha 2\nlinha 3", encoding="utf-8")

    docs = main.load_corpus(tmp_path)
    assert docs == [("pl_2338", "PL 2338/2023 – IA no Brasil", "linha 2\nlinha 3")]


@pytest.mark.asyncio
async def test_handle_tools_intents():
    assert "[INTENÇÃO: checagem_de_boato]" in await main.handle_tools(
        "É verdade isso é fake?"
    )
    assert "[INTENÇÃO: duvida_sobre_lei]" in await main.handle_tools(
        "PL 2338 fala sobre IA?"
    )
    assert "[INTENÇÃO: geral]" in await main.handle_tools("Olá, tudo bem?")
