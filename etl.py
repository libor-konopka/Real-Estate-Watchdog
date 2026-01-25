import time

import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Estate, Price

# 1. SETUP DATABÁZE
engine = create_engine("sqlite:///real_estate.db")
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# 2. KONFIGURACE
# ID 32 = Okres Příbram (Ověř si to v URL, pokud ti to nic nenajde)
DISTRICT_ID = 58
BASE_URL = f"https://www.sreality.cz/api/cs/v2/estates?category_main_cb=2&category_type_cb=1&locality_district_id={DISTRICT_ID}&per_page=20"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def process_page(estates_list):
    """Zpracuje jednu stránku inzerátů (Upsert logika)"""
    new_count = 0
    update_count = 0
    price_change_count = 0

    for item in estates_list:
        sreality_id = item["hash_id"]
        title = item["name"]
        locality = item["locality"]
        price_value = item["price_czk"]["value_raw"]

        if not isinstance(price_value, (int, float)):
            price_value = 0

        # --- LOGIKA UPSERT ---
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
                print(
                    f"   💰 Změna ceny u ID {sreality_id}: {last_price.price} -> {price_value}"
                )
                new_price = Price(price=price_value, estate=existing_estate)
                session.add(new_price)
                price_change_count += 1
        else:
            new_estate = Estate(sreality_id=sreality_id, title=title, locality=locality)
            session.add(new_estate)
            session.flush()
            initial_price = Price(price=price_value, estate_id=new_estate.id)
            session.add(initial_price)
            new_count += 1

    return new_count, update_count, price_change_count


def run_etl():
    print(f"🚀 Spouštím ETL Pipeline pro region {DISTRICT_ID}...")

    page = 1
    total_new = 0

    while True:
        # Sestavení URL pro konkrétní stránku
        page_url = f"{BASE_URL}&page={page}"
        print(f"📡 Stahuji stranu {page}...")

        try:
            response = requests.get(page_url, headers=HEADERS)
            response.raise_for_status()
            data = response.json()

            estates_list = data["_embedded"]["estates"]

            # KONTROLA KONCE: Pokud je seznam prázdný, jsme na konci
            if not estates_list:
                print("✅ Konec seznamu. Žádné další inzeráty.")
                break

            # Zpracování stránky
            n, u, p = process_page(estates_list)
            total_new += n

            # Commit po každé stránce (bezpečnější než až na konci)
            session.commit()
            print(f"   -> Strana {page} hotova: +{n} nových, {u} update.")

            page += 1
            # Seniorní detail: Pauza, abychom nedostali BAN (Ethical Scraping)
            time.sleep(2)

        except Exception as e:
            print(f"❌ Chyba na straně {page}: {e}")
            session.rollback()
            break

    print(f"🏁 ETL DOKONČENO. Celkem přidáno {total_new} inzerátů.")
    session.close()


if __name__ == "__main__":
    run_etl()
