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
                    # 1. Extrakce ID a kontrola existence
                    raw_id = item.get("hash_id")
                    if not raw_id:
                        logger.warning(
                            f"Přeskočen inzerát bez hash_id: {item.get('advert_name')}"
                        )
                        continue

                    external_id = str(raw_id)
                    title = item.get("advert_name", "Neznámý titulek")

                    # 2. Extrakce lokality z vnořeného objektu
                    locality_obj = item.get("locality", {})
                    # Pokud chybí 'city', vezmeme prázdný řetězec a Pydantic ho případně zachytí
                    locality = locality_obj.get("city", "Neznámá lokalita")

                    # 3. Získání čisté ceny v CZK
                    price = item.get("price_czk")

                    # 4. Konstrukce URL (Sreality tvoří URL na frontendu takto)
                    # Formát: https://www.sreality.cz/detail/prodej/dum/rodinny/{seo_lokalita}/{hash_id}
                    seo_city = locality_obj.get("city_seo_name", "neznama-lokalita")
                    url = f"https://www.sreality.cz/detail/prodej/dum/rodinny/{seo_city}/{external_id}"

                    # Sestavení normalizovaného slovníku
                    normalized = {
                        "source": source,  # Opraveno z _source_label
                        "external_id": external_id,
                        "title": title,
                        "locality": locality,
                        "url": url,
                        "price": int(price)
                        if price is not None
                        else 0,  # Opraveno z price_raw a převedeno na int
                        "area_match": None,
                        "land_match": None,
                    }

                    # Předání do Pydantic modelu a uložení
                    try:
                        parsed_item = EstateSchema(**normalized)
                        valid_items.append(parsed_item)
                    except Exception as e:
                        logger.warning(
                            f"SREALITY: Neplatný inzerát {external_id} - {e}"
                        )

                # --- LOGIKA PRO IDNES ---
                elif source == "idnes":
                    ext_id = item.get("external_id")

                    # Defenzivní kontroly proti chybějícím datům
                    if not ext_id:
                        logger.warning("IDNES: Přeskočen inzerát bez external_id")
                        skipped += 1
                        continue

                    # Rychlá kontrola duplicity uvnitř dávky
                    if ("idnes", ext_id) in seen_ids:
                        continue

                    price_raw = item.get("price_raw", "0")
                    price = Transformer._parse_price(str(price_raw))

                    # Bezpečné stažení s fallback hodnotami (zabrání chybám Unknown | None)
                    title = str(item.get("title", "Neznámý titulek"))
                    locality = str(item.get("locality", "Neznámá lokalita"))
                    url = str(item.get("url", ""))

                    estate = EstateSchema(
                        source="idnes",
                        external_id=str(ext_id),
                        title=title,
                        locality=locality,
                        price=price,
                        url=url,
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
