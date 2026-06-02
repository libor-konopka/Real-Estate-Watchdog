import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """
    Kmenová třída pro asynchronní datové extraktory.
    """

    # Použití Optional řeší konflikt typování
    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config or {}
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    @abstractmethod
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Každý scraper musí implementovat tuto metodu."""
        pass
