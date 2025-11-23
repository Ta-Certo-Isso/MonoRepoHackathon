import requests
from datetime import datetime, timedelta
from typing import List
from src.collectors.base import BaseCollector
from src.models.schemas import Proposition

class CamaraCollector(BaseCollector):
    """
    Collector for Camara dos Deputados API.
    """
    BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
    
    def collect(self, days_back: int, limit: int) -> List[Proposition]:
        self.logger.info("Starting Camara collection...")
        
        data_inicio = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        url = f"{self.BASE_URL}/proposicoes"
        params = {
            'itens': limit,
            'ordem': 'DESC',
            'ordenarPor': 'id',
            'siglaTipo': 'PL', # Default to PL
            'dataInicio': data_inicio
        }
        
        try:
            response = requests.get(url, params=params, timeout=15)
            
            # Fallback if date filter fails (API issue sometimes)
            if response.status_code == 400:
                self.logger.warning("Camara API rejected date filter, retrying without it.")
                del params['dataInicio']
                response = requests.get(url, params=params, timeout=15)
                
            response.raise_for_status()
            data = response.json().get('dados', [])
            
            propositions = []
            for item in data:
                prop = Proposition(
                    title=f"{item.get('siglaTipo')} {item.get('numero')}/{item.get('ano')}",
                    description=item.get('ementa', ''),
                    link=item.get('uri'),
                    date=item.get('dataApresentacao')[:10] if item.get('dataApresentacao') else None,
                    source="camara_deputados",
                    level="federal",
                    collection_type="api"
                )
                propositions.append(prop)
                
            self.logger.info(f"Camara collection finished. Found {len(propositions)} items.")
            return propositions
            
        except Exception as e:
            self.logger.error(f"Error collecting from Camara: {e}")
            return []
