"""
Coletor ALESP - Assembleia Legislativa de São Paulo
Usa Google Search API para buscar notícias sobre a ALESP em sites confiáveis
(alternativa ao web scraping que estava bloqueando)
"""

import json
import sys
import io
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

# Tenta importar o scraper de notícias via Google Search
try:
    from scraper_noticias import buscar_noticias
    GOOGLE_SEARCH_DISPONIVEL = True
except ImportError:
    GOOGLE_SEARCH_DISPONIVEL = False

class ColetorALESP:
    """Classe para coletar dados da ALESP
    
    A ALESP possui Portal de Dados Abertos: https://www.al.sp.gov.br/dados-abertos/catalogo
    """
    
    BASE_URL = "https://www.al.sp.gov.br"
    PORTAL_DADOS_ABERTOS = "https://www.al.sp.gov.br/dados-abertos"
    
    def __init__(self) -> None:
        """Inicializa o coletor com sessão HTTP configurada"""
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def buscar_proposicoes_recentes(
        self,
        dias_atras: int = 30,
        limite: int = 10
    ) -> List[Dict]:
        """
        Busca proposições recentes da ALESP via Google Search API
        
        NOTA: A ALESP não expõe API REST pública funcional e o site bloqueia bots.
        Esta função usa Google Search para buscar notícias sobre a ALESP em sites confiáveis
        (G1, Folha, etc) que reportam sobre as proposições da assembleia.
        
        Args:
            dias_atras: Quantos dias atrás buscar
            limite: Quantidade máxima de resultados
            
        Returns:
            Lista de proposições encontradas em notícias
        """
        # Tenta primeiro via Google Search (mais confiável)
        if GOOGLE_SEARCH_DISPONIVEL:
            print("[INFO] Buscando noticias sobre ALESP via Google Search...")
            noticias = self.buscar_via_google_search(dias_atras=dias_atras, limite=limite)
            if noticias:
                return noticias
        
        # Fallback: web scraping (pode estar bloqueado)
        print("[INFO] Tentando web scraping direto (pode estar bloqueado)...")
        return self.buscar_via_web_scraping(limite=limite)
    
    def buscar_via_google_search(
        self,
        dias_atras: int = 30,
        limite: int = 10
    ) -> List[Dict]:
        """
        Busca notícias sobre ALESP usando Google Search API
        
        Args:
            dias_atras: Quantos dias atrás buscar
            limite: Quantidade máxima de resultados
            
        Returns:
            Lista de proposições encontradas em notícias
        """
        todas_noticias = []
        
        # Usa fontes acessíveis testadas (focando em SP)
        sites_query = " OR ".join([f"site:{f}" for f in [
            "g1.globo.com", "folha.uol.com.br", "estadao.com.br",
            "oglobo.globo.com", "uol.com.br", "cartacapital.com.br"
        ]])
        
        queries = [
            f'"ALESP" "projeto de lei" "assembleia legislativa" ({sites_query})',
            f'"ALESP" "deputado estadual" "aprova" ({sites_query})',
            f'"assembleia legislativa SP" "projeto" ({sites_query})',
            f'"ALESP" "proposição" ({sites_query})',
        ]
        
        for query in queries[:3]:  # Limita para não exceder rate limits
            try:
                noticias = buscar_noticias(
                    termo=query,
                    topico="legislacao",
                    dias_maximos=dias_atras,
                    limite=5,
                    extrair_conteudo=True  # Extrai conteúdo completo
                )
                
                # Converte notícias para formato de proposições
                for noticia in noticias:
                    # Filtra apenas notícias de SP
                    url = noticia.get("link", "").lower()
                    if "g1.globo.com" in url and "/sp/" not in url:
                        continue
                    
                    proposicao = {
                        'titulo': noticia.get('titulo', ''),
                        'link': noticia.get('link', ''),
                        'descricao': noticia.get('descricao', ''),
                        'conteudo': noticia.get('conteudo', ''),
                        'data': noticia.get('data', ''),
                        'fonte': 'alesp',
                        'nivel': 'estadual',
                        'tipo_coleta': 'google_search',
                        'ementa': noticia.get('descricao', '')  # Para compatibilidade
                    }
                    todas_noticias.append(proposicao)
                    
            except Exception as e:
                print(f"  [ERRO] Erro ao buscar via Google Search: {e}")
                continue
        
        # Remove duplicatas
        noticias_unicas = {}
        for prop in todas_noticias:
            url = prop.get('link', '')
            if url and url not in noticias_unicas:
                noticias_unicas[url] = prop
        
        print(f"[OK] Encontradas {len(noticias_unicas)} noticias sobre ALESP")
        return list(noticias_unicas.values())[:limite]
    
    def acessar_catalogo(self) -> Dict:
        """
        Acessa o catálogo de dados abertos da ALESP para descobrir endpoints
        
        Returns:
            Dicionário com informações do catálogo
        """
        url_catalogo = f"{self.PORTAL_DADOS_ABERTOS}/catalogo"
        try:
            response = self.session.get(url_catalogo, timeout=10)
            if response.status_code == 200:
                return {
                    "url": url_catalogo,
                    "status": "acessivel",
                    "html": response.text[:1000]  # Primeiros 1000 chars para debug
                }
        except Exception as e:
            return {"erro": str(e)}
        return {}
    
    def buscar_via_web_scraping(self, url: str = None, limite: int = 10) -> List[Dict]:
        """
        Busca proposições via web scraping do site da ALESP
        
        Args:
            url: URL específica para fazer scraping (opcional)
            limite: Quantidade máxima de resultados
            
        Returns:
            Lista de proposições extraídas
        """
        from bs4 import BeautifulSoup
        
        # URLs possíveis da ALESP para buscar proposições
        # Baseado na estrutura do site encontrada
        urls_tentativas = [
            f"{self.BASE_URL}/processo-legislativo",
            f"{self.BASE_URL}/leis",
            f"{self.BASE_URL}/processo-legislativo/materias",
            f"{self.BASE_URL}/processo-legislativo/proposicoes",
            f"{self.BASE_URL}/legislacao",
        ]
        
        proposicoes = []
        
        for url_teste in urls_tentativas:
            if url:
                url_teste = url
                
            try:
                print(f"Fazendo scraping de: {url_teste}")
                response = self.session.get(url_teste, timeout=15)
                
                if response.status_code == 503:
                    print(f"  [AVISO] Site retornou 503, tentando proxima URL...")
                    continue
                
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Tenta encontrar tabelas com proposições
                tabelas = soup.find_all('table')
                for tabela in tabelas:
                    linhas = tabela.find_all('tr')
                    for linha in linhas[1:]:  # Pula cabeçalho
                        celulas = linha.find_all(['td', 'th'])
                        if len(celulas) >= 2:
                            link = linha.find('a')
                            if link:
                                href = link.get('href', '')
                                if href and not href.startswith('http'):
                                    if href.startswith('/'):
                                        href = f"{self.BASE_URL}{href}"
                                    else:
                                        href = f"{url_teste.rstrip('/')}/{href}"
                                
                                titulo = link.get_text(strip=True)
                                # Filtra links que não são proposições reais
                                palavras_excluir = ['pesquisa', 'busca', 'extranet', 'sobre', 'historia', 'consulta', 'acesse']
                                palavras_requeridas = ['pl ', 'pec ', 'projeto', 'lei nº', 'lei n.', 'materia', 'proposicao']
                                titulo_lower = titulo.lower()
                                
                                # Aceita se tiver palavra requerida OU se não for link de pesquisa/busca
                                tem_palavra_requerida = any(palavra in titulo_lower for palavra in palavras_requeridas) or \
                                                       any(palavra in href.lower() for palavra in ['/proposicao', '/materia', '/pl-', '/pec-'])
                                
                                # Se não tem palavra requerida, mas também não é pesquisa/busca, aceita (pode ser link útil)
                                eh_link_util = not any(palavra in titulo_lower for palavra in ['pesquisa', 'busca', 'consulta'])
                                
                                if titulo and len(titulo) > 5 and \
                                   not any(palavra in titulo_lower for palavra in palavras_excluir) and \
                                   not href.endswith('/pesquisa-proposicoes') and \
                                   (tem_palavra_requerida or (eh_link_util and 'processo' in href.lower())):
                                    proposicao = {
                                        'titulo': titulo,
                                        'link': href,
                                        'fonte': 'alesp',
                                        'nivel': 'estadual',
                                        'tipo_coleta': 'web_scraping',
                                        'descricao': titulo  # Para compatibilidade
                                    }
                                    proposicoes.append(proposicao)
                                    
                                    if len(proposicoes) >= limite:
                                        break
                    
                    if len(proposicoes) >= limite:
                        break
                
                # Se não encontrou em tabelas, procura links específicos de proposições
                if not proposicoes:
                    todos_links = soup.find_all('a', href=True)
                    for link in todos_links:
                        href = link.get('href', '')
                        texto = link.get_text(strip=True)
                        
                        # Filtra links que parecem ser proposições reais
                        if texto and len(texto) > 10:
                            # Procura padrões de proposições (PL, PEC, etc)
                            if any(padrao in texto.upper() for padrao in ['PL ', 'PEC ', 'PROJETO', 'LEI Nº', 'LEI N.']) or \
                               any(palavra in href.lower() for palavra in ['proposicao', 'materia', '/pl-', '/pec-']):
                                
                                if href and not href.startswith('http'):
                                    if href.startswith('/'):
                                        href = f"{self.BASE_URL}{href}"
                                    else:
                                        href = f"{url_teste.rstrip('/')}/{href}"
                                
                                # Evita duplicatas e links não relevantes
                                palavras_excluir = ['pesquisa', 'busca', 'sobre', 'extranet', 'consulta', 'acesse', 'clique', 'saiba mais']
                                palavras_requeridas = ['pl ', 'pec ', 'projeto', 'lei nº', 'lei n.', 'materia', 'proposicao']
                                texto_lower = texto.lower()
                                
                                # Aceita se tiver palavra requerida OU se não for link de pesquisa/busca
                                tem_palavra_requerida = any(palavra in texto_lower for palavra in palavras_requeridas) or \
                                                       any(palavra in href.lower() for palavra in ['/proposicao', '/materia', '/pl-', '/pec-'])
                                
                                # Se não tem palavra requerida, mas também não é pesquisa/busca, aceita (pode ser link útil)
                                eh_link_util = not any(palavra in texto_lower for palavra in ['pesquisa', 'busca', 'consulta'])
                                
                                if not any(palavra in texto_lower for palavra in palavras_excluir) and \
                                   not href.endswith('/pesquisa-proposicoes') and \
                                   (tem_palavra_requerida or (eh_link_util and 'processo' in href.lower())):
                                    proposicao = {
                                        'titulo': texto,
                                        'link': href,
                                        'fonte': 'alesp',
                                        'nivel': 'estadual',
                                        'tipo_coleta': 'web_scraping',
                                        'descricao': texto  # Para compatibilidade
                                    }
                                    proposicoes.append(proposicao)
                                    
                                    if len(proposicoes) >= limite:
                                        break
                
                # Se encontrou proposições, para de tentar outras URLs
                if proposicoes:
                    break
                
                # Se não encontrou em tabelas, tenta listas
                if not proposicoes:
                    listas = soup.find_all(['ul', 'ol'])
                    for lista in listas:
                        itens = lista.find_all('li')
                        for item in itens:
                            link = item.find('a')
                            if link:
                                texto = link.get_text(strip=True)
                                href = link.get('href', '')
                                
                                # Filtra links que parecem ser proposições reais
                                palavras_excluir = ['pesquisa', 'busca', 'sobre', 'extranet', 'consulta', 'acesse', 'clique', 'saiba mais']
                                palavras_requeridas = ['pl ', 'pec ', 'projeto', 'lei nº', 'lei n.', 'materia', 'proposicao']
                                texto_lower = texto.lower()
                                
                                # Aceita se tiver palavra requerida OU se não for link de pesquisa/busca
                                tem_palavra_requerida = any(palavra in texto_lower for palavra in palavras_requeridas) or \
                                                       any(palavra in href.lower() for palavra in ['/proposicao', '/materia', '/pl-', '/pec-'])
                                
                                # Se não tem palavra requerida, mas também não é pesquisa/busca, aceita (pode ser link útil)
                                eh_link_util = not any(palavra in texto_lower for palavra in ['pesquisa', 'busca', 'consulta'])
                                
                                if texto and len(texto) > 10 and \
                                   not any(palavra in texto_lower for palavra in palavras_excluir) and \
                                   not href.endswith('/pesquisa-proposicoes') and \
                                   (tem_palavra_requerida or (eh_link_util and 'processo' in href.lower())):
                                    
                                    if href and not href.startswith('http'):
                                        if href.startswith('/'):
                                            href = f"{self.BASE_URL}{href}"
                                        else:
                                            href = f"{url_teste.rstrip('/')}/{href}"
                                    
                                    proposicao = {
                                        'titulo': texto,
                                        'link': href,
                                        'fonte': 'alesp',
                                        'nivel': 'estadual',
                                        'tipo_coleta': 'web_scraping',
                                        'descricao': texto  # Para compatibilidade
                                    }
                                    proposicoes.append(proposicao)
                                    
                                    if len(proposicoes) >= limite:
                                        break
                        
                        if len(proposicoes) >= limite:
                            break
                
                if proposicoes:
                    break
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 503:
                    print(f"  [AVISO] Site retornou 503, tentando proxima URL...")
                    continue
                else:
                    print(f"  [ERRO] HTTP {e.response.status_code}")
                continue
            except Exception as e:
                print(f"  [ERRO] {str(e)[:100]}")
                continue
            
            if url:  # Se foi passada URL específica, não tenta outras
                break
        
        if proposicoes:
            print(f"[OK] Encontradas {len(proposicoes)} proposicoes via scraping")
        else:
            print("[AVISO] Nenhuma proposicao encontrada. Site pode estar indisponivel ou estrutura mudou.")
        
        return proposicoes[:limite]


def main() -> None:
    """Função principal para testar o coletor ALESP"""
    # Configura encoding para Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    print("=" * 60)
    print("COLETOR ALESP - ASSEMBLEIA LEGISLATIVA DE SP")
    print("=" * 60)
    print()
    
    coletor = ColetorALESP()
    
    print("Buscando proposicoes recentes da ALESP...")
    proposicoes = coletor.buscar_proposicoes_recentes(
        dias_atras=30,
        limite=10
    )
    
    if proposicoes:
        print(f"Encontradas {len(proposicoes)} proposicoes")
        if proposicoes:
            primeira = proposicoes[0]
            print(f"\nPrimeira proposicao:")
            print(json.dumps(primeira, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 60)
        print("Nenhuma proposicao encontrada via API")
        print("\nA ALESP possui Portal de Dados Abertos, mas os endpoints")
        print("precisam ser verificados manualmente no catalogo:")
        print(f"{coletor.PORTAL_DADOS_ABERTOS}/catalogo")
        print("\nAlternativa: Implementar web scraping do site da ALESP")


if __name__ == "__main__":
    main()


