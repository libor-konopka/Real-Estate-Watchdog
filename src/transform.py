import unicodedata
from typing import Dict, List

from .domain import EstateSchema
from .logger import logger


class Transformer:
    """
    Zodpovědnost: Převedení raw JSONu na validovaný Pydantic objekt.
    Řeší i konstrukci URL a sjednocení ID.
    """

    @staticmethod
    def _slugify(text: str) -> str:
        """Převede 'Příbram - Zdaboř' na 'pribram-zdabor' pro URL."""
        if not text:
            return "nezname"
        # 1. Normalizace (rozloží znaky na písmeno + háček)
        text = unicodedata.normalize("NFKD", text)
        # 2. Odstranění diakritiky (zahodíme znaky, co nejsou ASCII)
        text = text.encode("ascii", "ignore").decode("utf-8")
        # 3. Malá písmena a náhrada mezer
        return text.lower().replace(" ", "-").replace(",", "").replace(".", "")

    @staticmethod
    def transform(raw_data: List[Dict]) -> List[EstateSchema]:
        valid_items = []
        skipped_count = 0

        logger.info(f"🔄 START TRANSFORM: Ke zpracování {len(raw_data)} položek.")

        for item in raw_data:
            try:
                # 1. Řešení Ceny
                price_raw = item.get("price_czk", {}).get("value_raw")
                if isinstance(price_raw, (int, float)):
                    price = int(price_raw)
                else:
                    price = 0

                # 2. Konstrukce URL (Smart Version)
                # ID je v 'hash_id'
                ext_id = str(item["hash_id"])

                # Vytvoříme 'slug' z lokality (např. 'Příbram' -> 'pribram')
                # Používáme fallback kategorii 'rodinny' - Sreality to automaticky
                # přesměrují na správnou (např. 'vila' nebo 'chalupa'), pokud sedí ID.
                locality_slug = Transformer._slugify(item.get("locality", ""))

                url = f"https://www.sreality.cz/detail/prodej/dum/rodinny/{locality_slug}/{ext_id}"

                # 3. Validace přes Pydantic
                estate = EstateSchema(
                    source="sreality",
                    external_id=ext_id,
                    title=item["name"],
                    locality=item["locality"],
                    price=price,
                    url=url,
                )

                valid_items.append(estate)

            except Exception as e:
                logger.debug(f"Skipping item: {e}")
                skipped_count += 1
                continue

        logger.info(
            f"✅ TRANSFORM COMPLETE: Validováno {len(valid_items)}, přeskočeno {skipped_count}."
        )
        return valid_items
