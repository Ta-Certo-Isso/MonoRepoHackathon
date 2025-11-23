import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from googleapiclient.discovery import build

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)

class GoogleScraper:
    """
    Utility class for scraping news via Google Custom Search API.
    """
    
    def __init__(self):
        self.api_key = settings.GOOGLE_SEARCH_API_KEY
        self.engine_id = settings.GOOGLE_SEARCH_ENGINE_ID
        
        if not self.api_key or not self.engine_id:
            logger.warning("Google Search credentials not set. Search functionality will be disabled.")
            
    def search(
        self, 
        query: str, 
        days_back: int = 30, 
        limit: int = 10,
        extract_content: bool = True
    ) -> List[Dict]:
        """
        Perform a Google Custom Search.
        """
        if not self.api_key or not self.engine_id:
            return []
            
        try:
            service = build("customsearch", "v1", developerKey=self.api_key)
            
            logger.info(f"Searching for: '{query}'")
            res = service.cse().list(
                q=query, 
                cx=self.engine_id, 
                num=min(limit, 10),
                sort="date"
            ).execute()
            
            if "items" not in res:
                return []
                
            results = []
            for item in res["items"]:
                # Extract date
                news_date = item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time", "")
                news_date = news_date[:10] if news_date else ""
                
                # Filter by date
                if days_back > 0 and not self._is_recent(news_date, days_back):
                    continue
                    
                result = {
                    "title": item["title"],
                    "link": item["link"],
                    "description": item.get("snippet", ""),
                    "date": news_date,
                    "source": "google_search"
                }
                
                if extract_content:
                    result["content"] = self._extract_content(item["link"])
                    
                results.append(result)
                
                if len(results) >= limit:
                    break
                    
            return results
            
        except Exception as e:
            logger.error(f"Error in Google Search: {e}")
            return []

    def _is_recent(self, date_str: str, days: int) -> bool:
        """Check if date is within the last N days."""
        if not date_str:
            return True # Assume recent if no date
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            limit = datetime.today() - timedelta(days=days)
            return date_obj >= limit
        except:
            return True

    def _extract_content(self, url: str, max_chars: int = 2000) -> str:
        """Extract main text content from a URL."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            resp = requests.get(url, timeout=10, headers=headers)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            
            # Remove junk
            for s in soup(["script", "style", "nav", "footer", "header"]):
                s.extract()
            
            # Find main content
            article = soup.find('article') or soup.find('main') or soup.find('div', class_=lambda x: x and 'content' in str(x).lower())
            if article:
                text = article.get_text(separator=" ")
            else:
                text = soup.get_text(separator=" ")
                
            text = " ".join(text.split())
            return text[:max_chars]
        except Exception as e:
            logger.warning(f"Failed to extract content from {url}: {e}")
            return ""

# Global instance
scraper = GoogleScraper()
