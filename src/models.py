from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

# Definice základní třídy pro modely
Base = declarative_base()


class Estate(Base):
    """
    Tabulka pro unifikované inzeráty ze VŠECH zdrojů.
    Unikátnost je dána kombinací: ZDROJ + JEHO ID.
    """

    __tablename__ = "estates"

    id = Column(Integer, primary_key=True)

    # Identifikace zdroje
    source = Column(String, nullable=False, index=True)  # 'sreality'
    external_id = Column(String, nullable=False, index=True)  # '12345678'

    title = Column(String, nullable=False)
    locality = Column(String, nullable=False)
    description = Column(String, nullable=True)

    # NOVÉ: URL adresa inzerátu
    url = Column(String, nullable=True)

    # Velikosti
    area_match = Column(Integer, nullable=True)
    land_match = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Kompozitní klíč (Zdroj + ID musí být unikátní)
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="_source_ext_id_uc"),
    )

    prices = relationship(
        "Price", back_populates="estate", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Estate({self.source}:{self.external_id})>"


class Price(Base):
    """
    Tabulka pro historii cen.
    """

    __tablename__ = "prices"

    id = Column(Integer, primary_key=True)
    estate_id = Column(Integer, ForeignKey("estates.id"), nullable=False)

    price = Column(Integer, nullable=False)
    scraped_at = Column(DateTime(timezone=True), server_default=func.now())

    estate = relationship("Estate", back_populates="prices")

    def __repr__(self):
        return f"<Price(val={self.price}, date='{self.scraped_at}')>"
