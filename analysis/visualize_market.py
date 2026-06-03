import sys
from pathlib import Path

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
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

# --- 3. SQL (Pouze AKTUÁLNÍ ceny) ---
query = """
SELECT e.title, p.price
FROM estates e
JOIN prices p ON e.id = p.estate_id
WHERE p.scraped_at = (
    SELECT MAX(scraped_at) FROM prices WHERE estate_id = e.id
)
"""

print("📡 Čerpám data z databáze...")
try:
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)
except Exception as e:
    print(f"❌ Nelze se spojit s databází: {e}")
    sys.exit(1)

if df.empty:
    print("📭 Žádná data pro graf.")
    sys.exit(0)

# --- 4. VEKTOROVÁ TRANSFORMACE ---
print("🔄 Připravuji data pro vizualizaci (Vektorová extrakce)...")

# Aplikace čistícího regexu naráz na celý sloupec
clean_titles = df["title"].str.replace(r"[\xa0 \.]", "", regex=True)

# Nativní str.extract vyhledá vzor plošně. (?i) je inline flag pro IGNORECASE.
# Výsledek se rovnou přetypuje na float (Pandas Integer typ neumí držet NaN z inzerátů bez pozemku)
df["land_m2"] = clean_titles.str.extract(r"(?i)pozemek(\d+)m")[0].astype(float)

# Zmenšení řádu pro čitelnější osy
df["price_mil"] = df["price"] / 1_000_000

# --- 5. FILTROVÁNÍ (Outliers) ---
df_filtered = df[
    (df["land_m2"] > 0) & (df["land_m2"] < 15000) & (df["price_mil"] < 15.0)
].copy()

if df_filtered.empty:
    print("⚠️ Po filtrování nezbyla žádná data.")
    sys.exit(0)

# --- 6. VIZUALIZACE A MANIFESTACE ---
plt.figure(figsize=(14, 9))
sns.set_style("whitegrid")

scatter = sns.scatterplot(
    data=df_filtered,
    x="land_m2",
    y="price_mil",
    size="land_m2",
    sizes=(30, 300),
    hue="price_mil",
    palette="viridis_r",
    alpha=0.7,
    edgecolor="black",
)

# Definice cílové zóny
target_min_land = 1000
target_max_land = 5000
target_max_price = 4.5

rect = patches.Rectangle(
    (target_min_land, 0),
    target_max_land - target_min_land,
    target_max_price,
    linewidth=2,
    edgecolor="green",
    facecolor="#00ff00",
    alpha=0.15,
    linestyle="--",
    label="🎯 CÍL: Vize (< 4.5M)",
)
plt.gca().add_patch(rect)

plt.text(
    target_min_land + 200,
    1.0,
    "PROSTOR PRO TVŮJ PROJEKT",
    color="green",
    fontweight="bold",
    fontsize=10,
    rotation=90,
)

# Finální úpravy
plt.title("Analýza trhu: Cena vs. Pozemek", fontsize=18, pad=20)
plt.xlabel("Velikost pozemku (m²)", fontsize=14)
plt.ylabel("Cena (Miliony Kč)", fontsize=14)
plt.legend(loc="upper right", frameon=True)

# Odeslání do hmoty přes Pathlib
output_path = current_dir / "market_analysis.png"
plt.savefig(output_path, dpi=300, bbox_inches="tight")

print(f"✅ Graf úspěšně vygenerován: {output_path}")
