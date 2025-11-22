"""
Coletor Municipal - Montoya
Coleta notícias sobre câmaras municipais do Vale do Paraíba via Google Search
"""

from typing import Dict, List
from scraper_noticias import buscar_noticias_legislacao


class ColetorMunicipal:
    """Classe para coletar dados municipais via Google Search"""
    
    def __init__(self) -> None:
        """Inicializa o coletor municipal"""
        pass
    
    def buscar_proposicoes_recentes(
        self,
        regiao: str = "Vale do Paraíba",
        dias_atras: int = 30,
        limite: int = 10
    ) -> List[Dict]:
        """
        Busca notícias sobre câmaras municipais da região
        
        Args:
            regiao: Região de interesse (padrão: "Vale do Paraíba")
            dias_atras: Quantos dias atrás buscar
            limite: Quantidade máxima de resultados
            
        Returns:
            Lista de notícias sobre legislação municipal
        """
        noticias = buscar_noticias_legislacao(
            regiao=regiao,
            dias_atras=dias_atras,
            limite=limite
        )
        
        # Filtra apenas notícias municipais
        noticias_municipais = [
            n for n in noticias
            if n.get('nivel') == 'municipal'
        ]
        
        # Adiciona metadados
        for noticia in noticias_municipais:
            noticia['fonte'] = 'noticias_municipais'
            noticia['nivel'] = 'municipal'
            noticia['tipo_coleta'] = 'google_search'
            if 'titulo' not in noticia:
                noticia['titulo'] = noticia.get('title', '')
            if 'descricao' not in noticia:
                noticia['descricao'] = noticia.get('snippet', '')
        
        return noticias_municipais
    
    def filtrar_por_relevancia(self, proposicoes: List[Dict]) -> List[Dict]:
        """
        Filtra proposições por relevância (já vem filtrado do scraper)
        
        Args:
            proposicoes: Lista de proposições
            
        Returns:
            Lista filtrada (mesma lista, pois já vem filtrada)
        """
        return proposicoes

