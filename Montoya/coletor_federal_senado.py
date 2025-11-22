"""
Coletor de Dados do Senado Federal
Busca dados sobre leis e projetos legislativos via API
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class ColetorSenado:
    """Classe para coletar dados da API do Senado Federal"""
    
    BASE_URL = "https://legis.senado.leg.br/dadosabertos"
    
    def __init__(self) -> None:
        """Inicializa o coletor com sessão HTTP configurada"""
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'Montoya-Bot/1.0'
        })
    
    def buscar_materias_recentes(
        self,
        dias_atras: int = 30,
        limite: int = 10
    ) -> List[Dict]:
        """
        Busca matérias recentes do Senado
        
        Args:
            dias_atras: Quantos dias atrás buscar
            limite: Quantidade máxima de resultados
            
        Returns:
            Lista de matérias
        """
        # Calcula data inicial
        data_inicio = (datetime.now() - timedelta(days=dias_atras)).strftime('%Y%m%d')
        
        # Endpoint da API do Senado - lista de matérias recentes
        url = f"{self.BASE_URL}/materia/lista/recentes"
        params = {
            'data': data_inicio,
            'ordenarPor': 'dataUltimaAtualizacao',
            'ordem': 'DESC',
            'itensPorPagina': min(limite, 100)  # Limita a 100 por requisição
        }
        
        try:
            print(f"[INFO] Buscando materias desde {data_inicio}...")
            response = self.session.get(url, params=params, timeout=15)
            
            # Se der erro 404, tenta endpoint alternativo
            if response.status_code == 404:
                print("[AVISO] Endpoint nao encontrado, tentando endpoint alternativo...")
                url = f"{self.BASE_URL}/materia/pesquisa/lista"
                params_alt = {
                    'dataInicio': data_inicio,
                    'itens': limite
                }
                response = self.session.get(url, params=params_alt, timeout=15)
            
            # Se ainda der erro, tenta sem data
            if response.status_code != 200:
                print("[AVISO] Tentando sem filtro de data...")
                url = f"{self.BASE_URL}/materia/pesquisa/lista"
                params_sem_data = {'itens': limite}
                response = self.session.get(url, params=params_sem_data, timeout=15)
            
            response.raise_for_status()
            
            # API do Senado retorna JSON
            data = response.json()
            
            # Extrai matérias da resposta
            materias = []
            if 'ListaMaterias' in data:
                materias = data.get('ListaMaterias', {}).get('Materias', {}).get('Materia', [])
            
            if not isinstance(materias, list):
                materias = [materias] if materias else []
            
            # Adiciona metadados padronizados e normaliza campos
            materias_normalizadas = []
            for materia in materias:
                # Extrai informações da estrutura do Senado
                ident = materia.get('IdentificacaoMateria', {})
                dados = materia.get('DadosBasicosMateria', {})
                
                materia_normalizada = {
                    'titulo': ident.get('DescricaoBasicaMateria', dados.get('EmentaMateria', '')),
                    'ementa': dados.get('EmentaMateria', ''),
                    'link': ident.get('LinkInteiroTeor', ''),
                    'codigo': ident.get('CodigoMateria', ''),
                    'numero': ident.get('NumeroMateria', ''),
                    'ano': ident.get('AnoMateria', ''),
                    'sigla': ident.get('SiglaMateria', ''),
                    'data': dados.get('DataApresentacao', ''),
                    'fonte': 'senado_federal',
                    'nivel': 'federal',
                    'tipo_coleta': 'api',
                    # Mantém dados originais para compatibilidade
                    'dados_originais': materia
                }
                materias_normalizadas.append(materia_normalizada)
            
            print(f"[OK] Encontradas {len(materias_normalizadas)} materias")
            return materias_normalizadas[:limite]
                
        except requests.exceptions.RequestException as e:
            print(f"[ERRO] Erro ao buscar materias: {e}")
            return []
    
    def buscar_materia_por_id(self, codigo_materia: str) -> Optional[Dict]:
        """
        Busca detalhes de uma matéria específica
        
        Args:
            codigo_materia: Código da matéria
            
        Returns:
            Dicionário com detalhes da matéria ou None
        """
        url = f"{self.BASE_URL}/materia/{codigo_materia}"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            content_type = response.headers.get('Content-Type', '')
            if 'json' in content_type.lower():
                data = response.json()
                return data.get('DetalheMateria', {}).get('Materia', None)
            else:
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"[ERRO] Erro ao buscar detalhes: {e}")
            return None
    
    def filtrar_por_relevancia(self, materias: List[Dict]) -> List[Dict]:
        """
        Filtra matérias por palavras-chave relevantes
        
        Args:
            materias: Lista de matérias
            
        Returns:
            Lista filtrada
        """
        keywords = [
            'imposto', 'taxa', 'tributo', 'IPVA', 'IPI', 'ICMS',
            'aumento', 'reducao', 'beneficio', 'auxilio', 'bolsa',
            'transporte', 'educacao', 'saude', 'previdencia',
            'salario', 'minimo', 'trabalho', 'emprego'
        ]
        
        relevantes = []
        
        for materia in materias:
            # Busca keywords no ementa ou descricao
            texto_busca = f"{materia.get('Ementa', '')} {materia.get('Descricao', '')}".lower()
            
            if any(keyword.lower() in texto_busca for keyword in keywords):
                relevantes.append(materia)
        
        return relevantes


def main() -> None:
    """Função principal para testar o coletor do Senado"""
    print("=" * 70)
    print("COLETOR SENADO FEDERAL")
    print("=" * 70)
    print()
    
    coletor = ColetorSenado()
    
    print("[INFO] Buscando materias recentes do Senado...")
    materias = coletor.buscar_materias_recentes(
        dias_atras=30,
        limite=10
    )
    
    if materias:
        print(f"[OK] Encontradas {len(materias)} materias")
        if materias:
            primeira = materias[0]
            print(f"\n[RESULTADO] Primeira materia:")
            print(f"  Codigo: {primeira.get('codigo', 'N/A')}")
            print(f"  Tipo: {primeira.get('sigla', 'N/A')} {primeira.get('numero', 'N/A')}/{primeira.get('ano', 'N/A')}")
            print(f"  Titulo: {primeira.get('titulo', 'N/A')[:100]}")
            print(f"  Ementa: {primeira.get('ementa', 'N/A')[:100]}")
            print(f"  Link: {primeira.get('link', 'N/A')}")
    else:
        print("[AVISO] Nenhuma materia encontrada")


if __name__ == "__main__":
    main()

