import os
import re
import sqlite3
import sys

import pandas as pd

# --- 1. PATH HACK (Napojení na config z rootu) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

try:
    from config_loader import load_config
except ImportError:
    print("❌ Chyba importu: Spouštíš skript ze správné složky?")
    sys.exit(1)

# --- 2. CONFIG SETUP ---
config = load_config()
db_path_raw = config["database"]["connection_string"].replace("sqlite:///", "")
db_path = os.path.join(root_dir, db_path_raw)

if not os.path.exists(db_path):
    print(f"❌ DB nenalezena: {db_path}")
    sys.exit(1)

# --- 3. SQL (Pouze aktuální ceny) ---
conn = sqlite3.connect(db_path)

# Tento dotaz zajistí, že pro každý dům máme jen tu NEJNOVĚJŠÍ cenu
query = """
SELECT e.title, e.locality, p.price
FROM estates e
JOIN prices p ON e.id = p.estate_id
WHERE p.scraped_at = (
    SELECT MAX(scraped_at) FROM prices WHERE estate_id = e.id
)
AND p.price > 100000
"""

df = pd.read_sql(query, conn)
conn.close()

if df.empty:
    print("📭 Žádná data.")
    sys.exit()


# --- 4. ROBUSTNÍ REGEX (Ochrana proti záměně s pozemkem) ---
def extract_house_area(text):
    if not isinstance(text, str):
        return None

    clean_text = text.replace("\xa0", "").replace(" ", "")

    # Hledáme číslo, před kterým je specifické slovo (domu, chaty, plocha...)
    # Tím ignorujeme "pozemek 800m", "do centra 500m" atd.
    match = re.search(
        r"(?:domu|chalupy|vily|usedlosti|chaty|bytu|plocha|užitná)(\d+)m",
        clean_text,
        re.IGNORECASE,
    )

    if match:
        return int(match.group(1))

    # Fallback: Pokud nezaberou klíčová slova, zkusíme najít číslo na úplném začátku stringu
    # Typicky: "Prodej domu 150 m2..." -> "Prodejdomu150m2"
    match_fallback = re.search(r"^prodej[a-z]*(\d+)m", clean_text, re.IGNORECASE)
    if match_fallback:
        return int(match_fallback.group(1))

    return None


print("🔄 Analyzuji obytnou plochu...")
df["area"] = df["title"].apply(extract_house_area)

# Vyhodíme neznámé velikosti a extrémy (boudy pod 15m2)
df = df.dropna(subset=["area"])
df = df[df["area"] > 15]

# --- 5. METRIKY ---
df["price_per_m2"] = df["price"] / df["area"]

# --- 6. VÝSTUP ---
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_colwidth", 50)

print("\n" + "=" * 60)
print(f"🏠 ANALÝZA CENY ZA m² ({len(df)} validních inzerátů)")
print("=" * 60)

# Žebříček nejlevnějších
print("\n🔥 TOP 10 NEJVÝHODNĚJŠÍCH (Cena/m²):")
print(
    df[["title", "locality", "price", "area", "price_per_m2"]]
    .sort_values(by="price_per_m2")
    .head(10)
    .to_string(
        index=False,
        formatters={"price": "{:,.0f}".format, "price_per_m2": "{:,.0f}".format},
    )
)

# Statistiky
avg_m2 = df["price_per_m2"].mean()
median_m2 = df["price_per_m2"].median()

print("\n📊 STATISTIKA TRHU:")
print(f"Průměr: {avg_m2:,.0f} Kč/m²")
print(f"Medián: {median_m2:,.0f} Kč/m² (Reálnější střed)")
