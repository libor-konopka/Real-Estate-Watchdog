import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine

# --- 1. UKOTVENÍ PROSTORU (Pathlib) ---
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
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
except Exception as e:
    print(f"❌ Nelze se spojit s databází: {e}")
    sys.exit(1)

if df.empty:
    print("📭 Databáze je prázdná. Žádná data k analýze.")
    sys.exit(0)


# --- 4. ROBUSTNÍ REGEX A TRANSFORMACE ---
def extract_house_area(text: str) -> Optional[int]:
    """Extrakce obytné plochy s fallbackem."""
    if not isinstance(text, str):
        return None

    clean_text = text.replace("\xa0", "").replace(" ", "")

    match = re.search(
        r"(?:domu|chalupy|vily|usedlosti|chaty|bytu|plocha|užitná)(\d+)m",
        clean_text,
        re.IGNORECASE,
    )
    if match:
        return int(match.group(1))

    match_fallback = re.search(r"^prodej[a-z]*(\d+)m", clean_text, re.IGNORECASE)
    if match_fallback:
        return int(match_fallback.group(1))

    return None


print("🔄 Analyzuji obytnou plochu...")
df["area"] = df["title"].apply(extract_house_area)

# Očištění od prázdnoty a extrémů (vektorový filter)
df = df.dropna(subset=["area"])
df = df[df["area"] > 15].copy()  # explicitní kopie zabrání SettingWithCopyWarning

# --- 5. VEKTOROVÉ METRIKY ---
df["price_per_m2"] = df["price"] / df["area"]

# --- 6. VÝSTUP A MANIFESTACE ---
# Globální nastavení vzhledu a formátování měny
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_colwidth", 50)
pd.set_option("display.float_format", "{:,.0f}".format)

print("\n" + "=" * 80)
print(f"🏠 ANALÝZA CENY ZA m² ({len(df)} validních inzerátů)")
print("=" * 80)

print("\n🔥 TOP 10 NEJVÝHODNĚJŠÍCH (Cena/m²):")
best_m2 = df.sort_values(by="price_per_m2").head(10)
print(
    best_m2[["title", "locality", "price", "area", "price_per_m2"]].reset_index(
        drop=True
    )
)

# Statistiky trhu
avg_m2 = df["price_per_m2"].mean()
median_m2 = df["price_per_m2"].median()

print("\n📊 STATISTIKA TRHU:")
print(f"Průměr: {avg_m2:,.0f} Kč/m²")
print(f"Medián: {median_m2:,.0f} Kč/m² (Odolnější vůči extrémům)")
