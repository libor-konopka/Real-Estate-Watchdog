import re
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

# --- 1. UKOTVENÍ PROSTORU (Pathlib) ---
# Získáme absolutní cestu k rootu projektu a přidáme ji do cesty
current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent
sys.path.append(str(root_dir))

try:
    from src.settings import get_settings
except ImportError:
    print("❌ Chyba: Nemohu najít src.settings. Spouštíš skript z kořenového adresáře?")
    sys.exit(1)

# --- 2. NAČTENÍ ENERGIE A SPOJENÍ S HMOTOU ---
settings = get_settings()
db_url = settings.database.connection_string

# Vytvoření SQLAlchemy enginu (Pandas s ním nativně komunikuje)
engine = create_engine(db_url)

# --- 3. EXTRAKCE DAT (SQL) ---
query = """
SELECT e.title, e.locality, p.price
FROM estates e
JOIN prices p ON e.id = p.estate_id
WHERE p.scraped_at = (
    SELECT MAX(scraped_at) FROM prices WHERE estate_id = e.id
)
AND p.price > 100000
"""

print("📡 Čerpám data z databáze...")
try:
    # Pandas 2.0+ doporučuje používat SQLAlchemy connection explicitně
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
except Exception as e:
    print(f"❌ Nelze se spojit s databází: {e}")
    sys.exit(1)

if df.empty:
    print("📭 Databáze je prázdná. Žádná data k analýze.")
    sys.exit(0)


# --- 4. TRANSFORMACE DAT (REGEX) ---
def extract_areas(text: str) -> pd.Series:
    """Extrahuje velikost domu a pozemku z titulku."""
    if not isinstance(text, str):
        return pd.Series([None, None])

    clean_text = text.replace("\xa0", "").replace(" ", "")

    house_match = re.search(
        r"(?:domu|chalupy|vily|usedlosti|chaty|prodej)(\d+)m", clean_text, re.IGNORECASE
    )
    house_area = int(house_match.group(1)) if house_match else None

    land_match = re.search(r"pozemek(\d+)m", clean_text, re.IGNORECASE)
    land_area = int(land_match.group(1)) if land_match else None

    return pd.Series([house_area, land_area])


print("🔄 Normalizuji dimenze inzerátů...")
df[["house_m2", "land_m2"]] = df["title"].apply(extract_areas)

# --- 5. VEKTOROVÉ VÝPOČTY (Data Engineering Best Practice) ---
# Vektorové dělení je okamžité. Pandas automaticky zvládne NaN hodnoty.
df["price_per_land"] = df["price"] / df["land_m2"]

# --- 6. VÝSTUP A MANIFESTACE ---
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_colwidth", 50)

print("\n" + "=" * 80)
print(f"📊 ANALÝZA TRHU ({len(df)} inzerátů)")
print("=" * 80)

# Potenciál pro soběstačnost a celostní systémy
print("\n🌳 TOP 10: Největší pozemky (Potenciál pro soběstačnost a ekologii)")
top_land = df.sort_values(by="land_m2", ascending=False).head(10)
print(top_land[["title", "locality", "price", "land_m2", "price_per_land"]])

# Investiční hledisko
print("\n💰 TOP 10: Nejvýhodnější cena za m² (Pozemky nad 800 m²)")
big_plots = df[df["land_m2"] > 800].copy()

if not big_plots.empty:
    best_deals = big_plots.sort_values(by="price_per_land").head(10)
    print(best_deals[["title", "locality", "price", "land_m2", "price_per_land"]])
else:
    print("⚠️ Žádné pozemky nad 800 m² nenalezeny.")
