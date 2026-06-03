import re
from typing import Any, Dict, List

from .domain import EstateSchema
from .logger import logger


class Transformer:
    @staticmethod
    def _parse_price(text: Any) -> int:
        """Univerzální parser ceny (odstraní 'Kč', mezery, atd.)"""
        if isinstance(text, (int, float)):
            return int(text)
        if not text:
            return 0

        # Odstraníme vše kromě číslic
        clean = re.sub(r"[^\d]", "", str(text))
        return int(clean) if clean else 0

    @staticmethod
    def transform(raw_data: List[Dict[str, Any]]) -> List[EstateSchema]:
        valid_items: List[EstateSchema] = []
        seen_ids = set()  # Množina pro sledování unikátních (source, external_id)

        logger.info(f"🔄 START TRANSFORM: {len(raw_data)} raw položek.")

        for item in raw_data:
            try:
                source = item.get("_source_label", "unknown")

                # --- 1. EXTRAKCE PROMĚNNÝCH PODLE ZDROJE ---
                if source == "sreality":
                    raw_id = item.get("hash_id")
                    if not raw_id:
                        continue

                    external_id = str(raw_id)
                    title = item.get("advert_name", "Neznámý titulek")

                    locality_obj = item.get("locality", {})
                    locality = locality_obj.get("city", "Neznámá lokalita")

                    price = item.get("price_czk")
                    clean_price = int(price) if price is not None else 0

                    seo_city = locality_obj.get("city_seo_name", "neznama-lokalita")
                    url = f"https://www.sreality.cz/detail/prodej/dum/rodinny/{seo_city}/{external_id}"

                elif source == "idnes":
                    raw_id = item.get("external_id")
                    if not raw_id:
                        continue

                    external_id = str(raw_id)
                    title = str(item.get("title", "Neznámý titulek"))
                    locality = str(item.get("locality", "Neznámá lokalita"))
                    url = str(item.get("url", ""))
                    clean_price = Transformer._parse_price(item.get("price_raw", "0"))

                else:
                    # Neznámý zdroj
                    continue

                # --- 2. DEDUPLIKACE ---
                # Rychlá kontrola identity ještě před instanciací šetří procesor
                identity = (source, external_id)
                if identity in seen_ids:
                    continue

                # --- 3. INSTANCIACE A ZÁPIS ---
                # Společné nalití očištěné energie do Pydantic formy
                estate = EstateSchema(
                    source=source,
                    external_id=external_id,
                    title=title,
                    locality=locality,
                    price=clean_price,
                    url=url,
                )

                valid_items.append(estate)
                seen_ids.add(identity)

            except Exception as e:
                logger.debug(f"Chyba transformace ({item.get('_source_label')}): {e}")
                continue

        # Výpočet skutečně přeskočených (včetně duplicit v API)
        total_skipped = len(raw_data) - len(valid_items)
        logger.info(
            f"✅ TRANSFORM DONE: {len(valid_items)} unikátních, {total_skipped} zahozeno (chyby/duplicity)."
        )
        return valid_items
