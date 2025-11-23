import asyncio
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import Session

from src.core.config import settings
from src.core.logging import get_logger
from src.models.schemas import CollectionResult, CollectionSummary, Proposition
from src.models.db_models import DBProposition, DBScript
from src.collectors.camara import CamaraCollector
from src.collectors.senado import SenadoCollector
from src.collectors.alesp import AlespCollector
from src.collectors.municipal import MunicipalCollector

logger = get_logger(__name__)

class CollectorService:
    """
    Service to orchestrate data collection from all sources.
    """
    
    def __init__(self):
        self.collectors = {
            'federal_camara': CamaraCollector(),
            'federal_senado': SenadoCollector(),
            'estadual_alesp': AlespCollector(),
            'municipal': MunicipalCollector()
        }
        
    async def run_collection(self, days_back: int, limit: int, db: Session = None) -> CollectionSummary:
        """
        Run all collectors in parallel and save to DB.
        """
        days = days_back or settings.DEFAULT_DAYS_BACK
        limit_per_source = limit or settings.DEFAULT_LIMIT_PER_SOURCE
        
        logger.info(f"Starting full collection. Days: {days}, Limit: {limit_per_source}")
        
        loop = asyncio.get_event_loop()
        results_dict: Dict[str, List[Proposition]] = {}
        
        def run_collector(name, collector):
            try:
                if name == 'municipal' and not settings.INCLUDE_MUNICIPAL:
                    return []
                return collector.collect(days, limit_per_source)
            except Exception as e:
                logger.error(f"Collector {name} failed: {e}")
                return []

        with ThreadPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
            futures = []
            for name, collector in self.collectors.items():
                futures.append(
                    loop.run_in_executor(executor, run_collector, name, collector)
                )
            
            collected_lists = await asyncio.gather(*futures)
            
            for i, (name, _) in enumerate(self.collectors.items()):
                items = collected_lists[i]
                filtered = self.collectors[name].filter_relevant(items)
                results_dict[name] = filtered
                
                # Save to DB
                if db:
                    self._save_to_db(db, filtered)

        total = sum(len(items) for items in results_dict.values())
        summary_counts = {k: len(v) for k, v in results_dict.items()}
        
        logger.info(f"Collection completed. Total items: {total}")
        
        return CollectionSummary(
            total_items=total,
            sources_summary=summary_counts,
            details=results_dict
        )

    def _save_to_db(self, db: Session, items: List[Proposition]):
        """Save collected items to the database."""
        for item in items:
            # Check if exists (simple check by link or title)
            exists = db.query(DBProposition).filter(
                (DBProposition.link == item.link) | (DBProposition.title == item.title)
            ).first()
            
            if not exists:
                db_item = DBProposition(
                    title=item.title,
                    description=item.description,
                    content=item.content,
                    link=item.link,
                    date=item.date,
                    source=item.source,
                    level=item.level,
                    collection_type=item.collection_type
                )
                db.add(db_item)
        db.commit()

collector_service = CollectorService()
