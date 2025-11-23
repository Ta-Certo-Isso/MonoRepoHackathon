import os
from datetime import datetime

import pandas as pd
import yagmail

# --- VARIÁVEIS DE CONFIGURAÇÃO (Ajuste sua senha aqui) ---
EMAIL_REMETENTE = "tacertoisso.censo@gmail.com"
SENHA_EMAIL = "oazy fank oznv uwtr"
DESTINATARIO_FINAL = [
    "lelicontato@gmail.com",
    "lucas.correia.sas@gmail.com",
    "gabriel-nichols@hotmail.com",
]
NOME_ARQUIVO_GRAFICO = "relatorio_sentimento.jpg"
NOME_ARQUIVO_ANEXO = "df_attachment.csv"
ASSUNTO_EMAIL = (
    f"Relatório de Sentimento da População - {datetime.now().strftime('%Y-%m-%d')}"
)


# ==============================================================================
# FUNÇÃO AUXILIAR: CRIAÇÃO DA TABELA HTML PURA (DEVE FICAR FORA DA FUNÇÃO PRINCIPAL)
# ==============================================================================
def criar_tabela_html_pura(df_preview: pd.DataFrame) -> str:
    """Gera o HTML da tabela usando loops puros para controle total do CSS inline."""

    html = '<table width="100%" border="0" cellpadding="0" cellspacing="0" style="border-collapse: collapse; border: 1px solid #ccc; font-size: 12px; table-layout: fixed;">'

    # Cabeçalho da tabela (TH)
    html += "<thead><tr>"
    for col in df_preview.columns:
        html += f'<th style="background-color: #f5f5f5; color: #555; padding: 10px 5px; border: 1px solid #ccc; font-weight: bold; text-align: center;">{col.replace("_", " ")}</th>'
    html += "</tr></thead>"

    # Corpo da tabela (TD)
    html += "<tbody>"
    for index, row in df_preview.iterrows():
        html += "<tr>"
        for col in df_preview.columns:
            valor = str(row[col])
            # Estilo simples para as células
            html += f'<td style="padding: 8px; border: 1px solid #ccc; text-align: center; vertical-align: middle; word-wrap: break-word;">{valor}</td>'
        html += "</tr>"
    html += "</tbody>"
    html += "</table>"
    return html


# ==============================================================================
# FUNÇÃO PRINCIPAL: ENVIO DE EMAIL (Corrigida)
# ==============================================================================
def enviar_email_relatorio(df_cruzado_final: pd.DataFrame):
    print("Iniciando envio de E-mail.")

    caminho_grafico = NOME_ARQUIVO_GRAFICO
    caminho_anexo = NOME_ARQUIVO_ANEXO
    anexo_csv_criado = False
    attachments_list = []  # Inicializa a lista de anexos

    # 1. PREPARAÇÃO DE ARQUIVOS
    try:
        df_cruzado_final.to_csv(caminho_anexo, index=False, encoding="utf-8")
        anexo_csv_criado = True
    except Exception as e:
        print(f"🚨 Erro ao salvar o anexo CSV no disco: {e}")

    # 2. PRÉ-VISUALIZAÇÃO DE DADOS (CRIAÇÃO DO df_preview)
    # ESTE BLOCO DEFINE df_preview E DEVE OCORRER ANTES DO HTML
    colunas_preview = [
        "Artigo_Proposta_Lei",
        "Sentimento_Populacao",
        "UF",
        "Regiao",
        "DDD",
        "Ultima_Interacao_Usuario",
    ]
    colunas_existentes = [
        col for col in colunas_preview if col in df_cruzado_final.columns
    ]

    estado = "SP"
    # df_cruzado_final = df_cruzado_final[df_cruzado_final['UF'] == estado]

    df_preview = (
        df_cruzado_final[colunas_existentes]
        .copy()
        .rename(columns={"Ultima_Interacao_Usuario": "quantidade de respostas"})
    )

    df_preview1 = (
        df_preview.groupby(["Artigo_Proposta_Lei", "Sentimento_Populacao"])
        .agg({"quantidade de respostas": "count"})
        .reset_index()
        .sort_values("Artigo_Proposta_Lei")
    )
    df_preview2 = (
        df_preview1.rename(columns={"quantidade de respostas": "soma respostas"})
        .groupby(["Artigo_Proposta_Lei"])
        .agg({"soma respostas": "sum"})
        .reset_index()
        .sort_values("Artigo_Proposta_Lei")
    )

    df_preview3 = pd.merge(
        df_preview1, df_preview2, how="left", on="Artigo_Proposta_Lei"
    )
    df_preview3["%"] = round(
        (df_preview3["quantidade de respostas"] / df_preview3["soma respostas"]) * 100,
        1,
    )

    df_preview = df_preview3[["Artigo_Proposta_Lei", "Sentimento_Populacao", "%"]]
    df_preview = (
        df_preview.dropna(subset=["Artigo_Proposta_Lei", "Sentimento_Populacao", "%"])
        .head(10)
        .fillna("")
    )

    # GERAÇÃO DA TABELA HTML (ARAMAZENA O RESULTADO NA VARIÁVEL)
    tabela_html = criar_tabela_html_pura(df_preview)

    # 3. PREPARAÇÃO FINAL DE ANEXOS E IMAGEM INLINE

    # A) Prepara Imagem para inline (CID)
    if os.path.exists(caminho_grafico):
        # 1. Cria o objeto inline e o adiciona à lista de anexos
        imagem_objeto = yagmail.inline(caminho_grafico)
        attachments_list.append(imagem_objeto)

        # 2. Define a tag HTML <img> com o objeto inline no src
        imagem_tag = f'<img src="{imagem_objeto}" alt="Gráfico de Sentimento" style="max-width: 200px; height: auto; border: 1px solid #ddd; display: block; margin: 0 auto;">'
    else:
        imagem_tag = "<strong>* GRÁFICO NÃO DISPONÍVEL *</strong>"

    # B) Adiciona o CSV como anexo
    if anexo_csv_criado:
        attachments_list.append(caminho_anexo)

    # --- CORPO HTML ---
    MENSAGEM_HTML = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.4; color: #333; margin: 0; background-color: #f9f9f9;">
        <table width="700" border="0" cellpadding="0" cellspacing="0" style="margin: 0 auto; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px;">
            <tr>
                <td style="padding: 30px;">
                    <h2 style="color: #2a6496; border-bottom: 2px solid #eee; padding-bottom: 15px; margin-top: 0;">Relatório de Análise de Sentimento Legislativo</h2>
                    
                    <p style="margin-bottom: 15px;">Prezado(a) Destinatário(a),</p>
                    
                    <p>Os dados abaixo resumem a Distribuição dos Artigos/Propostas de Lei por Sentimento da População de {estado}!</p>
                    
                    <p style="font-weight: bold; margin-bottom: 10px; margin-top: 25px; color: #444;">PRÉ-VISUALIZAÇÃO DOS DADOS (10 Primeiros Registros Válidos):</p>
                    
                    {tabela_html}

                    <p style="margin-top: 25px;">A base de dados completa está anexo neste e-mail no formato CSV (<code>{NOME_ARQUIVO_ANEXO}</code>).</p>

                    <p style="margin-top: 30px; font-size: 0.9em; color: #888;">
                        Atenciosamente,<br>
                        Sistema Automatizado de Análise.
                    </p>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    # 4. ENVIO DO EMAIL
    try:
        yag = yagmail.SMTP(EMAIL_REMETENTE, SENHA_EMAIL)

        yag.send(
            to=DESTINATARIO_FINAL,
            subject=ASSUNTO_EMAIL,
            contents=[MENSAGEM_HTML],
            attachments=attachments_list,
        )
        print(
            f"\n✅ E-mail de relatório enviado com sucesso para {DESTINATARIO_FINAL}!"
        )

    except Exception as e:
        print("🚨 Erro ao enviar e-mails:", e)

    finally:
        # Limpa os arquivos temporários (CSV e PNG)
        if os.path.exists(caminho_grafico):
            os.remove(caminho_grafico)
        if os.path.exists(caminho_anexo):
            os.remove(caminho_anexo)
