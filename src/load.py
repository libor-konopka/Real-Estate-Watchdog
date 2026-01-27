from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .domain import EstateSchema
from .logger import logger
from .models import Base, Estate, Price


class Loader:
    """
    Zodpovědnost: Uložení validních dat do SQLite databáze.
    Řeší deduplikaci (Insert vs Update) a historii cen.
    """

    def __init__(self, config: dict):
        # --- OPRAVA ZDE ---
        # Musíme vytáhnout string zanořený v configu
        # Původně to bralo celé 'config' a spadlo to.
        db_connection_string = config["database"]["connection_string"]

        self.engine = create_engine(db_connection_string)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def load(self, data: List[EstateSchema]):
        if not data:
            logger.warning("💾 LOAD: Žádná data k uložení.")
            return

        session = self.Session()
        new_estates = 0
        updated = 0
        new_prices = 0
        errors = 0

        try:
            logger.info("💾 START LOAD: Zahajuji transakci...")

            for dto in data:
                try:
                    # 1. Hledáme podle KOMPOZITNÍHO KLÍČE (Source + External ID)
                    estate = (
                        session.query(Estate)
                        .filter_by(source=dto.source, external_id=dto.external_id)
                        .first()
                    )

                    if estate:
                        # UPDATE existujícího
                        # Aktualizujeme metadata, pokud se změnila
                        if estate.title != dto.title or estate.url != dto.url:
                            estate.title = dto.title
                            estate.locality = dto.locality
                            estate.url = dto.url
                            updated += 1

                        # Logika ceny (historie)
                        last_price = (
                            session.query(Price)
                            .filter_by(estate_id=estate.id)
                            .order_by(Price.scraped_at.desc())
                            .first()
                        )

                        # Pokud cena neexistuje nebo je jiná, zapíšeme novou
                        if not last_price or last_price.price != dto.price:
                            if last_price:
                                diff = dto.price - last_price.price
                                logger.info(
                                    f"💰 Změna ceny ({dto.source}/{dto.title}): {diff:+d} CZK"
                                )

                            session.add(
                                Price(
                                    price=dto.price,
                                    estate=estate,
                                    scraped_at=dto.scraped_at,
                                )
                            )
                            new_prices += 1

                    else:
                        # INSERT nového
                        new_estate = Estate(
                            source=dto.source,
                            external_id=dto.external_id,
                            title=dto.title,
                            locality=dto.locality,
                            url=dto.url,
                        )
                        session.add(new_estate)
                        session.flush()  # Získáme ID pro vazbu ceny

                        session.add(
                            Price(
                                price=dto.price,
                                estate_id=new_estate.id,
                                scraped_at=dto.scraped_at,
                            )
                        )
                        new_estates += 1

                except Exception as e:
                    logger.error(
                        f"❌ Chyba při ukládání položky {dto.external_id}: {e}"
                    )
                    errors += 1
                    continue

            session.commit()
            logger.info(
                f"✅ LOAD DONE: +{new_estates} nových, {updated} update, +{new_prices} cen. (Chyby: {errors})"
            )

        except Exception as e:
            session.rollback()
            logger.critical(f"🔥 DB ERROR (ROLLBACK): {e}")
            raise e
        finally:
            session.close()
