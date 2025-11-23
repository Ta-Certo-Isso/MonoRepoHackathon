from typing import List
from src.collectors.base import BaseCollector
from src.models.schemas import Proposition
from src.utils.scraper import scraper

class SenadoCollector(BaseCollector):
    """
    Collector for Senado Federal via Google Search.
    """
    
    def collect(self, days_back: int, limit: int) -> List[Proposition]:
        self.logger.info("Starting Senado collection...")
        
        sites_query = " OR ".join([f"site:{f}" for f in [
            "g1.globo.com", "folha.uol.com.br", "estadao.com.br",
            "oglobo.globo.com", "uol.com.br", "cartacapital.com.br"
        ]])
        
        queries = [
            f'"Senado Federal" "projeto de lei" ({sites_query})',
            f'"Senado" "senador" "aprova" ({sites_query})',
            f'"Senado Federal" "matéria" "tramitação" ({sites_query})'
        ]
        
        all_items = []
        for query in queries:
            results = scraper.search(query, days_back=days_back, limit=5)
            for item in results:
                # Filter to ensure it's about Senado
                text = f"{item['title']} {item['description']} {item.get('content', '')}".lower()
                if 'senado' not in text and 'senador' not in text:
                    continue
                    
                prop = Proposition(
                    title=item['title'],
                    description=item['description'],
                    content=item.get('content'),
                    link=item['link'],
                    date=item['date'],
                    source="senado_federal",
                    level="federal",
                    collection_type="google_search"
                )
                all_items.append(prop)
                
        # Deduplicate by link
        unique_items = {item.link: item for item in all_items}.values()
        
        self.logger.info(f"Senado collection finished. Found {len(unique_items)} items.")
        return list(unique_items)[:limit]
