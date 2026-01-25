import json
import time
from typing import Any, Dict, List

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.logger import logger  # Náš nový logger
from src.models import Base, Estate, Price

# --- NAČTENÍ KONFIGURACE ---
with open("config.json", "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# Databázové připojení z configu
engine = create_engine(CONFIG["database"]["connection_string"])
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_url_with_retry(url: str, retries: int = 3) -> Dict[str, Any]:
    """
    Enterprise pattern: Retry Logic with Exponential Backoff.
    Pokud API neodpoví, zkusíme to znovu (1s, 2s, 4s).
    """
    attempt = 0
    backoff = 1

    while attempt < retries:
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            attempt += 1
            logger.warning(f"Chyba sítě (pokus {attempt}/{retries}): {e}")
            if attempt == retries:
                logger.error(
                    f"Kritická chyba: URL {url} nedostupná po {retries} pokusech."
                )
                raise e
            time.sleep(backoff)
            backoff *= 2  # Exponenciální čekání
    return {}


def process_page(estates_list: List[Dict]) -> tuple[int, int, int]:
    """Zpracuje inzeráty z jedné stránky."""
    new_count = 0
    update_count = 0
    price_change_count = 0

    for item in estates_list:
        try:
            sreality_id = item["hash_id"]
            title = item["name"]
            locality = item["locality"]
            price_raw = item["price_czk"]["value_raw"]

            # Data validation
            price_value = int(price_raw) if isinstance(price_raw, (int, float)) else 0

            # UPSERT LOGIC
            existing_estate = (
                session.query(Estate).filter_by(sreality_id=sreality_id).first()
            )

            if existing_estate:
                existing_estate.title = title
                existing_estate.locality = locality
                update_count += 1

                last_price = (
                    session.query(Price)
                    .filter_by(estate_id=existing_estate.id)
                    .order_by(Price.scraped_at.desc())
                    .first()
                )

                if last_price and last_price.price != price_value:
                    logger.info(
                        f"💰 Změna ceny ID {sreality_id}: {last_price.price} -> {price_value}"
                    )
                    new_price = Price(price=price_value, estate=existing_estate)
                    session.add(new_price)
                    price_change_count += 1
            else:
                new_estate = Estate(
                    sreality_id=sreality_id, title=title, locality=locality
                )
                session.add(new_estate)
                session.flush()
                initial_price = Price(price=price_value, estate_id=new_estate.id)
                session.add(initial_price)
                new_count += 1

        except Exception as e:
            logger.error(f"Chyba při zpracování inzerátu: {e}")
            continue  # Skip bad record, don't crash pipeline

    return new_count, update_count, price_change_count


def run_pipeline():
    logger.info("🚀 START ETL PIPELINE")

    cfg = CONFIG["sreality"]
    base_url = f"{cfg['base_url']}?category_main_cb=2&category_type_cb=1&locality_district_id={cfg['district_id']}&per_page={cfg['per_page']}"

    page = 1
    total_new = 0

    while page <= cfg["max_pages"]:
        page_url = f"{base_url}&page={page}"
        logger.info(f"Stahuji stranu {page}...")

        try:
            data = fetch_url_with_retry(page_url)
            estates_list = data.get("_embedded", {}).get("estates", [])

            if not estates_list:
                logger.info("✅ Konec seznamu inzerátů.")
                break

            n, u, p = process_page(estates_list)
            total_new += n

            session.commit()
            logger.debug(f"Strana {page}: +{n} nových, {u} update.")

            page += 1
            time.sleep(cfg["request_delay"])

        except Exception as e:
            logger.critical(f"Pipeline spadla na straně {page}: {e}")
            session.rollback()
            break

    logger.info(f"🏁 KONEC ETL. Celkem nových: {total_new}")
    session.close()


if __name__ == "__main__":
    run_pipeline()
