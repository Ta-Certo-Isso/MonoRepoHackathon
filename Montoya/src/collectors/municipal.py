from typing import List
from src.collectors.base import BaseCollector
from src.models.schemas import Proposition
from src.utils.scraper import scraper

class MunicipalCollector(BaseCollector):
    """
    Collector for Municipal news via Google Search.
    """
    
    def collect(self, days_back: int, limit: int) -> List[Proposition]:
        self.logger.info("Starting Municipal collection...")
        
        region = "Vale do Paraíba"
        cities = ["São José dos Campos", "Taubaté", "Jacareí", "Guaratinguetá", "Pindamonhangaba"]
        
        sites_query = " OR ".join([f"site:{f}" for f in [
            "g1.globo.com", "folha.uol.com.br", "estadao.com.br",
            "oglobo.globo.com", "uol.com.br", "portalvale.com.br"
        ]])
        
        queries = [
            f'"{region}" "projeto de lei" "câmara municipal" ({sites_query})',
            f'"{region}" "vereadores" "aprova" ({sites_query})'
        ]
        
        # Add city specific queries
        for city in cities[:2]:
             queries.append(f'"{city}" "projeto de lei" "câmara" ({sites_query})')
        
        all_items = []
        for query in queries:
            results = scraper.search(query, days_back=days_back, limit=5)
            for item in results:
                # Filter logic similar to original
                if "g1.globo.com" in item['link'] and "/sp/" not in item['link']:
                    continue
                    
                prop = Proposition(
                    title=item['title'],
                    description=item['description'],
                    content=item.get('content'),
                    link=item['link'],
                    date=item['date'],
                    source="municipal",
                    level="municipal",
                    collection_type="google_search"
                )
                all_items.append(prop)
                
        unique_items = {item.link: item for item in all_items}.values()
        
        self.logger.info(f"Municipal collection finished. Found {len(unique_items)} items.")
        return list(unique_items)[:limit]
