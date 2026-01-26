from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .domain import EstateSchema
from .logger import logger
from .models import Base, Estate, Price


class Loader:
    """
    Zodpovědnost: Správa databáze a nahrávání dat (Loading).
    Pattern: Unit of Work (Session management).
    """

    def __init__(self, connection_string: str):
        # Vytvoření enginu
        self.engine = create_engine(connection_string)

        # Enterprise pravidlo: Loader by měl zajistit, že tabulky existují
        # (v reálu by tu byla migrace přes Alembic, ale pro začátek stačí toto)
        Base.metadata.create_all(self.engine)

        # Továrna na sessions
        self.Session = sessionmaker(bind=self.engine)

    def load(self, data: List[EstateSchema]):
        if not data:
            return

        session = self.Session()
        new_estates = 0
        updated = 0
        new_prices = 0

        try:
            logger.info("💾 START LOAD: Zahajuji transakci...")

            for dto in data:
                # 1. Hledáme podle KOMPOZITNÍHO KLÍČE (Source + External ID)
                estate = (
                    session.query(Estate)
                    .filter_by(source=dto.source, external_id=dto.external_id)
                    .first()
                )

                if estate:
                    # UPDATE existujícího
                    if estate.title != dto.title or estate.url != dto.url:
                        estate.title = dto.title
                        estate.locality = dto.locality
                        estate.url = dto.url  # Aktualizujeme URL kdyby se změnila
                        updated += 1

                    # Logika ceny (zůstává stejná)
                    last_price = (
                        session.query(Price)
                        .filter_by(estate_id=estate.id)
                        .order_by(Price.scraped_at.desc())
                        .first()
                    )

                    if not last_price or last_price.price != dto.price:
                        if last_price:
                            diff = dto.price - last_price.price
                            logger.info(f"💰 Změna ceny ({dto.title}): {diff:+d} CZK")

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
                    session.flush()  # Získáme ID

                    session.add(
                        Price(
                            price=dto.price,
                            estate_id=new_estate.id,
                            scraped_at=dto.scraped_at,
                        )
                    )
                    new_estates += 1

            session.commit()
            logger.info(
                f"✅ LOAD: +{new_estates} nových, {updated} update, +{new_prices} cen."
            )

        except Exception as e:
            session.rollback()
            logger.critical(f"🔥 DB ERROR: {e}")
            raise e
        finally:
            session.close()
