import re
import sqlite3

import pandas as pd

conn = sqlite3.connect("real_estate.db")

query = """
SELECT title, locality, price
FROM estates e
JOIN prices p ON e.id = p.estate_id
WHERE p.price > 1000000
"""
df = pd.read_sql(query, conn)

# --- POKROČILÝ REGEX ---


def extract_data(text):
    # Odstraníme pevné mezery (v "1 200" bývá často speciální znak \xa0)
    clean_text = text.replace("\xa0", "").replace(" ", "")

    # 1. Hledáme užitnou plochu (číslo hned za typem nemovitosti)
    # Hledá: "domu" + čísla + "m"
    house_match = re.search(
        r"(?:domu|chalupy|vily|usedlosti|chaty)(\d+)m", clean_text, re.IGNORECASE
    )
    house_area = int(house_match.group(1)) if house_match else None

    # 2. Hledáme pozemek (číslo za slovem "pozemek")
    land_match = re.search(r"pozemek(\d+)m", clean_text, re.IGNORECASE)
    land_area = int(land_match.group(1)) if land_match else None

    return pd.Series([house_area, land_area])


# Aplikujeme funkci (vrátí dva sloupce)
df[["house_m2", "land_m2"]] = df["title"].apply(extract_data)

# Filtry pro čistotu dat
df = df.dropna(subset=["price"])

# Výpočet metrik
# Ošetřujeme dělení nulou
df["price_per_house"] = df.apply(
    lambda x: x["price"] / x["house_m2"] if x["house_m2"] else None, axis=1
)
df["price_per_land"] = df.apply(
    lambda x: x["price"] / x["land_m2"] if x["land_m2"] else None, axis=1
)

# Nastavení zobrazení
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)
pd.set_option("display.max_colwidth", 60)

print("\n--- 🌳 TOP 10 NEJVĚTŠÍCH POZEMKŮ (Permakultura potenciál) ---")
# Řadíme podle velikosti pozemku (sestupně)
print(
    df[["title", "locality", "price", "land_m2", "price_per_land"]]
    .sort_values(by="land_m2", ascending=False)
    .head(10)
)

print("\n--- 💰 TOP 10 NEJVÝHODNĚJŠÍCH POZEMKŮ (Cena za m² půdy) ---")
# Řadíme podle ceny za metr pozemku (vzestupně), ale chceme aspoň 800 m2
big_plots = df[df["land_m2"] > 800]
print(
    big_plots[["title", "locality", "price", "land_m2", "price_per_land"]]
    .sort_values(by="price_per_land")
    .head(10)
)
