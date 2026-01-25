import sqlite3

import pandas as pd

# 1. Připojení k DB (jako Connection String)
conn = sqlite3.connect("real_estate.db")

# 2. SQL Dotaz (Tady jsi doma)
# Chceme vidět název, lokalitu a aktuální cenu.
# Řadíme od nejdražších, abychom viděli, jestli tam nejsou nesmysly.
query = """
SELECT 
    e.sreality_id,
    e.title, 
    e.locality, 
    p.price, 
    p.scraped_at
FROM estates e
JOIN prices p ON e.id = p.estate_id
ORDER BY p.price DESC
LIMIT 20
"""

# 3. Načtení do Pandas DataFrame
# Pandas automaticky vezme názvy sloupců z SQL a vytvoří krásnou tabulku
df = pd.read_sql(query, conn)

# 4. Formátování výstupu
# Pandas defaultně zkracuje text, nastavíme, ať vidíme vše
pd.set_option("display.max_columns", None)
pd.set_option("display.width", 1000)

print("--- TOP 20 NEJDRAŽŠÍCH DOMŮ V OKRESE PŘÍBRAM ---")
print(df)

# Rychlá statistika (jako SELECT AVG(price), MIN(price)...)
print("\n--- STATISTIKA CEN ---")
print(df["price"].describe().apply(lambda x: format(x, "f")))
