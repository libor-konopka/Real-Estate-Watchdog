from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

# Definice základní třídy pro modely
Base = declarative_base()


class Estate(Base):
    """
    Tabulka pro unifikované inzeráty.
    Pokud se inzerát objeví znovu, nezakládáme nový řádek, jen aktualizujeme data.
    """

    __tablename__ = "estates"

    id = Column(Integer, primary_key=True)
    sreality_id = Column(
        Integer, unique=True, nullable=False, index=True
    )  # Klíčové pro deduplikaci
    title = Column(String)
    locality = Column(String)
    description = Column(String, nullable=True)

    # Extra data vyparsovaná z názvu/popisu
    area_match = Column(Integer, nullable=True)  # Užitná plocha v m2
    land_match = Column(Integer, nullable=True)  # Plocha pozemku v m2

    # Auditní sloupce
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Vazba 1:N (Jeden dům má mnoho záznamů o ceně v čase)
    prices = relationship(
        "Price", back_populates="estate", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Estate(id={self.sreality_id}, loc='{self.locality}')>"


class Price(Base):
    """
    Tabulka pro historii cen.
    Každý záznam znamená: "V tento den stál dům tolik peněz."
    """

    __tablename__ = "prices"

    id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey("estates.id"), nullable=False)
    price = Column(Integer, nullable=False)  # Ukládáme jako Integer (bez haléřů)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    # Vazba zpět
    estate = relationship("Estate", back_populates="prices")

    def __repr__(self):
        return f"<Price(val={self.price}, date='{self.scraped_at}')>"


# --- Inicializace DB (pouze pro test, v produkci bude jinde) ---
if __name__ == "__main__":
    # Vytvoří lokální SQLite databázi 'real_estate.db'
    engine = create_engine("sqlite:///real_estate.db")
    Base.metadata.create_all(engine)
    print("✅ Databáze a tabulky vytvořeny (real_estate.db)")
