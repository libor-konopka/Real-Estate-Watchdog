from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EstateSchema(BaseModel):
    """
    DTO (Data Transfer Object).
    Definuje striktní tvar dat pro Multi-source architekturu.
    """

    # Pydantic V2 konfigurace (nahrazuje starý 'class Config')
    model_config = ConfigDict(from_attributes=True)

    # --- NOVÉ IDENTITY FIELDS (Místo sreality_id) ---
    source: str = Field(..., description="Zdroj dat (např. 'sreality', 'idnes')")
    external_id: str = Field(..., description="Unikátní ID v rámci zdroje (string)")

    # --- DATA ---
    title: str = Field(..., min_length=3, description="Titulek inzerátu")
    locality: str = Field(..., description="Lokalita")
    price: int = Field(ge=0, description="Cena v CZK")

    # URL adresa (nově přidaná)
    url: Optional[str] = Field(None, description="Přímý odkaz na inzerát")

    # Volitelné
    description: Optional[str] = None

    # Audit
    scraped_at: datetime = Field(default_factory=datetime.now)

    # --- VALIDACE ---

    @field_validator("title")
    def clean_title(cls, v):
        if not v:
            raise ValueError("Titulek nesmí být prázdný")
        return v.strip()

    @field_validator("locality")
    def locality_must_make_sense(cls, v):
        if len(v) < 2:
            raise ValueError(f"Podezřelá lokalita: {v}")
        return v
