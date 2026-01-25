import re
import sqlite3

import pandas as pd

# Připojení
conn = sqlite3.connect("real_estate.db")

# Načteme data
query = """
SELECT e.title, e.locality, p.price
FROM estates e
JOIN prices p ON e.id = p.estate_id
WHERE p.price > 1000000 -- Ignorujeme chyby a podezřele levné věci
"""
df = pd.read_sql(query, conn)

# --- TRANSFORMACE (PANDAS MAGIC) ---


# Funkce na vytažení čísla m2 z textu "Prodej domu 150 m2..."
def extract_area(text):
    # Hledáme číslo následované "m" (např. 120 m, 120m, 120 m2)
    match = re.search(r"(\d+)\s*m", text)
    if match:
        return int(match.group(1))
    return None


# Aplikujeme funkci na sloupec title
df["area"] = df["title"].apply(extract_area)

# Vyhodíme řádky, kde se nepovedlo zjistit plochu nebo je cena 0
df = df.dropna(subset=["area"])
df = df[df["area"] > 20]  # Ignorujeme garáže a nesmysly pod 20m2

# VÝPOČET METRIKY
df["price_per_m2"] = df["price"] / df["area"]

# --- VÝSTUP ---
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_colwidth", 50)

# Řadíme od nejlevnějších na metr (potenciální kaufy)
print("\n--- 🏠 TOP 10 NEJVÝHODNĚJŠÍCH DOMŮ (Cena za m²) ---")
print(
    df[["title", "locality", "price", "area", "price_per_m2"]]
    .sort_values(by="price_per_m2")
    .head(10)
)

print("\n--- 📊 TRŽNÍ PRŮMĚR (Okres Příbram) ---")
avg_m2 = df["price_per_m2"].mean()
print(f"Průměrná cena: {avg_m2:,.0f} Kč/m²".replace(",", " "))
