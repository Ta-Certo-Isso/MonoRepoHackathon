"""
Coletor de Notícias usando Google Custom Search API
Adaptado para buscar notícias sobre legislação municipal/estadual
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from googleapiclient.discovery import build

# Caminho das credenciais (arquivo local na pasta Montoya)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "google-credentials.json")

# Carrega credenciais
try:
    with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
        creds = json.load(f)
    
    API_KEY = creds.get("search_api_key", "")
    SEARCH_ENGINE_ID = creds.get("search_engine_id", "")
    
    if not API_KEY or not SEARCH_ENGINE_ID:
        print("[AVISO] Credenciais do Google Search API nao encontradas no arquivo.")
        API_KEY = None
        SEARCH_ENGINE_ID = None
except FileNotFoundError:
    print(f"[AVISO] Arquivo de credenciais nao encontrado: {CREDENTIALS_PATH}")
    API_KEY = None
    SEARCH_ENGINE_ID = None
except Exception as e:
    print(f"[ERRO] Erro ao carregar credenciais: {e}")
    API_KEY = None
    SEARCH_ENGINE_ID = None

PERIODO_MAXIMO = 6  # meses

# Dicionário de tópicos e fontes confiáveis
TOPICOS_FONTES = {
    "tecnologia": [
        # Internacionais
        "gizmodo.com", "theverge.com", "wired.com", "bbc.com", "techcrunch.com",
        "arstechnica.com", "cnet.com", "recode.net", "zdnet.com", "computerworld.com",
        # Brasil
        "tecmundo.com.br", "canaltech.com.br", "olhardigital.com.br", "g1.globo.com/tecnologia"
    ],
    "política": [
        # Internacionais
        "bbc.com", "cnn.com", "nytimes.com", "theguardian.com", "reuters.com",
        "aljazeera.com", "washingtonpost.com", "bloomberg.com", "politico.com",
        # Brasil
        "g1.globo.com/politica", "folha.uol.com.br", "estadao.com.br", "uol.com.br",
        "valor.globo.com", "cartacapital.com.br", "oglobo.globo.com", "jornaldocommercio.com.br"
    ],
    "economia": [
        # Internacionais
        "bbc.com", "forbes.com", "businessinsider.com", "investing.com", "wsj.com",
        "bloomberg.com", "economist.com", "money.cnn.com", "financialtimes.com",
        # Brasil
        "valor.globo.com", "infomoney.com.br", "exame.com", "estadao.com.br/economia"
    ],
    "esportes": [
        # Internacionais
        "fifa.com", "uefa.com", "nba.com", "nfl.com", "mlb.com", "motorsport.com",
        "espn.com", "skysports.com", "bleacherreport.com", "foxsports.com",
        # Brasil
        "ge.globo.com", "espn.com.br", "lancenet.com.br", "cbf.com.br", "r7.com/esportes"
    ],
    "ciencia": [
        # Internacionais
        "nature.com", "sciencemag.org", "bbc.com", "nasa.gov", "smithsonianmag.com",
        "scientificamerican.com", "newscientist.com", "livescience.com", "phys.org", "pnas.org",
        # Brasil
        "g1.globo.com/ciencia", "revistagalileu.globo.com", "jornal.usp.br/ciencia"
    ],
    "entretenimento": [
        # Internacionais
        "rollingstone.com", "variety.com", "billboard.com", "hollywoodreporter.com",
        "deadline.com", "pitchfork.com", "mtv.com", "nme.com", "ew.com",
        # Brasil
        "g1.globo.com/pop-arte", "hugogloss.uol.com.br", "contigo.uol.com.br", "caras.uol.com.br"
    ],
    "jogos": [
        # Internacionais
        "ign.com", "kotaku.com", "polygon.com", "pcgamer.com", "rockpapershotgun.com",
        "gamespot.com", "eurogamer.net", "nintendolife.com", "playstationlifestyle.net", "xbox.com",
        # Brasil
        "meups.com.br", "adrenaline.com.br", "tecmundo.com.br/jogos", "theenemy.com.br"
    ],
    "saúde": [
        # Internacionais
        "who.int", "cdc.gov", "bmj.com", "nejm.org", "thelancet.com",
        "medscape.com", "mayo.edu", "healthline.com",
        # Brasil
        "g1.globo.com/saude", "drauziovarella.uol.com.br", "fiocruz.br", "abramge.com.br"
    ],
    "educação": [
        # Internacionais
        "edutopia.org", "khanacademy.org", "education.com", "bbc.com/education", "npr.org/sections/ed",
        "theconversation.com", "timeshighereducation.com", "insidehighered.com", "forbes.com/education",
        # Brasil
        "novaescola.org.br", "g1.globo.com/educacao", "mec.gov.br", "jornal.usp.br/educacao"
    ],
    "finanças pessoais": [
        # Internacionais
        "forbes.com", "money.cnn.com", "thebalance.com", "nerdwallet.com",
        "investopedia.com", "businessinsider.com", "bloomberg.com", "wsj.com",
        # Brasil
        "exame.com", "valor.globo.com", "infomoney.com.br", "meusucesso.com"
    ],
    "automóveis": [
        # Internacionais
        "motor1.com", "caranddriver.com", "autocar.co.uk", "topgear.com", "autosport.com",
        "motortrend.com", "carscoops.com", "insideevs.com",
        # Brasil
        "autoesporte.com.br", "quatrorodas.abril.com.br", "noticiasautomotivas.com.br"
    ],
    "segurança cibernética": [
        # Internacionais
        "krebsonsecurity.com", "threatpost.com", "wired.com", "arstechnica.com/security",
        "darkreading.com", "cyberscoop.com", "securityweek.com", "zdnet.com/security", "scmagazine.com",
        # Brasil
        "tecmundo.com.br/seguranca", "olhardigital.com.br/seguranca", "canaltech.com.br/seguranca"
    ],
    "astronomia": [
        # Internacionais
        "nasa.gov", "space.com", "esa.int", "skyandtelescope.org", "universetoday.com",
        "earthsky.org", "phys.org/space-news", "livescience.com/space", "scientificamerican.com/space",
        # Brasil
        "revistagalileu.globo.com/espaco", "g1.globo.com/ciencia/espaco", "inpe.br"
    ],
    "meio ambiente": [
        # Internacionais
        "nationalgeographic.com/environment", "bbc.com/environment",
        "nature.com/natureclimatechange", "mongabay.com", "theguardian.com/environment",
        "unep.org", "carbonbrief.org", "climatecentral.org",
        # Brasil
        "g1.globo.com/natureza", "oeco.org.br", "socioambiental.org", "revistagalileu.globo.com/meio-ambiente"
    ],
    "inteligência artificial": [
        # Internacionais
        "arxiv.org", "openai.com/blog", "deeplearning.ai", "towardsdatascience.com", "wired.com",
        "venturebeat.com/ai", "forbes.com/ai", "syncedreview.com", "techcrunch.com/artificial-intelligence",
        # Brasil
        "tecmundo.com.br/ia", "canaltech.com.br/ia", "olhardigital.com.br/inteligencia-artificial"
    ],
    "fofocas": [
        # Internacionais
        "tmz.com", "people.com", "usmagazine.com", "eonline.com", "perezhilton.com",
        "justjared.com", "theblast.com", "pagesix.com", "radaronline.com", "hollywoodlife.com",
        # Brasil
        "gshow.globo.com", "hugogloss.uol.com.br", "contigo.uol.com.br", "metropoles.com/colunas/pipocando",
        "ofuxico.com.br", "caras.uol.com.br", "revistaquem.globo.com", "emoff.ig.com.br", "tvefamosos.uol.com.br"
    ],
    "crimes": [
        # Internacionais
        "bbc.com", "cnn.com", "nytimes.com", "theguardian.com", "reuters.com",
        "foxnews.com", "aljazeera.com", "npr.org", "apnews.com",
        # Brasil
        "g1.globo.com/policia", "folha.uol.com.br/cotidiano", "estadao.com.br", "uol.com.br/noticias",
        "metropoles.com/brasil", "r7.com/noticias/policia", "extra.globo.com/casos-de-policia",
        "correiobraziliense.com.br", "jovempan.com.br/noticias/brasil", "diariodonordeste.verdesmares.com.br/seguranca"
    ],
    "legislacao": [
        # Fontes confiáveis e acessíveis (testadas em testar_fontes.py)
        "g1.globo.com",                    # G1 - Globo
        "folha.uol.com.br",                # Folha de S.Paulo
        "estadao.com.br",                  # Estadão
        "oglobo.globo.com",                # O Globo
        "uol.com.br",                      # UOL
        "cartacapital.com.br",             # CartaCapital
        "jornaldocommercio.com.br",        # Jornal do Comércio
        "portalvale.com.br"                # Portal Vale (regional SP)
        # Removidas (não acessíveis):
        # "valor.globo.com" - erro de conexão
        # "jornalovale.com.br" - erro de conexão
    ]
}

def is_recent(news_date_str: str, dias_maximos: int = 30) -> bool:
    """
    Verifica se a notícia é recente
    
    Args:
        news_date_str: Data da notícia no formato "YYYY-MM-DD"
        dias_maximos: Quantos dias atrás considerar como recente
        
    Returns:
        True se a notícia for recente, False caso contrário
    """
    if not news_date_str:
        return True
    try:
        date_obj = datetime.strptime(news_date_str, "%Y-%m-%d")
        limite = datetime.today() - timedelta(days=dias_maximos)
        return date_obj >= limite
    except ValueError:
        # Tenta outros formatos de data
        try:
            # Formato ISO com hora
            date_obj = datetime.fromisoformat(news_date_str.replace('Z', '+00:00'))
            limite = datetime.today() - timedelta(days=dias_maximos)
            return date_obj >= limite
        except:
            return True

def extrair_texto(link: str, max_chars: int = 2000) -> str:
    """
    Pega HTML da página e retorna texto limpo com no máximo max_chars caracteres.
    
    Args:
        link: URL da notícia
        max_chars: Número máximo de caracteres a retornar
        
    Returns:
        Texto extraído da página
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = requests.get(link, timeout=10, headers=headers)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # Remove scripts e estilos
        for s in soup(["script", "style", "nav", "footer", "header"]):
            s.extract()
        
        # Tenta encontrar o conteúdo principal
        artigo = soup.find('article') or soup.find('main') or soup.find('div', class_=lambda x: x and 'content' in str(x).lower())
        if artigo:
            text = artigo.get_text(separator=" ")
        else:
            text = soup.get_text(separator=" ")
        
        # Limpa espaços múltiplos
        text = " ".join(text.split())
        
        # Limita o tamanho
        return text[:max_chars]
    except Exception as e:
        print(f"[ERRO] Erro ao extrair conteudo de {link}: {e}")
        return ""

def buscar_noticias(
    termo: str, 
    topico: str = "legislacao",
    dias_maximos: int = 30,
    limite: int = 10,
    extrair_conteudo: bool = True
) -> List[Dict]:
    """
    Busca notícias usando Google Custom Search API
    
    Args:
        termo: Termo de busca (ex: "câmara municipal Vale do Paraíba")
        topico: Tópico para filtrar fontes (padrão: "legislacao")
        dias_maximos: Quantos dias atrás buscar (padrão: 30)
        limite: Quantidade máxima de resultados (padrão: 10)
        extrair_conteudo: Se deve extrair conteúdo completo das páginas
        
    Returns:
        Lista de notícias encontradas
    """
    if not API_KEY or not SEARCH_ENGINE_ID:
        print("[ERRO] Credenciais do Google Search API nao configuradas.")
        return []
    
    fontes = TOPICOS_FONTES.get(topico.lower(), [])
    if not fontes:
        print(f"[AVISO] Topico '{topico}' nao reconhecido. Usando 'legislacao'.")
        fontes = TOPICOS_FONTES.get("legislacao", TOPICOS_FONTES["política"])

    # Usa todas as fontes acessíveis testadas
    sites = " OR ".join([f"site:{fonte}" for fonte in fontes])
    query = f"{termo} ({sites})"
    
    try:
        service = build("customsearch", "v1", developerKey=API_KEY)
        
        print(f"Buscando noticias: '{termo}' (topico: {topico})...")
        res = service.cse().list(
            q=query, 
            cx=SEARCH_ENGINE_ID, 
            num=min(limite, 10),  # Google limita a 10 por requisição
            sort="date"
        ).execute()
        
        if "items" not in res:
            print("Nenhuma noticia encontrada.")
            return []

        noticias = []
        for item in res["items"]:
            # Extrai data da notícia
            news_date = item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time", "")
            news_date = news_date[:10] if news_date else ""
            
            # Filtra por data se especificado
            if dias_maximos > 0 and not is_recent(news_date, dias_maximos):
                continue

            noticia = {
                "titulo": item["title"],
                "link": item["link"],
                "descricao": item.get("snippet", ""),
                "data": news_date,
                "fonte": "Google Search",
                "tipo": "noticia",
                "nivel": _detectar_nivel(item["title"] + " " + item.get("snippet", ""))
            }
            
            # Extrai conteúdo completo se solicitado
            if extrair_conteudo:
                noticia["conteudo"] = extrair_texto(noticia["link"], max_chars=2000)
            
            noticias.append(noticia)
            
            if len(noticias) >= limite:
                break

        print(f"[OK] Encontradas {len(noticias)} noticias")
        return noticias

    except Exception as e:
        print(f"[ERRO] Erro na pesquisa de noticias: {e}")
        return []


def _detectar_nivel(texto: str) -> str:
    """
    Detecta o nível da notícia (federal, estadual, municipal)
    
    Args:
        texto: Texto da notícia
        
    Returns:
        'federal', 'estadual', 'municipal' ou 'desconhecido'
    """
    texto_lower = texto.lower()
    
    if any(palavra in texto_lower for palavra in ['congresso', 'senado', 'câmara dos deputados', 'federal', 'brasília']):
        return 'federal'
    elif any(palavra in texto_lower for palavra in ['assembleia', 'alesp', 'estadual', 'governo do estado', 'sp']):
        return 'estadual'
    elif any(palavra in texto_lower for palavra in ['câmara municipal', 'prefeitura', 'vereador', 'municipal', 'prefeito']):
        return 'municipal'
    else:
        return 'desconhecido'


def buscar_noticias_legislacao(
    regiao: str = "Vale do Paraíba",
    dias_atras: int = 30,
    limite: int = 10
) -> List[Dict]:
    """
    Busca notícias sobre legislação na região especificada
    Foca em sites de notícias (G1, Folha, etc) que reportam sobre legislação,
    evitando links diretos para sites de câmaras municipais
    
    Args:
        regiao: Região de interesse (ex: "Vale do Paraíba", "São Paulo")
        dias_atras: Quantos dias atrás buscar
        limite: Quantidade máxima de resultados
        
    Returns:
        Lista de notícias sobre legislação
    """
    todas_noticias = []
    
    # Queries específicas para legislação - foca em notícias, não sites oficiais
    # Inclui cidades específicas do Vale do Paraíba para melhor precisão
    cidades_vale = ["São José dos Campos", "Taubaté", "Jacareí", "Guaratinguetá", 
                    "Pindamonhangaba", "Caçapava", "Lorena", "Cruzeiro"]
    
    # Usa todas as fontes acessíveis (não apenas G1)
    sites_query = " OR ".join([f"site:{f}" for f in [
        "g1.globo.com", "folha.uol.com.br", "estadao.com.br",
        "oglobo.globo.com", "uol.com.br", "cartacapital.com.br",
        "jornaldocommercio.com.br", "portalvale.com.br"
    ]])
    
    queries = [
        f'"{regiao}" "projeto de lei" "câmara municipal" ({sites_query})',
        f'"{regiao}" "vereadores" "aprova" ({sites_query})',
        f'"{regiao}" "IPTU" "câmara" ({sites_query})',
        f'"{regiao}" "lei municipal" ({sites_query})',
    ]
    
    # Adiciona queries com cidades específicas
    for cidade in cidades_vale[:3]:  # Limita a 3 cidades para não exceder rate limits
        queries.append(f'"{cidade}" "projeto de lei" "câmara" ({sites_query})')
    
    for query in queries[:4]:  # Limita para não exceder rate limits
        noticias = buscar_noticias(
            termo=query,
            topico="legislacao",
            dias_maximos=dias_atras,
            limite=5,
            extrair_conteudo=True  # Extrai conteúdo completo das notícias
        )
        
        # Filtra para evitar links diretos de câmaras municipais e focar na região
        noticias_filtradas = []
        for noticia in noticias:
            url = noticia.get("link", "").lower()
            titulo = noticia.get("titulo", "").lower()
            descricao = noticia.get("descricao", "").lower()
            texto_completo = f"{titulo} {descricao}"
            
            # Aceita apenas fontes acessíveis testadas
            sites_aceitos = [
                "g1.globo.com", "folha.uol.com.br", "estadao.com.br",
                "oglobo.globo.com", "uol.com.br", "cartacapital.com.br",
                "jornaldocommercio.com.br", "portalvale.com.br"
            ]
            eh_site_noticia = any(site in url for site in sites_aceitos)
            
            # Filtra por SP (São Paulo) - verifica na URL do G1
            # G1 usa padrão: g1.globo.com/sp/... ou g1.globo.com/sp/vale-do-paraiba...
            # Verifica se contém /sp/ na URL (não /rj/, /am/, etc)
            eh_sp = "/sp/" in url
            nao_eh_sp = any(f"/{estado}/" in url for estado in ["rj", "am", "pi", "ba", "mg", "pr", "sc", "rs"])
            
            # Exclui links diretos para sites de câmaras (mesmo que sejam de sites de notícias)
            palavras_excluir_url = [
                "/sapl", "/proposicoes", "/materias", "/vereadores",
                "camara.gov.br", "camaras.gov.br"
            ]
            
            eh_link_camara_direto = any(palavra in url for palavra in palavras_excluir_url)
            
            # Prioriza notícias que mencionam a região ou cidades do Vale do Paraíba
            regiao_lower = regiao.lower()
            cidades_vale_lower = [c.lower() for c in ["são josé", "taubaté", "jacareí", 
                                                      "guaratinguetá", "pindamonhangaba", 
                                                      "caçapava", "lorena", "cruzeiro", "pinda"]]
            
            # Verifica se menciona região na URL (mais confiável)
            url_contem_regiao = "vale-do-paraiba" in url or any(cidade.replace(" ", "-") in url or cidade in url for cidade in cidades_vale_lower)
            texto_contem_regiao = regiao_lower in texto_completo or any(cidade in texto_completo for cidade in cidades_vale_lower)
            menciona_regiao = url_contem_regiao or texto_contem_regiao
            
            if eh_site_noticia and not eh_link_camara_direto:
                # Se for G1, só aceita se for de SP
                if "g1.globo.com" in url:
                    if nao_eh_sp or not eh_sp:
                        continue  # Pula notícias do G1 que não são de SP
                
                # Se estamos buscando por região específica, prioriza muito as notícias da região
                if regiao and regiao != "Brasil":
                    if menciona_regiao:
                        noticia['relevancia'] = 10  # Alta relevância
                        noticias_filtradas.insert(0, noticia)  # Insere no início
                    elif eh_sp:
                        # Notícias de SP mas não da região específica
                        noticia['relevancia'] = 7
                        noticias_filtradas.append(noticia)
                    else:
                        # Aceita outras notícias mas com menor prioridade
                        noticia['relevancia'] = 5
                        noticias_filtradas.append(noticia)
                else:
                    # Se não especificou região, aceita todas
                    noticia['relevancia'] = 7
                    noticias_filtradas.append(noticia)
        
        todas_noticias.extend(noticias_filtradas)
    
    # Remove duplicatas (por URL) e ordena por relevância
    noticias_unicas = {}
    for noticia in todas_noticias:
        url = noticia.get("link", "")
        if url and url not in noticias_unicas:
            noticias_unicas[url] = noticia
    
    # Ordena por relevância (maior primeiro) e depois por data
    noticias_ordenadas = sorted(
        noticias_unicas.values(),
        key=lambda x: (x.get('relevancia', 5), x.get('data', '')),
        reverse=True
    )
    
    return noticias_ordenadas[:limite]


def main() -> None:
    """Função principal para testar"""
    print("=" * 70)
    print("COLETOR DE NOTICIAS - GOOGLE SEARCH API")
    print("=" * 70)
    print()
    
    # Testa busca de notícias sobre legislação
    print("Buscando noticias sobre legislacao no Vale do Paraiba...")
    noticias = buscar_noticias_legislacao(
        regiao="Vale do Paraíba",
        dias_atras=30,
        limite=5
    )
    
    if noticias:
        print(f"\nTotal encontrado: {len(noticias)} noticias")
        for i, noticia in enumerate(noticias, 1):
            print(f"\n{'='*70}")
            print(f"{i}. {noticia.get('titulo', 'Sem titulo')}")
            print(f"   Fonte: {noticia.get('fonte', 'N/A')}")
            print(f"   Nivel: {noticia.get('nivel', 'N/A')}")
            print(f"   Data: {noticia.get('data', 'N/A')}")
            print(f"   Link: {noticia.get('link', 'N/A')}")
            
            # Mostra descrição/snippet
            descricao = noticia.get('descricao', '')
            if descricao:
                print(f"\n   Descricao: {descricao[:200]}...")
            
            # Mostra conteúdo completo se disponível
            conteudo = noticia.get('conteudo', '')
            if conteudo:
                print(f"\n   Conteudo completo ({len(conteudo)} caracteres):")
                # Mostra primeiros 500 caracteres do conteúdo
                conteudo_exibido = conteudo[:500].replace('\n', ' ').strip()
                print(f"   {conteudo_exibido}...")
            else:
                print(f"\n   [AVISO] Conteudo completo nao disponivel")
    else:
        print("\nNenhuma noticia encontrada.")


if __name__ == "__main__":
    main()