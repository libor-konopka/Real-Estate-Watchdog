import time
from typing import Any, Dict, List

import requests

from .logger import logger  # Tečka znamená "z tohoto balíčku src"


class SrealityExtractor:
    """
    Zodpovědnost: Komunikace s API Sreality.
    Vstup: Konfigurace (dict).
    Výstup: Surový seznam inzerátů (List of Dicts).
    """

    def __init__(self, config: dict):
        self.base_url = config["base_url"]
        self.district_id = config["district_id"]
        self.per_page = config["per_page"]
        self.max_pages = config["max_pages"]

        # Tváříme se jako prohlížeč, aby nás API nezablokovalo
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
            # Sestavení URL s parametry
            url = (
                f"{self.base_url}"
                f"?category_main_cb=2"  # Domy
                f"&category_type_cb=1"  # Prodej
                f"&locality_district_id={self.district_id}"
                f"&per_page={self.per_page}"
                f"&page={page}"
            )

            try:
                logger.debug(f"Stahuji stranu {page}/{self.max_pages}...")

                # 1. Request s timeoutem (aby program nezamrzl)
                response = requests.get(url, headers=self.headers, timeout=10)

                # 2. Kontrola HTTP chyb (404, 500)
                response.raise_for_status()

                # 3. Parsování JSON
                json_data = response.json()
                estates_batch = json_data.get("_embedded", {}).get("estates", [])

                # Pokud API vrátí prázdný seznam, jsme na konci
                if not estates_batch:
                    logger.info("✅ Konec seznamu inzerátů (API vrátilo prázdná data).")
                    break

                all_data.extend(estates_batch)

                # 4. Politeness Policy (Zpoždění, abychom nedostali IP ban)
                time.sleep(2)
                page += 1

            except requests.exceptions.RequestException as e:
                # Síťová chyba (výpadek internetu, nedostupné API)
                logger.error(f"❌ Chyba sítě na straně {page}: {e}")
                # U kritické chyby sítě přerušíme cyklus, ale vrátíme, co máme
                break
            except Exception as e:
                # Jiná chyba (např. špatný JSON)
                logger.error(f"❌ Neočekávaná chyba na straně {page}: {e}")
                break

        logger.info(f"📦 EXTRACT COMPLETE: Staženo celkem {len(all_data)} záznamů.")
        return all_data
