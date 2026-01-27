import re
import unicodedata
from typing import Dict, List

from .domain import EstateSchema
from .logger import logger


class Transformer:
    @staticmethod
    def _slugify(text: str) -> str:
        if not text:
            return "nezname"
        text = (
            unicodedata.normalize("NFKD", text)
            .encode("ascii", "ignore")
            .decode("utf-8")
        )
        return text.lower().replace(" ", "-").replace(",", "").replace(".", "")

    @staticmethod
    def _parse_price(text: str) -> int:
        """Univerzální parser ceny (odstraní 'Kč', mezery, atd.)"""
        if isinstance(text, (int, float)):
            return int(text)
        if not text:
            return 0
        # Odstraníme vše kromě číslic
        clean = re.sub(r"[^\d]", "", str(text))
        return int(clean) if clean else 0

    @staticmethod
    def transform(raw_data: List[Dict]) -> List[EstateSchema]:
        valid_items = []
        skipped = 0
        seen_ids = set()  # Množina pro sledování unikátních (source, external_id)

        logger.info(f"🔄 START TRANSFORM: {len(raw_data)} raw položek.")

        for item in raw_data:
            try:
                source = item.get("_source_label", "unknown")
                estate = None  # Inicializace

                # --- LOGIKA PRO SREALITY ---
                if source == "sreality":
                    price = item.get("price_czk", {}).get("value_raw", 0)
                    ext_id = str(item["hash_id"])

                    # Rychlá kontrola duplicity uvnitř dávky
                    if ("sreality", ext_id) in seen_ids:
                        continue

                    locality_slug = Transformer._slugify(item.get("locality", ""))
                    url = f"https://www.sreality.cz/detail/prodej/dum/rodinny/{locality_slug}/{ext_id}"

                    estate = EstateSchema(
                        source="sreality",
                        external_id=ext_id,
                        title=item["name"],
                        locality=item["locality"],
                        price=int(price) if price else 0,
                        url=url,
                    )

                # --- LOGIKA PRO IDNES ---
                elif source == "idnes":
                    ext_id = item.get("external_id")

                    # Rychlá kontrola duplicity uvnitř dávky
                    if ("idnes", ext_id) in seen_ids:
                        continue

                    price = Transformer._parse_price(item.get("price_raw"))

                    estate = EstateSchema(
                        source="idnes",
                        external_id=ext_id,
                        title=item["title"],
                        locality=item["locality"],
                        price=price,
                        url=item["url"],
                    )

                else:
                    skipped += 1
                    continue

                # Pokud se podařilo vytvořit objekt, přidáme ho
                if estate:
                    valid_items.append(estate)
                    seen_ids.add(
                        (estate.source, estate.external_id)
                    )  # Poznačíme si, že už ho máme

            except Exception as e:
                logger.debug(f"Chyba transformace ({source}): {e}")
                skipped += 1
                continue

        # Výpočet skutečně přeskočených (včetně duplicit v API)
        total_skipped = len(raw_data) - len(valid_items)
        logger.info(
            f"✅ TRANSFORM DONE: {len(valid_items)} unikátních, {total_skipped} zahozeno (chyby/duplicity)."
        )
        return valid_items
