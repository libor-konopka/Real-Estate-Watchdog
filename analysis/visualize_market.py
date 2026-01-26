import os
import re
import sqlite3
import sys

import matplotlib.patches as patches
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# --- 1. PATH HACK & CONFIG (Jako vždy) ---
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
sys.path.append(root_dir)

try:
    from src.config_loader import load_config
except ImportError:
    print("❌ Chyba: Spusť skript ze složky 'analysis' nebo přes python analysis/...")
    sys.exit(1)

config = load_config()
db_path = os.path.join(
    root_dir, config["database"]["connection_string"].replace("sqlite:///", "")
)

if not os.path.exists(db_path):
    print("❌ DB nenalezena. Spusť nejdřív main.py.")
    sys.exit(1)

# --- 2. SQL (Pouze AKTUÁLNÍ ceny) ---
conn = sqlite3.connect(db_path)
query = """
SELECT e.title, p.price 
FROM estates e 
JOIN prices p ON e.id = p.estate_id
WHERE p.scraped_at = (
    SELECT MAX(scraped_at) FROM prices WHERE estate_id = e.id
)
"""
df = pd.read_sql(query, conn)
conn.close()

if df.empty:
    print("📭 Žádná data pro graf.")
    sys.exit()


# --- 3. TRANSFORMACE ---
def get_land_area(text):
    # Oprava: Enter za dvojtečkou
    if not isinstance(text, str):
        return None

    try:
        text = text.replace("\xa0", "").replace(" ", "").replace(".", "")
        match = re.search(r"pozemek(\d+)m", text, re.IGNORECASE)

        if match:
            return int(match.group(1))
        return None  # Pokud nenajde, vrátí None (explicitní je lepší než implicitní)

    except Exception:
        return None


print("🔄 Připravuji data pro vizualizaci...")
df["land_m2"] = df["title"].apply(get_land_area)

# Převedeme cenu na miliony (čitelnější osy)
df["price_mil"] = df["price"] / 1_000_000

# --- 4. FILTROVÁNÍ (Outliers) ---
# Odstraníme extrémy pro čistší graf, ale ne příliš agresivně
df_filtered = df[
    (df["land_m2"] > 0)
    & (df["land_m2"] < 15000)  # Ořízneme obří pole nad 15 tis m2
    & (df["price_mil"] < 15.0)  # Ořízneme vily nad 15 mil.
].copy()

if df_filtered.empty:
    print("⚠️ Po filtrování nezbyla žádná data.")
    sys.exit()

# --- 5. VIZUALIZACE ---
plt.figure(figsize=(14, 9))
sns.set_style("whitegrid")

# Vytvoříme scatter plot
# Používáme 'hue' pro zvýraznění ceny barvou
scatter = sns.scatterplot(
    data=df_filtered,
    x="land_m2",
    y="price_mil",
    size="land_m2",
    sizes=(30, 300),
    hue="price_mil",
    palette="viridis_r",  # Obrácená paleta (tmavá = levná = dobrá)
    alpha=0.7,
    edgecolor="black",
)

# --- 6. PERMAKULTURA CÍLOVÁ ZÓNA (The Sweet Spot) ---
# Definice tvého cíle:
# Pozemek: 1000 až 5000 m2 (aby se tam dalo hospodařit)
# Cena: do 4.5 milionu (hypotetický strop)
target_min_land = 1000
target_max_land = 5000
target_max_price = 4.5

# Vykreslení obdélníku (Anchor je vlevo dole)
rect = patches.Rectangle(
    (target_min_land, 0),  # (x, y) start
    target_max_land - target_min_land,  # šířka
    target_max_price,  # výška
    linewidth=2,
    edgecolor="green",
    facecolor="#00ff00",
    alpha=0.15,
    linestyle="--",
    label="🎯 CÍL: Permakultura (< 4.5M)",
)
plt.gca().add_patch(rect)

# Popisek přímo do grafu
plt.text(
    target_min_land + 200,
    1.0,
    "PROSTOR PRO TVŮJ PROJEKT",
    color="green",
    fontweight="bold",
    fontsize=10,
    rotation=90,
)

# --- 7. FINÁLNÍ ÚPRAVY ---
plt.title("Analýza trhu Příbram: Cena vs. Pozemek", fontsize=18, pad=20)
plt.xlabel("Velikost pozemku (m²)", fontsize=14)
plt.ylabel("Cena (Miliony Kč)", fontsize=14)

# Legenda
plt.legend(loc="upper right", frameon=True)

# Uložení do složky analysis (ne do rootu, aby se to nemíchalo)
output_path = os.path.join(current_dir, "market_analysis.png")
plt.savefig(output_path, dpi=300, bbox_inches="tight")

print(f"✅ Graf úspěšně vygenerován: {output_path}")
print("Tip: Otevři ho ve VS Code kliknutím na soubor v levém panelu.")
