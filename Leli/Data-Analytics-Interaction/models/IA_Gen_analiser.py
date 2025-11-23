import json
import os
import re
import time

import pandas as pd
from dotenv import load_dotenv  # Importa a função
from openai import APIError, OpenAI

load_dotenv()  # Carrega as variáveis do arquivo .env

# --- CONFIGURAÇÃO DA API OPENAI ---
MODEL_NAME = "gpt-4o-mini"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Inicializa o cliente da OpenAI
if not OPENAI_API_KEY:
    print(
        "🚨 ERRO DE CONFIGURAÇÃO: A variável de ambiente OPENAI_API_KEY não está definida."
    )
    print("A classificação não será realizada. Defina a variável para prosseguir.")
else:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ Cliente OpenAI inicializado com sucesso.")
    except Exception as e:
        print(f"🚨 ERRO ao inicializar o cliente OpenAI: {e}")


# --- FUNÇÃO DE CLASSIFICAÇÃO COM IA GENERATIVA (OPENAI) ---


def chamar_api_openai_para_classificar(texto_usuario: str) -> int:
    """
    Chama a API da OpenAI (GPT-4o-mini) para obter uma classificação de 0 a 10.
    """
    # Verifica se o cliente foi inicializado (se a chave da API estava presente)
    if client is None:
        return 5  # Retorna neutro (5) se a API não estiver configurada

    # O Prompt é adaptado para ser mais rígido na solicitação de APENAS o número
    prompt = f"""
    Sua tarefa é classificar o sentimento de concordância do usuário em relação à lei em uma escala estritamente numérica de 0 a 10 (sem decimal).

    Regras da Pontuação:
    0 a 3: Discordância Total (Ex: "Discordo totalmente", "Péssima ideia")
    4:  Discordância parcial (Ex: "Discordo totalmente", "Péssima ideia")
    8 a 10: Concordância Total (Ex: "Concordo plenamente", "Excelente", "100% de acordo")
    5 a 7: Neutro/Incerteza (Ex: "Não sei avaliar", "Estou em cima do muro")

    Analise o texto do usuário e retorne **SOMENTE** o número da pontuação entre (0 a 10). Nenhuma palavra extra, explicação ou formatação.

    Texto do Usuário: "{texto_usuario}"
    """

    # --- CHAMADA À API ---
    try:
        chat_completion = client.chat.completions.create(  # Esta linha agora é segura
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_NAME,
            temperature=0.0,
        )

        response_text = chat_completion.choices[0].message.content.strip()
        scores_found = re.findall(r"\b\d{1,2}\b", response_text)

        if scores_found:
            score = int(scores_found[0])
            return max(0, min(10, score))
        else:
            print(
                f"Erro no Parsing: IA não retornou um número válido. Resposta: {response_text[:50]}..."
            )
            return 5

    except APIError as e:
        print(f"Erro na API da OpenAI: {e}")
        return 5
    except Exception as e:
        print(f"Erro inesperado durante a chamada: {e}")
        return 5


def classificar_acordo_openai(df: pd.DataFrame) -> pd.DataFrame:
    # A lógica desta função permanece a mesma, mas ela agora chama a função
    # de classificação corrigida e segura.
    pontuacoes = []

    if client is None:
        print(
            "[CLASSIFICADOR IA GENERATIVA] Pulando classificação. Chave da API ausente ou inválida."
        )
        df["Pontuacao Acordo (IA Gen)"] = [5] * len(df)  # Preenche com neutro
        return df

    print(
        f"\n[CLASSIFICADOR IA GENERATIVA] Iniciando classificação via API OpenAI ({MODEL_NAME})..."
    )

    for index, row in df.iterrows():
        interacao_json = row["Interacao_usuario"]
        texto_usuario = ""

        try:
            conversa = json.loads(interacao_json)
            texto_usuario = conversa[1]["content"]
        except (json.JSONDecodeError, IndexError, KeyError):
            pass

        score = chamar_api_openai_para_classificar(texto_usuario)
        pontuacoes.append(score)

        time.sleep(0.3)

    df["Pontuacao Acordo (IA Gen)"] = pontuacoes
    print("[CLASSIFICADOR IA GENERATIVA] Classificação concluída.")
    return df
