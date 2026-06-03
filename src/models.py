from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


# Základní třída v novém standardu SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass


class Estate(Base):
    """
    Tabulka pro unifikované inzeráty ze VŠECH zdrojů.
    Unikátnost je dána kombinací: ZDROJ + JEHO ID.
    """

    __tablename__ = "estates"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Identifikace zdroje
    source: Mapped[str] = mapped_column(String, index=True)
    external_id: Mapped[str] = mapped_column(String, index=True)

    # Základní data
    title: Mapped[str] = mapped_column(String)
    locality: Mapped[str] = mapped_column(String)

    # Volitelná data (Nyní s typem Text pro neomezený datový tok)
    description: Mapped[Optional[str]] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(Text)

    # Velikosti
    area_match: Mapped[Optional[int]] = mapped_column(Integer)
    land_match: Mapped[Optional[int]] = mapped_column(Integer)

    # Časová razítka
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Kompozitní klíč
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="_source_ext_id_uc"),
    )

    # Relace (Čistý zápis bez uvozovek díky __future__)
    prices: Mapped[List[Price]] = relationship(
        back_populates="estate", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Estate({self.source}:{self.external_id})>"


class Price(Base):
    """
    Tabulka pro historii cen.
    """

    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    estate_id: Mapped[int] = mapped_column(ForeignKey("estates.id"))

    price: Mapped[int] = mapped_column(Integer)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relace zpět (Čistý zápis bez uvozovek)
    estate: Mapped[Estate] = relationship(back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price(val={self.price}, date='{self.scraped_at}')>"
