from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class EstateSchema(BaseModel):
    """
    DTO (Data Transfer Object).
    Definuje striktní tvar dat pro Multi-source architekturu.
    """

    # Pydantic V2 konfigurace
    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    # --- IDENTITY FIELDS ---
    source: str = Field(..., description="Zdroj dat (např. 'sreality', 'idnes')")
    external_id: str = Field(..., description="Unikátní ID v rámci zdroje (string)")

    # --- DATA ---
    title: str = Field(..., min_length=3, description="Titulek inzerátu")
    locality: str = Field(..., min_length=2, description="Lokalita")
    price: int = Field(ge=0, description="Cena v CZK")

    # URL adresa
    url: Optional[str] = Field(None, description="Přímý odkaz na inzerát")

    # Volitelné
    description: Optional[str] = None

    # Audit
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
