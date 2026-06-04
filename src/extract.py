import asyncio
from typing import Any, Dict, List

import aiohttp
from bs4 import BeautifulSoup

from .base_scraper import BaseScraper
from .logger import logger


class SrealityScraper(BaseScraper):
    """
    Extraktor dat ze Sreality pomocí neveřejného JSON API v1.
    Zajišťuje stránkování pomocí offsetu a limitu.
    """

    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        results = []

        cfg = self.config.sreality
        base_url = cfg.base_url
        max_pages = cfg.max_pages
        per_page = cfg.per_page

        logger.info("📡 SREALITY: Startuji async stahování...")

        for page in range(1, max_pages + 1):
            # Přepočet stránky na offset
            limit = per_page
            offset = (page - 1) * limit

            params = {
                "category_main_cb": cfg.category_main_cb,
                "category_type_cb": cfg.category_type_cb,
                "locality_country_id": cfg.locality_country_id,
                "locality_region_id": cfg.locality_region_id,
                "locality_district_id": cfg.district_id,
                "limit": limit,
                "offset": offset,
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
                    estates = data.get("results", [])

                    if not estates:
                        logger.info("✅ SREALITY: Konec dat.")
                        break

                    # Obohacení dat o zdroj (abychom to poznali v transformaci)
                    for item in estates:
                        item["_source_label"] = "sreality"

                    results.extend(estates)

                    # Async sleep (neblokuje ostatní scrapery)
                    await asyncio.sleep(cfg.request_delay)

            except aiohttp.ClientError as e:
                logger.error(f"❌ SÍŤOVÁ CHYBA na straně {page}: {e}")
                break
            except Exception as e:
                logger.error(f"❌ NEOČEKÁVANÁ CHYBA: {e}")
                break

        logger.info(f"📦 SREALITY: Staženo {len(results)} položek.")
        return results


class IdnesScraper(BaseScraper):
    """
    Extraktor dat z portálu iDnes pomocí parsování HTML (BeautifulSoup).
    Spoléhá na CSS selektory.
    """

    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        results = []

        cfg = self.config.idnes
        base_url = cfg.base_url
        max_pages = cfg.max_pages
        delay = cfg.request_delay
        default_loc = cfg.default_locality

        logger.info("📡 IDNES: Startuji async stahování...")

        for page in range(1, max_pages + 1):
            try:
                async with session.get(
                    base_url, params={"page": page}, headers=self.headers
                ) as response:
                    if response.status != 200:
                        break

                    html = await response.text()
                    soup = BeautifulSoup(html, "html.parser")

                    articles = soup.find_all("div", class_="c-products__item")

                    if not articles:
                        logger.info("✅ IDNES: Konec dat.")
                        break

                    for article in articles:
                        link_tag = article.find("a", class_="c-products__link")
                        title_tag = article.find("h2", class_="c-products__title")
                        price_tag = article.find("p", class_="c-products__price")

                        if link_tag and title_tag:
                            # BeautifulSoup může vracet vícenásobné atributy...
                            raw_href = link_tag.get("href")
                            if isinstance(raw_href, list):
                                href = str(raw_href[0])
                            else:
                                href = str(raw_href or "")

                            # --- EXTRAKCE PŘESNÉ LOKALITY ---
                            locality_tag = article.find("p", class_="c-products__info")
                            if not locality_tag:
                                locality_tag = article.find(
                                    "span", class_="c-products__title-info"
                                )

                            if locality_tag:
                                # Získáme celý text (např. "Třebsko, okres Příbram")
                                raw_text = locality_tag.get_text(strip=True)
                                # Rozštěpíme text podle čárky a vezmeme pouze první část (index 0)
                                # .strip() zajistí odstranění případné mezery před čárkou
                                precise_locality = raw_text.split(",")[0].strip()
                            else:
                                precise_locality = default_loc

                            item = {
                                "_source_label": "idnes",
                                "external_id": href.strip("/").split("/")[-1]
                                if href
                                else "",
                                "title": title_tag.get_text(strip=True),
                                "url": href,
                                "price_raw": price_tag.get_text(strip=True)
                                if price_tag
                                else "0",
                                "locality": precise_locality,
                            }
                            results.append(item)

                    # Async sleep (neblokuje ostatní scrapery)
                    await asyncio.sleep(delay)

            except aiohttp.ClientError as e:
                logger.error(f"❌ SÍŤOVÁ CHYBA na straně {page}: {e}")
                break
            except Exception as e:
                logger.error(f"❌ NEOČEKÁVANÁ CHYBA: {e}")
                break

        logger.info(f"📦 IDNES: Staženo {len(results)} položek.")
        return results
