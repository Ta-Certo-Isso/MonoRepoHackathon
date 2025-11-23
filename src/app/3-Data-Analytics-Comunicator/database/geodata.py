import pandas as pd

# --- 1. Dicionário Mestre de Dados: DDDs e E-mails Governamentais por Região/Estado ---

# Nota: A coluna 'ouvidoria' é o contato mais adequado para censo/opinião pública.
dados_geopoliticos_br = {
    "Norte": {
        "AC": {
            "ddds": ["68"],
            "emails": {
                "ouvidoria": "ouvidoria@ac.gov.br",
                "gabinete": "gabgoverno@ac.gov.br",
                "sefaz": "sefaz@sefaz.ac.gov.br",
            },
        },
        "AP": {
            "ddds": ["96"],
            "emails": {
                "ouvidoria": "ouvidoria@ouvidoria.ap.gov.br",
                "gabinete": "gabinete@gap.ap.gov.br",
                "sefaz": "gabinete.sefaz@sefaz.ap.gov.br",
            },
        },
        "AM": {
            "ddds": ["92", "97"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.am.gov.br",
                "gabinete": "gabinete@cge.am.gov.br",
                "sefaz": "sefaz@sefaz.am.gov.br",
            },
        },
        "PA": {
            "ddds": ["91", "93", "94"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.pa.gov.br",
                "gabinete": "gabgoverno@pa.gov.br",
                "sefaz": "gabinete@sefa.pa.gov.br",
            },
        },
        "RO": {
            "ddds": ["69"],
            "emails": {
                "ouvidoria": "ouvidoriageral@cge.ro.gov.br",
                "gabinete": "gabgoverno@ro.gov.br",
                "sefaz": "ouvidoria@sefin.ro.gov.br",
            },
        },
        "RR": {
            "ddds": ["95"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.rr.gov.br",
                "gabinete": "gabinetegovernador@rr.gov.br",
                "sefaz": "faleconosco@sefaz.rr.gov.br",
            },
        },
        "TO": {
            "ddds": ["63"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.to.gov.br",
                "gabinete": "gabinetegovernador@to.gov.br",
                "sefaz": "sefaz@sefaz.to.gov.br",
            },
        },
    },
    "Nordeste": {
        "AL": {
            "ddds": ["82"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.al.gov.br",
                "gabinete": "gabinete@gab.al.gov.br",
                "sefaz": "atendimento@sefaz.al.gov.br",
            },
        },
        "BA": {
            "ddds": ["71", "73", "74", "75", "77"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.ba.gov.br",
                "gabinete": "gabinetegovernador@gov.ba.gov.br",
                "sefaz": "faleconosco@sefaz.ba.gov.br",
            },
        },
        "CE": {
            "ddds": ["85", "88"],
            "emails": {
                "ouvidoria": "ouvidoria.geral@cge.ce.gov.br",
                "gabinete": "gabinete@gabgov.ce.gov.br",
                "sefaz": "sefaz.atendimento@sefaz.ce.gov.br",
            },
        },
        "MA": {
            "ddds": ["98", "99"],
            "emails": {
                "ouvidoria": "ouvidoria.geral@cge.ma.gov.br",
                "gabinete": "gabinetecivil@cgc.ma.gov.br",
                "sefaz": "ouvidoria@sefaz.ma.gov.br",
            },
        },
        "PB": {
            "ddds": ["83"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.pb.gov.br",
                "gabinete": "gabinetedogovernador@gab.pb.gov.br",
                "sefaz": "sefaz_contato@sefaz.pb.gov.br",
            },
        },
        "PE": {
            "ddds": ["81", "87"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.pe.gov.br",
                "gabinete": "gabinetegovernador@pe.gov.br",
                "sefaz": "sefazpe@sefaz.pe.gov.br",
            },
        },
        "PI": {
            "ddds": ["86", "89"],
            "emails": {
                "ouvidoria": "ouvidoria.geral@cge.pi.gov.br",
                "gabinete": "gabgoverno@pi.gov.br",
                "sefaz": "sefaz@sefaz.pi.gov.br",
            },
        },
        "RN": {
            "ddds": ["84"],
            "emails": {
                "ouvidoria": "ouvidoriageral@rn.gov.br",
                "gabinete": "gabinetecivil@rn.gov.br",
                "sefaz": "sefaz@rn.gov.br",
            },
        },
        "SE": {
            "ddds": ["79"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.se.gov.br",
                "gabinete": "gabinetegovernador@se.gov.br",
                "sefaz": "sefaz@sefaz.se.gov.br",
            },
        },
    },
    "Centro-Oeste": {
        "DF": {
            "ddds": ["61"],
            "emails": {
                "ouvidoria": "ouvidoria@df.gov.br",
                "gabinete": "gabinete@buriti.df.gov.br",
                "sefaz": "falecomasefaz@economia.df.gov.br",
            },
        },
        "GO": {
            "ddds": ["62", "64"],
            "emails": {
                "ouvidoria": "ouvidoria.cge@goias.gov.br",
                "gabinete": "gabgov@goias.gov.br",
                "sefaz": "faleconosco@sefaz.go.gov.br",
            },
        },
        "MT": {
            "ddds": ["65", "66"],
            "emails": {
                "ouvidoria": "ouvidoria@controladoria.mt.gov.br",
                "gabinete": "gabinetegovernador@gabinete.mt.gov.br",
                "sefaz": "cits.sefaz@sefaz.mt.gov.br",
            },
        },
        "MS": {
            "ddds": ["67"],
            "emails": {
                "ouvidoria": "ouvidoria@ouvidoriageral.ms.gov.br",
                "gabinete": "gabinetecivil@gab.ms.gov.br",
                "sefaz": "faleconosco@sefaz.ms.gov.br",
            },
        },
    },
    "Sudeste": {
        "ES": {
            "ddds": ["27", "28"],
            "emails": {
                "ouvidoria": "ouvidoria@es.gov.br",
                "gabinete": "gabinete@es.gov.br",
                "sefaz": "faleconosco@sefaz.es.gov.br",
            },
        },
        "MG": {
            "ddds": ["31", "32", "33", "34", "35", "37", "38"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.mg.gov.br",
                "gabinete": "gabinetecivil@cge.mg.gov.br",
                "sefaz": "faleconosco@fazenda.mg.gov.br",
            },
        },
        "RJ": {
            "ddds": ["21", "22", "24"],
            "emails": {
                "ouvidoria": "ouvidoria@cge.rj.gov.br",
                "gabinete": "gabinete@gabgov.rj.gov.br",
                "sefaz": "sefaz@fazenda.rj.gov.br",
            },
        },
        # SP usa canal de comunicação direta/social para maior engajamento público, conforme combinado.
        "SP": {
            "ddds": ["11", "12", "13", "14", "15", "16", "17", "18", "19"],
            "emails": {
                "ouvidoria": "ouvidoria@sp.gov.br",
                "gabinete": "socialsaopaulo@sp.gov.br",
                "sefaz": "ouvidoria_sefaz@fazenda.sp.gov.br",
            },
        },
    },
    "Sul": {
        "PR": {
            "ddds": ["41", "42", "43", "44", "45", "46"],
            "emails": {
                "ouvidoria": "ouvidoriageral@cge.pr.gov.br",
                "gabinete": "gabinetegovernador@pr.gov.br",
                "sefaz": "atendimento@sefaz.pr.gov.br",
            },
        },
        "RS": {
            "ddds": ["51", "53", "54", "55"],
            "emails": {
                "ouvidoria": "ouvidoriageral@cge.rs.gov.br",
                "gabinete": "gabinetedogovernador@rs.gov.br",
                "sefaz": "atendimento@sefaz.rs.gov.br",
            },
        },
        "SC": {
            "ddds": ["47", "48", "49"],
            "emails": {
                "ouvidoria": "ouvidoriageral@cge.sc.gov.br",
                "gabinete": "gabinetecivil@sc.gov.br",
                "sefaz": "sef_atendimento@sef.sc.gov.br",
            },
        },
    },
}

# --- 2. Processamento dos Dados para o DataFrame ---

lista_dados = []

for regiao, estados in dados_geopoliticos_br.items():
    for uf, dados in estados.items():
        ddds_str = ", ".join(dados["ddds"])

        registro = {
            "DDDs_Ativos": ddds_str,
            "Regiao": regiao,
            "UF": uf,
            "Email_Ouvidoria_CensoRecomendado": dados["emails"]["ouvidoria"],
            "Email_Gabinete_Referência": dados["emails"]["gabinete"],
            "Email_SEFAZ_Fazenda": dados["emails"]["sefaz"],
        }
        lista_dados.append(registro)

# --- 3. Criação e Exibição do DataFrame ---


def geodata_tb():
    df_geopolitico = pd.DataFrame(lista_dados)
    return df_geopolitico


print(
    "✅ DataFrame criado com sucesso! Use a coluna 'Email Ouvidoria (Censo Recomendado)'."
)
