"""
Coletor de Dados Legislativos - Montoya
Busca dados de APIs públicas sobre leis e projetos legislativos
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ColetorCamara:
    """Classe para coletar dados da API da Câmara dos Deputados"""
    
    BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Montoya-Bot/1.0'
        })
    
    def buscar_proposicoes_recentes(
        self, 
        sigla_tipo: Optional[str] = None,
        dias_atras: int = 30,
        limite: int = 10
    ) -> List[Dict]:
        """
        Busca proposições recentes da Câmara
        
        Args:
            sigla_tipo: Tipo de proposição (ex: 'PL', 'PEC', 'MPV')
            dias_atras: Quantos dias atrás buscar (padrão: 30)
            limite: Quantidade máxima de resultados
            
        Returns:
            Lista de proposições
        """
        # Calcula data inicial (garantindo que seja uma data válida)
        data_inicio = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d')
        
        # Monta URL - começando com parâmetros mais simples
        url = f"{self.BASE_URL}/proposicoes"
        params = {
            'itens': limite,
            'ordem': 'DESC',
            'ordenarPor': 'id'
        }
        
        # Adiciona filtros opcionais
        if sigla_tipo:
            params['siglaTipo'] = sigla_tipo
        
        # Tenta com data, mas se falhar, tenta sem
        params_com_data = params.copy()
        params_com_data['dataInicio'] = data_inicio
        
        try:
            print(f"[INFO] Buscando proposicoes desde {data_inicio}...")
            # Primeiro tenta com data
            response = self.session.get(url, params=params_com_data, timeout=15)
            
            # Se der erro 400, tenta sem data
            if response.status_code == 400:
                print("[AVISO] Erro com filtro de data, tentando sem data...")
                response = self.session.get(url, params=params, timeout=15)
            
            response.raise_for_status()
            
            data = response.json()
            proposicoes = data.get('dados', [])
            
            # Se usou data, filtra manualmente por data
            if 'dataInicio' in params_com_data and proposicoes:
                data_limite = datetime.strptime(data_inicio, '%Y-%m-%d')
                proposicoes = [
                    p for p in proposicoes 
                    if p.get('dataApresentacao') and 
                    datetime.strptime(p['dataApresentacao'][:10], '%Y-%m-%d') >= data_limite
                ]
            
            # Adiciona metadados padronizados
            for prop in proposicoes:
                prop['fonte'] = 'camara_deputados'
                prop['nivel'] = 'federal'
                prop['tipo_coleta'] = 'api'
            
            print(f"[OK] Encontradas {len(proposicoes)} proposicoes")
            return proposicoes
            
        except requests.exceptions.RequestException as e:
            print(f"[ERRO] Erro ao buscar proposicoes: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"   Resposta: {e.response.text[:200]}")
            return []
    
    def buscar_detalhes_proposicao(self, id_proposicao: int) -> Optional[Dict]:
        """
        Busca detalhes completos de uma proposição
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Dicionário com detalhes da proposição ou None
        """
        url = f"{self.BASE_URL}/proposicoes/{id_proposicao}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('dados', None)
            
        except requests.exceptions.RequestException as e:
            print(f"[ERRO] Erro ao buscar detalhes: {e}")
            return None
    
    def filtrar_por_relevancia(self, proposicoes: List[Dict]) -> List[Dict]:
        """
        Filtra proposições por palavras-chave relevantes
        
        Args:
            proposicoes: Lista de proposições
            
        Returns:
            Lista filtrada
        """
        keywords = [
            'imposto', 'taxa', 'tributo', 'IPVA', 'IPI', 'ICMS',
            'aumento', 'redução', 'benefício', 'auxílio', 'bolsa',
            'transporte', 'educação', 'saúde', 'previdência',
            'salário', 'mínimo', 'trabalho', 'emprego'
        ]
        
        relevantes = []
        
        for prop in proposicoes:
            # Busca keywords no título e ementa
            texto_busca = f"{prop.get('ementa', '')} {prop.get('ementaDetalhada', '')}".lower()
            
            if any(keyword.lower() in texto_busca for keyword in keywords):
                relevantes.append(prop)
        
        return relevantes


def main():
    """Função principal para testar o coletor"""
    print("=" * 70)
    print("COLETOR DE DADOS LEGISLATIVOS - CAMARA DOS DEPUTADOS")
    print("=" * 70)
    print()
    
    coletor = ColetorCamara()
    
    # Busca proposições recentes (últimos 30 dias)
    print("[INFO] Buscando proposicoes recentes da Camara...")
    proposicoes = coletor.buscar_proposicoes_recentes(
        sigla_tipo='PL',  # Projetos de Lei
        dias_atras=30,
        limite=10
    )
    
    if not proposicoes:
        print("[AVISO] Nenhuma proposicao encontrada")
        return
    
    # Filtra por relevância
    print("\n[INFO] Filtrando por relevancia...")
    relevantes = coletor.filtrar_por_relevancia(proposicoes)
    
    print(f"\n[RESULTADO] Total encontrado: {len(proposicoes)}")
    print(f"[RESULTADO] Relevantes: {len(relevantes)}")
    print()
    
    # Mostra a primeira proposição relevante (ou a primeira se não houver relevantes)
    mostrar = relevantes[0] if relevantes else proposicoes[0]
    
    print("=" * 70)
    print("PRIMEIRA PROPOSICAO:")
    print("=" * 70)
    print(f"ID: {mostrar.get('id', 'N/A')}")
    print(f"Tipo: {mostrar.get('siglaTipo', 'N/A')} {mostrar.get('numero', 'N/A')}/{mostrar.get('ano', 'N/A')}")
    print(f"Ementa: {mostrar.get('ementa', 'N/A')[:200]}...")
    print(f"Data: {mostrar.get('dataApresentacao', 'N/A')}")
    print(f"Link: {mostrar.get('uri', 'N/A')}")
    print("=" * 70)


if __name__ == "__main__":
    main()

