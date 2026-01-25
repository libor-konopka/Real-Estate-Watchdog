from typing import Dict, List

from .domain import EstateSchema
from .logger import logger


class Transformer:
    """
    Zodpovědnost: Převedení raw slovníku (JSON) na validovaný Pydantic objekt.
    """

    @staticmethod
    def transform(raw_data: List[Dict]) -> List[EstateSchema]:
        valid_items = []
        skipped_count = 0

        logger.info(f"🔄 START TRANSFORM: Ke zpracování {len(raw_data)} položek.")

        for item in raw_data:
            try:
                # 1. Extrakce ceny (Sreality to mají vnořené)
                # Cena může být v 'price_czk' -> 'value_raw'
                price_raw = item.get("price_czk", {}).get("value_raw")

                # Ošetření: Někdy je cena None nebo text
                if isinstance(price_raw, (int, float)):
                    price = int(price_raw)
                else:
                    price = 0  # Nebo přeskočit? Zatím dáme 0 (Cena dohodou)

                # 2. Vytvoření a validace přes Pydantic
                # Pokud tady něco chybí (např. title), EstateSchema vyhodí chybu
                estate = EstateSchema(
                    sreality_id=item["hash_id"],
                    title=item["name"],
                    locality=item["locality"],
                    price=price,
                )

                valid_items.append(estate)

            except Exception:
                # Pokud validace selže, logujeme varování, ale nezastavíme celou pipeline
                # logger.debug(f"Skipping item ID {item.get('hash_id')}: {e}")
                skipped_count += 1
                continue

        logger.info(
            f"✅ TRANSFORM COMPLETE: Validováno {len(valid_items)}, přeskočeno {skipped_count}."
        )
        return valid_items
