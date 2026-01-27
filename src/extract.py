import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List

import aiohttp
from bs4 import BeautifulSoup

from .logger import logger


# --- ABSTRAKTNÍ TŘÍDA (Interface) ---
class BaseScraper(ABC):
    def __init__(self, config: dict):
        self.config = config
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    @abstractmethod
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """Každý scraper musí implementovat tuto metodu."""
        pass


# --- IMPLEMENTACE: SREALITY (JSON API) ---
class SrealityScraper(BaseScraper):
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        results = []
        cfg = self.config["sreality"]
        base_url = cfg["base_url"]
        district_id = cfg["district_id"]
        max_pages = cfg["max_pages"]
        per_page = cfg["per_page"]

        logger.info(f"📡 SREALITY: Startuji async stahování (okres {district_id})...")

        for page in range(1, max_pages + 1):
            params = {
                "category_main_cb": 2,  # Domy
                "category_type_cb": 1,  # Prodej
                "locality_district_id": district_id,
                "per_page": per_page,
                "page": page,
            }

            try:
                async with session.get(
                    base_url, params=params, headers=self.headers
                ) as response:
                    if response.status != 200:
                        logger.error(
                            f"❌ SREALITY: Chyba {response.status} na straně {page}"
                        )
                        break

                    data = await response.json()
                    estates = data.get("_embedded", {}).get("estates", [])

                    if not estates:
                        logger.info("✅ SREALITY: Konec dat.")
                        break

                    # Obohacení dat o zdroj (abychom to poznali v transformaci)
                    for item in estates:
                        item["_source_label"] = "sreality"

                    results.extend(estates)

                    # Async sleep (neblokuje ostatní scrapery)
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ SREALITY: Exception na straně {page}: {e}")
                break

        logger.info(f"📦 SREALITY: Staženo {len(results)} položek.")
        return results


# --- IMPLEMENTACE: IDNES (HTML Parsing) ---
class IdnesScraper(BaseScraper):
    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        """
        iDnes nemá veřejné API, musíme parsovat HTML.
        URL pro Příbram (okres):
        https://reality.idnes.cz/s/prodej/domy/okres-pribram/?page=1
        """
        results = []
        # Tady natvrdo pro demonstraci, ideálně taky tahat z configu
        base_url = "https://reality.idnes.cz/s/prodej/domy/okres-pribram/"
        max_pages = 5  # Pro začátek méně, ať nedostaneme ban

        logger.info("📡 IDNES: Startuji async stahování...")

        for page in range(1, max_pages + 1):
            url = f"{base_url}?page={page}"

            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        break

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    # Selektory se mohou měnit, toto je aktuální stav k 2025/2026
                    articles = soup.find_all("div", class_="c-products__item")

                    if not articles:
                        logger.info("✅ IDNES: Konec dat.")
                        break

                    for article in articles:
                        # Extrakce dat z HTML
                        link_tag = article.find("a", class_="c-products__link")
                        title_tag = article.find("h2", class_="c-products__title")
                        price_tag = article.find("p", class_="c-products__price")

                        if link_tag and title_tag:
                            item = {
                                "_source_label": "idnes",
                                "external_id": link_tag["href"]
                                .strip("/")
                                .split("/")[-1],  # ID z URL
                                "title": title_tag.get_text(strip=True),
                                "url": link_tag["href"],
                                "price_raw": price_tag.get_text(strip=True)
                                if price_tag
                                else "0",
                                "locality": "Příbram (okres)",  # iDnes má lokalitu složitější, zatím placeholder
                            }
                            results.append(item)

                    await asyncio.sleep(1)  # Slušnost

            except Exception as e:
                logger.error(f"❌ IDNES: Exception: {e}")
                break

        logger.info(f"📦 IDNES: Staženo {len(results)} položek.")
        return results
