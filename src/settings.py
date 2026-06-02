import json
from pathlib import Path

from pydantic import BaseModel, Field


class DatabaseSettings(BaseModel):
    connection_string: str = Field(
        ..., description="URI lokátoru databáze, např. sqlite:///real_estate.db"
    )


class SrealitySettings(BaseModel):
    base_url: str = Field(..., description="Základní API endpoint pro vyhledávání")
    category_main_cb: int = Field(
        ..., description="Hlavní kategorie: 1 = Byty, 2 = Domy, 3 = Pozemky"
    )
    category_type_cb: int = Field(
        ..., description="Typ transakce: 1 = Prodej, 2 = Pronájem"
    )
    locality_country_id: int = Field(..., description="Geolokace státu: 112 = ČR")
    locality_region_id: int = Field(
        ..., description="Geolokace kraje: 11 = Středočeský"
    )
    district_id: int = Field(..., description="Geolokace okresu: 58 = Příbram")
    per_page: int = Field(
        default=60,
        description="Velikost stránky pro API dotaz",
        ge=1,
        le=100,  # Ochrana: API většinou nedovolí více než 100
    )
    max_pages: int = Field(
        default=20, description="Bezpečnostní limit maximálního počtu stránek"
    )
    request_delay: float = Field(
        default=1.0, description="Pauza mezi iteracemi (slušnost k serveru)"
    )


class IdnesSettings(BaseModel):
    base_url: str = Field(..., description="URL okresu na iDnes")
    max_pages: int = Field(default=5, description="Počet stran k seškrábání")
    request_delay: float = Field(
        default=1.0, description="Pauza mezi iteracemi (slušnost k serveru)"
    )
    default_locality: str = Field(
        default="Příbram (okres)", description="Záložní název lokality"
    )


class LoggingSettings(BaseModel):
    level: str = Field(
        default="INFO", description="Úroveň logování (INFO, DEBUG, ERROR)"
    )
    file: str = Field(default="logs/pipeline.log", description="Cesta k souboru s logy")


class AppConfig(BaseModel):
    """
    Hlavní konfigurační kmen sdružující všechny větve systému.
    """

    database: DatabaseSettings
    sreality: SrealitySettings
    idnes: IdnesSettings
    logging: LoggingSettings

    @classmethod
    def load(cls, path: str = "config.json") -> "AppConfig":
        """Načte JSON soubor a zhmotní ho do striktně typovaného objektu."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Konfigurační soubor {path} nebyl nalezen.")

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(**data)
