from typing import List
from src.collectors.base import BaseCollector
from src.models.schemas import Proposition
from src.utils.scraper import scraper

class AlespCollector(BaseCollector):
    """
    Collector for ALESP via Google Search.
    """
    
    def collect(self, days_back: int, limit: int) -> List[Proposition]:
        self.logger.info("Starting ALESP collection...")
        
        sites_query = " OR ".join([f"site:{f}" for f in [
            "g1.globo.com", "folha.uol.com.br", "estadao.com.br",
            "oglobo.globo.com", "uol.com.br", "cartacapital.com.br"
        ]])
        
        queries = [
            f'"ALESP" "projeto de lei" "assembleia legislativa" ({sites_query})',
            f'"ALESP" "deputado estadual" "aprova" ({sites_query})',
            f'"assembleia legislativa SP" "projeto" ({sites_query})'
        ]
        
        all_items = []
        for query in queries:
            results = scraper.search(query, days_back=days_back, limit=5)
            for item in results:
                # Filter for SP
                if "g1.globo.com" in item['link'] and "/sp/" not in item['link']:
                    continue
                    
                prop = Proposition(
                    title=item['title'],
                    description=item['description'],
                    content=item.get('content'),
                    link=item['link'],
                    date=item['date'],
                    source="alesp",
                    level="estadual",
                    collection_type="google_search"
                )
                all_items.append(prop)
                
        unique_items = {item.link: item for item in all_items}.values()
        
        self.logger.info(f"ALESP collection finished. Found {len(unique_items)} items.")
        return list(unique_items)[:limit]
