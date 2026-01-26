import time
from typing import Any, Dict, List

import requests

from .logger import logger


class SrealityExtractor:
    """
    Zodpovědnost: Synchronní stahování dat z Sreality API.
    """

    def __init__(self, config: dict):
        self.base_url = config["base_url"]
        self.district_id = config["district_id"]
        self.per_page = config["per_page"]
        self.max_pages = config["max_pages"]
        # Načítáme delay z configu (s fallbackem na 2s, kdyby chyběl)
        self.delay = config.get("request_delay", 2)

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.sreality.cz/",
        }

    def extract(self) -> List[Dict[str, Any]]:
        all_data = []
        page = 1

        logger.info(f"📡 START EXTRACTION: Hledám v okrese ID {self.district_id}")

        while page <= self.max_pages:
            try:
                # Senior Way: Parametry jako slovník, ne string
                params = {
                    "category_main_cb": 2,  # Domy
                    "category_type_cb": 1,  # Prodej
                    "locality_district_id": self.district_id,
                    "per_page": self.per_page,
                    "page": page,
                }

                logger.debug(f"Stahuji stranu {page}/{self.max_pages}...")

                # Requests si parametry sám složí do URL
                response = requests.get(
                    self.base_url, params=params, headers=self.headers, timeout=10
                )

                response.raise_for_status()

                json_data = response.json()
                estates_batch = json_data.get("_embedded", {}).get("estates", [])

                if not estates_batch:
                    logger.info("✅ Konec seznamu inzerátů (API vrátilo prázdná data).")
                    break

                all_data.extend(estates_batch)

                # Dynamický sleep podle configu
                time.sleep(self.delay)
                page += 1

            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Chyba sítě na straně {page}: {e}")
                break
            except Exception as e:
                logger.error(f"❌ Neočekávaná chyba na straně {page}: {e}")
                break

        logger.info(f"📦 EXTRACT COMPLETE: Staženo celkem {len(all_data)} záznamů.")
        return all_data
