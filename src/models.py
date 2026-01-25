from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

# Definice základní třídy pro modely
Base = declarative_base()


class Estate(Base):
    """
    Tabulka pro unifikované inzeráty (Nemovitosti).
    Identifikátorem je sreality_id.
    """

    __tablename__ = "estates"

    id = Column(Integer, primary_key=True)
    # Index=True zrychlí vyhledávání při UPSERT operacích
    sreality_id = Column(Integer, unique=True, nullable=False, index=True)

    title = Column(String, nullable=False)
    locality = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # Strukturální data (zatím nullable, naplníme později v Transform)
    area_match = Column(Integer, nullable=True)  # Užitná plocha v m2
    land_match = Column(Integer, nullable=True)  # Plocha pozemku v m2

    # Auditní sloupce (kdy jsme to našli a kdy naposledy viděli)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Vazba 1:N (Jeden dům -> Mnoho historických cen)
    prices = relationship(
        "Price", back_populates="estate", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Estate(id={self.sreality_id}, loc='{self.locality}')>"


class Price(Base):
    """
    Tabulka pro historii cen (Time-Series data).
    """

    __tablename__ = "prices"

    id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey("estates.id"), nullable=False)

    # BigInteger by byl bezpečnější pro Postgres, ale Integer v SQLite stačí (do 9 trilionů)
    price = Column(Integer, nullable=False)

    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    # Vazba zpět
    estate = relationship("Estate", back_populates="prices")

    def __repr__(self):
        return f"<Price(val={self.price}, date='{self.scraped_at}')>"
