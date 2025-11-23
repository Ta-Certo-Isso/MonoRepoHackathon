import datetime as dt
import json
import random

import pandas as pd

# --- Importação da função de classificação Groq (Renomeada no seu script para IA_Gen_analiser) ---

# --- Lista de DDDs Comuns no Brasil (Substitui a geração geográfica do Faker) ---
# Inclui DDDs centrais de capitais e grandes regiões
DDDS_BRASIL = ["11", "19", "21", "31", "41", "51", "61", "71", "81", "85", "92", "91"]

# --- Listas Aprimoradas de Respostas (Mantidas para consistência) ---

RESPOSTAS_CONCORDANCIA = [
    "Essa lei é excelente, concordo plenamente com a proposta. Finalmente algo que nos beneficia!",
    "Sim, concordo. A explicação da IA foi cristalina e a lei parece ser muito necessária.",
    "Acho que a explicação simplificada ajudou a entender. Dou um 'joinha' pra essa lei!",
    "Perfeito! Não vejo pontos negativos. Concordo 100%.",
    "Estou totalmente de acordo. É um avanço para o país.",
]

RESPOSTAS_DISCORDANCIA = [
    "Não concordo. Achei a explicação vaga e a lei pode ter efeitos colaterais negativos.",
    "Discordo totalmente. Parece que essa lei só vai complicar ainda mais as coisas.",
    "Apesar da explicação da IA, não me convenceu. Não concordo com o texto final.",
    "Achei ruim. Acredito que o governo deveria focar em outras prioridades, não concordo com essa lei.",
    "Infelizmente, não estou de acordo. É uma medida que não resolve o problema principal.",
]

RESPOSTAS_NEUTRAS = [
    "Entendi, mas ainda estou em cima do muro. Não sei se concordo ou discordo.",
    "A explicação foi boa, mas preciso pesquisar mais. Minha avaliação é neutra.",
    "É uma faca de dois gumes. Não concordo nem discordo, vamos ver no que dá.",
    "Ficou claro, mas o impacto prático ainda é incerto. Prefiro não opinar agora.",
    "Agradeço a explicação. Não tenho uma opinião forte o suficiente para concordar ou discordar.",
]

# --- Funções Auxiliares (Mantidas) ---


def gerar_interacao_usuario_aprimorada(artigo_lei):
    """Gera uma interação user/assistant simplificada e variada sobre a lei."""

    explicacao_ia = (
        f"Em resumo, o '{artigo_lei}' significa que agora você tem "
        f"{random.choice(['mais tempo para pagar', 'novos direitos à informação', 'isenção de alguma taxa', 'melhor acesso a serviços'])}. "
        f"É uma mudança que torna as coisas {random.choice(['mais fáceis e justas', 'mais transparentes', 'mais rápidas para todos'])}."
    )

    tom = random.choice(["concordancia", "discordancia", "neutra"])

    if tom == "concordancia":
        resposta_usuario = random.choice(RESPOSTAS_CONCORDANCIA)
    elif tom == "discordancia":
        resposta_usuario = random.choice(RESPOSTAS_DISCORDANCIA)
    else:
        resposta_usuario = random.choice(RESPOSTAS_NEUTRAS)

    conversa = [
        {
            "role": "assistant",
            "content": f"O novo **{artigo_lei}** foi aprovado! O que isso muda na prática? "
            + explicacao_ia,
        },
        {"role": "user", "content": resposta_usuario},
    ]
    return json.dumps(conversa, ensure_ascii=False)


def gerar_dados_mock(num_registros=35):
    """Gera o DataFrame com os dados mock, incluindo o DDD como único dado de localização."""

    dados = []

    leis_populares = [
        "Lei da Transparência de Custos Bancários (LTCB)",
        "Proposta de Emenda Constitucional (PEC) do Teletrabalho",
        "Marco Civil da Inteligência Artificial (MCIA)",
        "Revisão da Tabela de Imposto de Renda Pessoa Física (IRPF-2025)",
        "Lei de Proteção e Acesso a Medicamentos Raros (PAMER)",
    ]

    for _ in range(num_registros):
        # --- MUDANÇA: Sorteia um DDD aleatório do Brasil ---
        ddd_usuario = random.choice(DDDS_BRASIL)
        # ----------------------------------------------------

        artigo_lei = random.choice(leis_populares)

        dados.append(
            {
                # Apenas o DDD é mantido como dado de localização
                "DDD": ddd_usuario,
                "Artigo_Proposta_Lei": artigo_lei,
                "Interacao_usuario": gerar_interacao_usuario_aprimorada(artigo_lei),
                "anomesdia": int(dt.datetime.now().strftime("%Y%m%d")) - 1,
            }
        )

    return pd.DataFrame(dados)


# --- Execução do Script ---


def gerar_dados():
    # Gerar 50 registros mock (ajuste o número conforme necessário)
    df_mocks = gerar_dados_mock(num_registros=50)

    return df_mocks


print("✅ DataFrame Gerado com Sucesso! (Apenas DDD mantido)")

# Você pode então chamar o classificador de IA:
# df_classificado = classificar_acordo_openai(df_mocks)
# print(df_classificado.head())
