import os
import sqlite3
import sys

import pandas as pd

# --- 1. PATH HACK (Napojení na root projektu) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

try:
    from config_loader import load_config
except ImportError:
    print("❌ Chyba: Nenalezen config_loader.py.")
    sys.exit(1)

# --- 2. CONFIG & DB PATH ---
config = load_config()
# Získání absolutní cesty k DB ze stringu 'sqlite:///real_estate.db'
db_path_raw = config["database"]["connection_string"].replace("sqlite:///", "")
db_path = os.path.join(root_dir, db_path_raw)

if not os.path.exists(db_path):
    print(f"❌ Databáze neexistuje na cestě: {db_path}")
    print("Tip: Spusť nejprve 'main.py' v kořenu projektu.")
    sys.exit(1)

# --- 3. SQL DOTAZ (Pouze AKTUÁLNÍ ceny) ---
# Enterprise pravidlo: Nikdy nedělej analýzu nad duplicitními historickými daty,
# pokud explicitně neděláš časovou řadu.
query = """
SELECT 
    e.sreality_id,
    e.title, 
    e.locality, 
    p.price, 
    p.scraped_at
FROM estates e
JOIN prices p ON e.id = p.estate_id
WHERE p.scraped_at = (
    -- Subquery: Pro každý dům najdi datum nejnovější ceny
    SELECT MAX(scraped_at) FROM prices WHERE estate_id = e.id
)
ORDER BY p.price DESC
LIMIT 20
"""

# --- 4. NAČTENÍ DAT ---
conn = sqlite3.connect(db_path)
try:
    df = pd.read_sql(query, conn)
finally:
    conn.close()

# --- 5. VÝSTUP ---
if df.empty:
    print("📭 Databáze je prázdná.")
else:
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)
    pd.set_option("display.max_colwidth", 40)  # Zkrátíme dlouhé názvy

    print("\n💎 TOP 20 NEJDRAŽŠÍCH DOMŮ (Aktuální nabídka)")
    print("=" * 80)

    # Formátování ceny pro hezčí výpis (např. 15 000 000 místo 15000000)
    print(
        df.to_string(
            formatters={
                "price": "{:,.0f} Kč".format,
                "scraped_at": lambda x: str(x)[:10],  # Jen datum bez hodin
            }
        )
    )

    print("\n📊 STATISTIKA CEN (V milionech Kč)")
    print("-" * 30)
    # Zobrazíme statistiku v milionech, je to čitelnější
    stats = (df["price"] / 1_000_000).describe()
    print(stats.apply(lambda x: f"{x:,.2f} mil."))
