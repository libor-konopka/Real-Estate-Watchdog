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
        """
        Hlavní metoda pro uložení dat.
        Provádí UPSERT logiku (Aktualizuj existující, vlož nové).
        """
        if not data:
            logger.info("💾 LOAD: Žádná data k uložení.")
            return

        session = self.Session()
        new_estates_count = 0
        updated_estates_count = 0
        new_prices_count = 0

        try:
            logger.info("💾 START LOAD: Zahajuji transakci...")

            for dto in data:
                # 1. Hledáme, zda nemovitost už existuje (podle Sreality ID)
                estate = (
                    session.query(Estate).filter_by(sreality_id=dto.sreality_id).first()
                )

                if estate:
                    # --- SCÉNÁŘ A: Nemovitost už známe (UPDATE) ---
                    # Aktualizujeme metadata (kdyby se změnil název nebo lokalita)
                    if estate.title != dto.title or estate.locality != dto.locality:
                        estate.title = dto.title
                        estate.locality = dto.locality
                        updated_estates_count += 1

                    # Kontrola ceny (zajímá nás vývoj v čase)
                    # Najdeme poslední známou cenu pro tuto nemovitost
                    last_price = (
                        session.query(Price)
                        .filter_by(estate_id=estate.id)
                        .order_by(Price.scraped_at.desc())
                        .first()
                    )

                    # Pokud se cena změnila (nebo žádná není), vložíme novou
                    if not last_price or last_price.price != dto.price:
                        # Logování zajímavé události
                        if last_price:
                            diff = dto.price - last_price.price
                            logger.info(
                                f"💰 Změna ceny (ID {dto.sreality_id}): {last_price.price} -> {dto.price} ({diff:+d} CZK)"
                            )

                        new_price = Price(
                            price=dto.price,
                            estate=estate,  # SQLAlchemy vazba
                            scraped_at=dto.scraped_at,
                        )
                        session.add(new_price)
                        new_prices_count += 1

                else:
                    # --- SCÉNÁŘ B: Nová nemovitost (INSERT) ---
                    new_estate = Estate(
                        sreality_id=dto.sreality_id,
                        title=dto.title,
                        locality=dto.locality,
                    )
                    session.add(new_estate)
                    session.flush()  # Vynutí přidělení ID pro new_estate, abychom ho mohli použít pro Price

                    # Přidáme první cenu
                    initial_price = Price(
                        price=dto.price,
                        estate_id=new_estate.id,
                        scraped_at=dto.scraped_at,
                    )
                    session.add(initial_price)
                    new_estates_count += 1

            # 2. COMMIT (Potvrzení transakce)
            session.commit()

            # Enterprise Reporting
            logger.info(
                f"✅ LOAD COMPLETE: "
                f"+{new_estates_count} nových domů, "
                f"{updated_estates_count} aktualizovaných popisů, "
                f"+{new_prices_count} nových cen."
            )

        except Exception as e:
            # 3. ROLLBACK (Vrátit změny při chybě)
            session.rollback()
            logger.critical(f"🔥 CHYBA DATABÁZE (Rollback proveden): {e}")
            raise e  # Vyhoď chybu dál, ať main.py ví, že to spadlo

        finally:
            # 4. CLOSE (Vždy zavřít spojení)
            session.close()
