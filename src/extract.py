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


class BezrealitkyScraper(BaseScraper):
    """
    Extraktor dat pro Bezrealitky.
    Komunikuje přes GraphQL API pomocí POST požadavků.
    Stránkování probíhá přes limit a offset.
    """

    async def scrape(self, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
        results = []
        cfg = self.config.bezrealitky

        logger.info("📡 BEZREALITKY: Startuji async stahování...")

        limit = 15  # Pevně daná velikost okna dle API
        for page in range(1, cfg.max_pages + 1):
            offset = (page - 1) * limit

            payload = {
                "operationName": "AdvertList",
                "variables": {
                    "limit": limit,
                    "offset": offset,
                    "order": "TIMEORDER_DESC",
                    "locale": "CS",
                    "country": "ceska-republika",
                    "currency": "CZK",
                    "estateType": [cfg.estate_type.upper()],
                    "offerType": [cfg.offer_type.upper()],
                    "regionOsmIds": [cfg.region_id],
                },
                "query": """
                query AdvertList($limit: Int, $offset: Int, $estateType: [EstateType], $offerType: [OfferType], $regionOsmIds: [ID], $locale: Locale!) {
                  listAdverts(
                    limit: $limit
                    offset: $offset
                    estateType: $estateType
                    offerType: $offerType
                    regionOsmIds: $regionOsmIds
                  ) {
                    list {
                      id
                      uri
                      title
                      price
                      surface
                      surfaceLand
                      city(locale: $locale)
                    }
                  }
                }
                """,
            }

            try:
                async with session.post(
                    cfg.base_url, json=payload, headers=self.headers
                ) as response:
                    if response.status != 200:
                        logger.error(
                            f"❌ BEZREALITKY: Chyba {response.status} na straně {page}"
                        )
                        break

                    data = await response.json()

                    if "errors" in data:
                        logger.error(f"❌ BEZREALITKY GraphQL Error: {data['errors']}")
                        break

                    list_adverts = data.get("data", {}).get("listAdverts", {})
                    if not list_adverts:
                        logger.info("✅ BEZREALITKY: Konec dat (struktura nenalezena).")
                        break

                    adverts = list_adverts.get("list", [])

                    if not adverts:
                        logger.info("✅ BEZREALITKY: Konec dat (žádné inzeráty).")
                        break

                    for ad in adverts:
                        # 1. Ochrana před prázdnotou v titulku
                        raw_title = ad.get("title")
                        if not raw_title:
                            raw_title = "Rodinný dům"

                        # 2. Syntetický otisk pozemku: Vlisujeme ho do textu pro app.py
                        raw_land = ad.get("surfaceLand")
                        if raw_land:
                            final_title = f"{raw_title} s pozemkem {raw_land} m²"
                        else:
                            final_title = raw_title

                        # 3. Ochrana před null hodnotami u ceny
                        raw_price = ad.get("price")
                        final_price = str(raw_price) if raw_price is not None else "0"

                        # 4. Ochrana před prostorovou prázdnotou (Pydantic min_length=2)
                        raw_city = ad.get("city")
                        final_city = (
                            raw_city
                            if raw_city and len(raw_city) >= 2
                            else "Neznámá lokalita"
                        )

                        item = {
                            "_source_label": "bezrealitky",
                            "external_id": str(ad.get("id", "")),
                            "title": final_title,
                            "url": f"https://www.bezrealitky.cz/nemovitosti-byty-domy/{ad.get('uri', '')}",
                            "price_raw": final_price,
                            "locality": final_city,
                        }
                        results.append(item)

                    # --- NOVÁ FYZIKA STRÁNKOVÁNÍ ---
                    if len(adverts) < limit:
                        logger.info(
                            "✅ BEZREALITKY: Dosaženo konce (méně položek než limit)."
                        )
                        break
                    # -------------------------------

                    await asyncio.sleep(cfg.request_delay)

            except Exception as e:
                logger.error(f"❌ BEZREALITKY: Neočekávaná chyba: {e}")
                break

        logger.info(f"📦 BEZREALITKY: Staženo {len(results)} položek.")
        return results
