from abc import ABC, abstractmethod
from typing import List
from src.models.schemas import Proposition
from src.core.logging import get_logger

logger = get_logger(__name__)

class BaseCollector(ABC):
    """
    Abstract base class for data collectors.
    """
    
    def __init__(self):
        self.logger = logger

    @abstractmethod
    def collect(self, days_back: int, limit: int) -> List[Proposition]:
        """
        Collect data from the source.
        """
        pass

    def filter_relevant(self, items: List[Proposition]) -> List[Proposition]:
        """
        Filter items by relevance keywords.
        """
        keywords = [
            'imposto', 'taxa', 'tributo', 'IPVA', 'IPI', 'ICMS',
            'aumento', 'redução', 'benefício', 'auxílio', 'bolsa',
            'transporte', 'educação', 'saúde', 'previdência',
            'salário', 'mínimo', 'trabalho', 'emprego'
        ]
        
        relevant = []
        for item in items:
            text = f"{item.title} {item.description} {item.content or ''}".lower()
            if any(keyword.lower() in text for keyword in keywords):
                item.relevance_score = 10 # Simple score for now
                relevant.append(item)
                
        return relevant
