import sys
from pathlib import Path

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

# --- 3. SQL DOTAZ (Pouze AKTUÁLNÍ ceny) ---
# Pravidlo: Analýza pouze nad deduplikovanými daty v aktuálním čase.
query = """
SELECT
    e.source,
    e.external_id,
    e.title,
    e.locality,
    p.price,
    p.scraped_at
FROM estates e
JOIN prices p ON e.id = p.estate_id
WHERE p.scraped_at = (
    -- Subquery: Pro každý inzerát najdi otisk nejnovější ceny
    SELECT MAX(scraped_at) FROM prices WHERE estate_id = e.id
)
ORDER BY p.price DESC
LIMIT 20
"""

# --- 4. NAČTENÍ DAT ---
print("📡 Čerpám data z databáze...")
try:
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
except Exception as e:
    print(f"❌ Nelze se spojit s databází: {e}")
    sys.exit(1)

# --- 5. TRANSFORMACE A VÝSTUP ---
if df.empty:
    print("📭 Databáze je prázdná.")
    sys.exit(0)

# Vektorové očištění časového razítka na čisté datum
df["scraped_at"] = pd.to_datetime(df["scraped_at"]).dt.date

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_colwidth", 40)

print("\n💎 TOP 20 NEJDRAŽŠÍCH NEMOVITOSTÍ (Aktuální nabídka)")
print("=" * 90)

print(
    df.to_string(
        formatters={
            "price": "{:,.0f} Kč".format,
        }
    )
)

print("\n📊 STATISTIKA CEN TOP 20 (V milionech Kč)")
print("-" * 40)
# Agregace a vizualizace hmoty
stats = (df["price"] / 1_000_000).describe()
print(stats.apply(lambda x: f"{x:,.2f} mil."))
