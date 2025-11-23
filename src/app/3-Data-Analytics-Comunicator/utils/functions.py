# Manipulação de sistema para ajustar paths de importação
import json
import os
import sys

import matplotlib.pyplot as plt
import pandas as pd

# Adiciona o caminho até a pasta que contém o configs.py no sys.path
sys.path.append(os.path.abspath("../"))

# chamando a função do módulo configs.py que mapeia as pastas no ambiente
import configs as cf

cf.mapeia_pastas()

from geodata import geodata_tb
from mock_dados import gerar_dados

dados_mockados = gerar_dados()
geodados = geodata_tb()
con = cf.criar_conexao_db()


# Função que recebe o nome de uma query e retorna o conteúdo do arquivo .sql correspondente
def ler_query(query_name):
    # Abre o arquivo .sql com o nome especificado em 'query_name' na pasta 'database'
    with open(f"../database/querys/{query_name}.sql", "r", encoding="utf-8") as file:
        sql_text = file.read()  # Lê o conteúdo do arquivo
        return sql_text  # Retorna o conteúdo do arquivo (a query SQL)


def ingestao(df_geo=geodados, df_interaction=dados_mockados):
    # Cria a conexão com o banco de dados usando a função criada no configs.py

    geo_loc = ler_query("tbl_geolocalizacao_orgs")
    usr_interact = ler_query("tbl_user_interactions")

    con.execute(geo_loc)
    con.execute(usr_interact)

    arquivos = {
        "geolocalizacao_orgs": geodados,
        "tbl_interacao_usuario": dados_mockados,
    }

    for nome in arquivos:
        con.register("temp", arquivos[nome])
        con.execute(f"INSERT INTO {nome} SELECT * FROM temp")
        con.unregister("temp")

    return True


def carregar_tabela_etl(nome_tabela):
    return con.execute(f"SELECT * FROM {nome_tabela}").df()


def NPS_populacao(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria a coluna 'Sentimento_Populacao' usando try/except para lidar com erros
    de tipo ou ausência de coluna durante a classificação das pontuações (0-10).
    """
    coluna_pontuacao = "Pontuacao Acordo (IA Gen)"

    try:
        if coluna_pontuacao not in df.columns:
            # Lança um erro se a coluna não for encontrada
            raise KeyError(f"A coluna '{coluna_pontuacao}' é necessária.")

        # Aplica a lógica de mapeamento de faixas, convertendo para int por segurança
        df["Sentimento_Populacao"] = df[coluna_pontuacao].apply(
            lambda score: (
                "Discorda Totalmente"
                if score >= 0 and score <= 3
                else "Discorda Parcialmente"
                if score == 4
                else "Neutro ou Incerteza"
                if score >= 5 and score <= 7
                else "Concorda Totalmente"
            )
        )

        print("✅ Coluna 'Sentimento_Populacao' criada com sucesso.")
        return df

    except KeyError as e:
        print(f"🚨 Erro de Coluna: {e}")
        return df
    except TypeError as e:
        print(
            f"🚨 Erro de Tipo de Dado: Verifique se a coluna '{coluna_pontuacao}' contém valores numéricos. Detalhe: {e}"
        )
        # Preenche com um valor de erro para não quebrar o DataFrame
        df["Sentimento_Populacao"] = "ERRO_TIPO"
        return df
    except Exception as e:
        print(f"🚨 Erro Inesperado durante a classificação do sentimento: {e}")
        return df


def join_classificado_x_geoloc(df_classificado, df_geoloc):
    """
    Realiza um merge left join entre dois DataFrames, garantindo que não haja
    duplicação de linhas de usuário no resultado final (relação 1:1).

    Args:
        df_classificado (pd.DataFrame): DataFrame principal (usuário) contendo a coluna 'DDD'.
        df_geoloc (pd.DataFrame): DataFrame geográfico contendo a coluna 'DDDs_Ativos'.

    Returns:
        pd.DataFrame: DataFrame com os dados do usuário cruzados com as informações geográficas.
    """

    # 1. PREPARAÇÃO: Garante que a coluna de DDDS_Ativos seja string e que esteja splitada
    df_geoloc_copy = df_geoloc.copy()
    df_geoloc_copy["DDDs_Split"] = (
        df_geoloc_copy["DDDs_Ativos"].astype(str).str.split(", ")
    )

    # 2. EXPLOSÃO: Cria uma linha para cada DDD individual na tabela geográfica
    df_exploded = df_geoloc_copy.explode("DDDs_Split")

    # 3. RENOMEAR CHAVE
    df_exploded = df_exploded.rename(columns={"DDDs_Split": "DDD_Chave"})

    # Garante que cada DDD individual (DDD_Chave) só apareça uma vez,
    df_exploded = df_exploded.drop_duplicates(subset=["DDD_Chave"], keep="first")

    # 4. SELECIONA COLUNAS E PREPARA O DATAFRAME PRINCIPAL
    colunas_geo_disponiveis = [
        col
        for col in [
            "Regiao",
            "UF",
            "Email_Ouvidoria",
            "DDDs_Ativos",
            "Email_Ouvidoria_CensoRecomendado",
            "Email_Gabinete_Referência",
            "Email_SEFAZ_Fazenda",
        ]
        if col in df_geoloc.columns
    ]
    colunas_geo = ["DDD_Chave"] + colunas_geo_disponiveis

    df_classificado["DDD_Chave"] = df_classificado["DDD"].astype(str)

    # 5. MERGE: Realiza o left join exato
    df_cruzado = pd.merge(
        df_classificado,
        df_exploded[colunas_geo],
        left_on="DDD_Chave",
        right_on="DDD_Chave",
        how="left",
    )

    # 6. LIMPEZA: Remove a coluna auxiliar
    df_cruzado = df_cruzado.drop(columns=["DDD_Chave"])

    return df_cruzado


def extrair_ultima_interacao(conversa_json):
    """
    Carrega a string JSON e retorna a 'content' da última interação na lista.
    """
    try:
        # 1. Carrega a string JSON em uma lista de dicionários Python
        conversa_list = json.loads(conversa_json)

        # 2. Acessa o ÚLTIMO item da lista e pega o valor de 'content'.
        # Na sua estrutura [assistente, usuário], o último item é a resposta do usuário.
        ultima_interacao = conversa_list[-1]["content"]

        return ultima_interacao

    except (json.JSONDecodeError, IndexError, TypeError, KeyError):
        # Lida com strings JSON inválidas ou estruturas ausentes
        return None  # Retorna None se a extração falhar


import pandas as pd


def gerar_graficos_sentimento(
    df_agrupado: pd.DataFrame,
    coluna_contagem: str = "Interacao_usuario",
    nome_arquivo: str = None,
    # Mantido o DPI padrão para e-mail
    dpi_output: int = 150,
):
    """
    Gera três gráficos de pizza lado a lado com DIMENSÃO REDUZIDA,
    e garante o salvamento em formato JPEG para menor tamanho de arquivo.
    """

    # 1. PREPARAÇÃO DE DADOS (omitido para brevidade)
    df_analise = df_agrupado.rename(columns={coluna_contagem: "Contagem"})
    sentimentos = ["Concorda Totalmente", "Discorda Totalmente", "Neutro ou Incerteza"]

    todas_as_leis = df_analise["Artigo_Proposta_Lei"].unique()
    cores = plt.cm.get_cmap("Set3", len(todas_as_leis))
    mapeamento_cores = {lei: cores(i) for i, lei in enumerate(todas_as_leis)}

    def autopct_format(values):
        def my_format(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return f"{pct:.1f}%\n({val} resp)"

        return my_format

    # 2. CONFIGURAÇÃO DE PLOTAGEM
    plt.style.use("seaborn-v0_8-whitegrid")
    # AJUSTE CHAVE: REDUÇÃO DO TAMANHO DA FIGURA (24x10 para 16x7)
    fig, axes = plt.subplots(1, 3, figsize=(16, 7))
    fig.suptitle(
        "Distribuição das Leis por Categoria de Sentimento da População",
        # Fonte reduzida
        fontsize=16,
        y=1.05,
        fontweight="bold",
    )

    # 3. GERAÇÃO DOS GRÁFICOS
    for i, sentimento in enumerate(sentimentos):
        df_slice = df_analise[df_analise["Sentimento_Populacao"] == sentimento].copy()

        if df_slice.empty:
            axes[i].text(0.5, 0.5, "Sem dados", ha="center", va="center", fontsize=12)
            axes[i].set_title(sentimento, fontsize=14)
            axes[i].axis("off")
            continue

        labels = df_slice["Artigo_Proposta_Lei"]
        sizes = df_slice["Contagem"]
        set_colors = [mapeamento_cores[label] for label in labels]

        axes[i].pie(
            sizes,
            labels=None,
            autopct=autopct_format(sizes),
            startangle=90,
            colors=set_colors,
            # Tamanho da fonte reduzido
            textprops={"fontsize": 10, "fontweight": "bold"},
            wedgeprops={"edgecolor": "gray", "linewidth": 0.8, "antialiased": True},
        )
        # Tamanho do título do subplot reduzido
        axes[i].set_title(f"{sentimento}", fontsize=18, fontweight="semibold")
        axes[i].axis("equal")

    # 4. POSICIONAMENTO DA LEGENDA
    legend_handles = [
        plt.Rectangle((0, 0), 1, 1, fc=mapeamento_cores[lei]) for lei in todas_as_leis
    ]
    fig.legend(
        legend_handles,
        todas_as_leis,
        title="Artigo / Proposta de Lei",
        loc="lower center",
        bbox_to_anchor=(0.5, -0.05),
        ncol=3,
        fontsize=10,  # Fonte da legenda reduzida
        title_fontsize=12,  # Fonte do título da legenda reduzida
        frameon=False,
    )
    # Ajuste do layout para figura menor
    plt.subplots_adjust(top=0.85, bottom=0.20, wspace=0.2)

    # 5. --- AÇÃO DE SALVAMENTO (GARANTINDO JPEG) ---
    if nome_arquivo:
        try:
            # 1. Garante que a extensão seja .jpg para usar 'quality'
            nome_arquivo_final = nome_arquivo.replace(".png", ".jpg")

            # 2. Salva como JPEG com compressão
            plt.savefig(
                nome_arquivo_final,
                bbox_inches="tight",
                dpi=dpi_output,  # Usa 150 DPI padrão para bom equilíbrio
                quality=90,
            )
            print(f"\n✅ Gráfico salvo com sucesso em: {nome_arquivo_final}")
        except Exception as e:
            # Fallback para salvar como PNG, caso haja erro com o backend JPEG
            print(f"\n🚨 Erro ao salvar como JPG ({e}). Tentando salvar como PNG...")
            plt.savefig(nome_arquivo, bbox_inches="tight", dpi=dpi_output)
            print(f"✅ Gráfico salvo como PNG: {nome_arquivo}")

    plt.show()
