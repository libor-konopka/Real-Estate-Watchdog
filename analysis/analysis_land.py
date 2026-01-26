import os
import re
import sqlite3
import sys

import pandas as pd

# --- 1. PATH HACK (Abychom viděli na config_loader v rodičovské složce) ---
# Získáme cestu k aktuálnímu souboru a jdeme o úroveň výš (do rootu)
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

try:
    from src.config_loader import load_config
except ImportError:
    print("❌ Chyba: Nemohu najít config_loader.py. Spouštíš skript ze správné složky?")
    sys.exit(1)

# --- 2. NAČTENÍ KONFIGURACE ---
config = load_config()
db_conn_string = config["database"]["connection_string"]
# Odstraníme 'sqlite:///' abychom dostali čistou cestu k souboru
db_path = os.path.join(root_dir, db_conn_string.replace("sqlite:///", ""))

if not os.path.exists(db_path):
    print(f"❌ Databáze neexistuje na cestě: {db_path}")
    print("Tip: Spusť nejprve 'main.py' v kořenu projektu.")
    sys.exit(1)

# --- 3. PANDAS & SQL ---
conn = sqlite3.connect(db_path)

query = """
SELECT e.title, e.locality, p.price
FROM estates e
JOIN prices p ON e.id = p.estate_id
-- Vezmeme jen nejnovější cenu pro každou nemovitost (pokud by jich bylo víc)
WHERE p.scraped_at = (
    SELECT MAX(scraped_at) FROM prices WHERE estate_id = e.id
)
AND p.price > 100000 -- Ignorujeme podezřele levné (např. 'Cena za m2')
"""

try:
    df = pd.read_sql(query, conn)
finally:
    conn.close()

if df.empty:
    print("📭 Databáze je prázdná. Žádná data k analýze.")
    sys.exit(0)


# --- 4. DATA MINING (REGEX) ---
def extract_data(text):
    if not isinstance(text, str):
        return pd.Series([None, None])

    # Odstraníme pevné mezery a běžné mezery -> "Prodejdomu150m2,pozemek800m2"
    clean_text = text.replace("\xa0", "").replace(" ", "")

    # A. Hledáme dům (číslo před 'm' na začátku nebo po typu nemovitosti)
    # Regex hledá např. "domu150m"
    house_match = re.search(
        r"(?:domu|chalupy|vily|usedlosti|chaty|prodej)(\d+)m", clean_text, re.IGNORECASE
    )
    house_area = int(house_match.group(1)) if house_match else None

    # B. Hledáme pozemek (číslo za slovem "pozemek")
    land_match = re.search(r"pozemek(\d+)m", clean_text, re.IGNORECASE)
    land_area = int(land_match.group(1)) if land_match else None

    return pd.Series([house_area, land_area])


# Aplikace regexu
print("🔄 Analyzuji texty inzerátů...")
df[["house_m2", "land_m2"]] = df["title"].apply(extract_data)

# --- 5. VÝPOČTY A METRIKY ---
# Cena za m2 pozemku (pouze pokud je pozemek > 0)
df["price_per_land"] = df.apply(
    lambda x: x["price"] / x["land_m2"] if x["land_m2"] and x["land_m2"] > 0 else None,
    axis=1,
)

# --- 6. VÝSTUP ---
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_colwidth", 50)  # Zkrátíme dlouhé názvy

print("\n" + "=" * 80)
print(f"📊 ANALÝZA TRHU ({len(df)} inzerátů)")
print("=" * 80)

# Permakultura TOP 10 (Velké pozemky)
print("\n🌳 TOP 10: Největší pozemky (Potenciál pro soběstačnost)")
top_land = df.sort_values(by="land_m2", ascending=False).head(10)
print(top_land[["title", "locality", "price", "land_m2", "price_per_land"]])

# Investiční TOP 10 (Nejlevnější m2, ale smysluplná velikost)
print("\n💰 TOP 10: Nejvýhodnější cena za m² (Pozemky > 800 m²)")
big_plots = df[df["land_m2"] > 800].copy()

if not big_plots.empty:
    best_deals = big_plots.sort_values(by="price_per_land").head(10)
    print(best_deals[["title", "locality", "price", "land_m2", "price_per_land"]])
else:
    print("⚠️ Žádné pozemky nad 800 m² nenalezeny.")
