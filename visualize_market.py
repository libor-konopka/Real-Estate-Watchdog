import re
import sqlite3

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# 1. NAČTENÍ DAT
conn = sqlite3.connect("real_estate.db")
query = "SELECT title, price FROM estates e JOIN prices p ON e.id = p.estate_id"
df = pd.read_sql(query, conn)


# 2. TRANSFORMACE (Znovu vytáhneme pozemky, stejně jako v minulé lekci)
def get_land_area(text):
    text = text.replace("\xa0", "").replace(" ", "")
    match = re.search(r"pozemek(\d+)m", text, re.IGNORECASE)
    return int(match.group(1)) if match else None


df["land_m2"] = df["title"].apply(get_land_area)
df = df.dropna(subset=["land_m2", "price"])

# 3. FILTROVÁNÍ (Odstraníme extrémy, aby byl graf čitelný)
# Vyhodíme tu obří farmu v Březnici (nad 20 000 m2) a drahé vily nad 15M
df_filtered = df[
    (df["land_m2"] < 20000) & (df["price"] < 15000000) & (df["land_m2"] > 200)
]

# 4. VIZUALIZACE
plt.figure(figsize=(12, 8))
sns.set_style("whitegrid")

# Vytvoříme bodový graf
scatter = sns.scatterplot(
    data=df_filtered,
    x="land_m2",
    y="price",
    size="land_m2",
    sizes=(20, 200),
    alpha=0.6,
    edgecolor="black",
)

# 5. VYZNAČENÍ TVÉ CÍLOVÉ OBLASTI (Permakultura sweet spot)
# Hledáme: Pozemek > 1000 m2 a Cena < 4 miliony
plt.axvspan(
    1000,
    20000,
    ymin=0,
    ymax=4000000 / 15000000,
    color="green",
    alpha=0.1,
    label="Cílová zóna (Permakultura)",
)
plt.text(2000, 1000000, "🎯 TVŮJ CÍL", color="green", fontweight="bold", fontsize=12)

# Popisky
plt.title("Realitní trh Příbram: Cena vs. Velikost pozemku", fontsize=16)
plt.xlabel("Velikost pozemku (m²)", fontsize=12)
plt.ylabel("Cena (Kč)", fontsize=12)
plt.ticklabel_format(style="plain", axis="y")  # Aby se cena nevypisovala jako 1e7

# Uložení grafu
filename = "market_analysis.png"
plt.savefig(filename)
print(f"✅ Graf uložen jako {filename}. Podívej se na něj!")
