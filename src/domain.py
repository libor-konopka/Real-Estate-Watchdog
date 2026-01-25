from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EstateSchema(BaseModel):
    """
    DTO (Data Transfer Object).
    Definuje striktní tvar dat, která tečou skrz pipeline.

    Pokud API vrátí nesmysl (např. text místo čísla),
    Pydantic vyhodí chybu a nepustí data dál.
    """

    sreality_id: int = Field(..., description="Unikátní hash ID z Sreality")
    title: str = Field(..., min_length=3, description="Titulek inzerátu")
    locality: str = Field(..., description="Lokalita (např. 'Příbram')")
    price: int = Field(ge=0, description="Cena v CZK (musí být nezáporná)")

    # Volitelné pole (nemusí být vyplněno)
    description: Optional[str] = None

    # Automaticky doplníme čas, pokud není zadán
    scraped_at: datetime = Field(default_factory=datetime.now)

    # --- VLASTNÍ VALIDACE (Enterprise Business Logic) ---

    @field_validator("title")
    def clean_title(cls, v):
        """Očistí titulek od zbytečných mezer."""
        if not v:
            raise ValueError("Titulek nesmí být prázdný")
        return v.strip()

    @field_validator("locality")
    def locality_must_make_sense(cls, v):
        """Příklad validace: Lokalita nesmí být příliš krátká."""
        if len(v) < 2:
            raise ValueError(f"Podezřelá lokalita: {v}")
        return v

    class Config:
        # Povolí použití s ORM (pokud bychom to mapovali přímo)
        from_attributes = True
