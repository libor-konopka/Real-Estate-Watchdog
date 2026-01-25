import json
import os
import re
import sqlite3

import pandas as pd
import streamlit as st

# --- KONFIGURACE A CESTY ---
st.set_page_config(page_title="Real Estate Watchdog", layout="wide")


def load_config() -> dict:
    """Načte konfiguraci pro připojení k DB."""
    config_path = "config.json"
    if not os.path.exists(config_path):
        st.error(f"❌ Chybí konfigurační soubor: {config_path}")
        st.stop()

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Načteme config
CONFIG = load_config()


# --- POMOCNÉ FUNKCE ---
def get_db_path(connection_string: str) -> str:
    """Získá čistou cestu k souboru z connection stringu (sqlite:///file.db)."""
    return connection_string.replace("sqlite:///", "")


def extract_land_area(text: str) -> int:
    """
    Vytáhne velikost pozemku z textu inzerátu.
    Příklad: 'Prodej domu 150 m2, pozemek 800 m2' -> 800
    """
    if not isinstance(text, str):
        return 0

    # Odstranění mezer pro snadnější regex (8 000 -> 8000)
    clean_text = text.replace("\xa0", "").replace(" ", "")

    # Hledáme číslo před 'm' (case insensitive), které následuje po slově 'pozemek'
    match = re.search(r"pozemek(\d+)m", clean_text, re.IGNORECASE)
    return int(match.group(1)) if match else 0


# --- DATA LOADER ---
@st.cache_data(ttl=60)
def load_data(db_path: str) -> pd.DataFrame:
    """Načte data z SQLite a provede základní transformace."""
    if not os.path.exists(db_path):
        return pd.DataFrame()  # Vrátí prázdný DF, pokud DB neexistuje

    conn = sqlite3.connect(db_path)

    query = """
    SELECT 
        e.title, 
        e.locality, 
        p.price, 
        p.scraped_at, 
        e.sreality_id 
    FROM estates e 
    JOIN prices p ON e.id = p.estate_id
    """

    try:
        df = pd.read_sql(query, conn)
        # Aplikace logiky na vytažení pozemku
        df["land_m2"] = df["title"].apply(extract_land_area)
        return df
    except Exception as e:
        st.error(f"Chyba při čtení SQL: {e}")
        return pd.DataFrame()
    finally:
        conn.close()


# --- HLAVNÍ APLIKACE ---
def main():
    st.title("🏡 Příbram Real Estate Watchdog")

    # Získání cesty k DB z configu
    db_conn_str = CONFIG["database"]["connection_string"]
    db_file = get_db_path(db_conn_str)

    # Načtení dat
    df = load_data(db_file)

    if df.empty:
        st.warning("📭 Databáze je prázdná nebo neexistuje.")
        st.info("Tip: Spusť nejprve 'main.py' pro stažení dat.")
        return

    # --- SIDEBAR (Filtry) ---
    st.sidebar.header("🔍 Filtry")

    # Dynamické rozsahy podle dat
    max_land_val = int(df["land_m2"].max()) if not df.empty else 5000
    max_price_val = int(df["price"].max() / 1_000_000) + 1 if not df.empty else 20

    min_land = st.sidebar.slider(
        "Minimální pozemek (m²)",
        min_value=0,
        max_value=max_land_val,
        value=800,
        step=100,
    )

    max_price_mil = st.sidebar.slider(
        "Maximální cena (mil. Kč)",
        min_value=1.0,
        max_value=float(max_price_val),
        value=6.0,
        step=0.5,
    )
    max_price = max_price_mil * 1_000_000

    # --- FILTRACE DAT ---
    filtered_df = df[
        (df["land_m2"] >= min_land) & (df["price"] <= max_price)
    ].sort_values(by="price")

    # --- KPI METRIKY ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Počet nabídek", len(filtered_df))

    if not filtered_df.empty:
        min_price = filtered_df["price"].min()
        avg_price_m2_land = (filtered_df["price"] / filtered_df["land_m2"]).mean()

        col2.metric("Nejnižší cena", f"{min_price:,.0f} Kč".replace(",", " "))
        col3.metric(
            "Průměrná cena/m² pozemku", f"{avg_price_m2_land:,.0f} Kč".replace(",", " ")
        )
    else:
        col2.metric("Nejnižší cena", "-")
        col3.metric("Průměr", "-")

    # --- TABULKA ---
    st.subheader(f"Nalezené nemovitosti ({len(filtered_df)})")

    if not filtered_df.empty:
        display_df = filtered_df.copy()
        # Generování odkazu
        display_df["link"] = display_df["sreality_id"].apply(
            lambda x: f"https://sreality.cz/detail/prodej/dum/x/x/{x}"
        )

        st.dataframe(
            display_df[["title", "locality", "price", "land_m2", "link"]],
            column_config={
                "title": "Název",
                "locality": "Lokalita",
                "price": st.column_config.NumberColumn("Cena", format="%d Kč"),
                "land_m2": st.column_config.NumberColumn(
                    "Pozemek (m²)", format="%d m²"
                ),
                "link": st.column_config.LinkColumn("Odkaz"),
            },
            width="stretch",
            hide_index=True,
        )

        # --- GRAF ---
        st.subheader("📊 Analýza trhu (Cena vs. Pozemek)")
        st.scatter_chart(
            filtered_df,
            x="land_m2",
            y="price",
            size="land_m2",
            color="locality",
            height=500,
        )
    else:
        st.info("Žádné inzeráty neodpovídají filtrům.")


if __name__ == "__main__":
    main()
