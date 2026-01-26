import os
import re
import sqlite3

import pandas as pd
import streamlit as st

# --- KONFIGURACE STRÁNKY ---
st.set_page_config(page_title="Real Estate Watchdog", page_icon="🏠", layout="wide")


# --- FUNKCE PRO NAČTENÍ DAT ---
def load_data():
    # Cesta k DB (robustní vůči spouštění z různých složek)
    db_path = "real_estate.db"

    if not os.path.exists(db_path):
        st.error(f"❌ Databáze '{db_path}' nenalezena. Spusť nejdřív 'main.py'!")
        return pd.DataFrame()

    conn = sqlite3.connect(db_path)

    # 1. SQL DOTAZ (Upravený pro novou strukturu)
    query = """
    SELECT 
        e.source,
        e.external_id,
        e.title, 
        e.locality, 
        e.url,
        p.price, 
        p.scraped_at
    FROM estates e
    JOIN prices p ON e.id = p.estate_id
    WHERE p.scraped_at = (
        -- Bereme jen nejnovější cenu
        SELECT MAX(scraped_at) FROM prices WHERE estate_id = e.id
    )
    ORDER BY p.scraped_at DESC
    """

    df = pd.read_sql(query, conn)
    conn.close()
    return df


# --- POMOCNÉ FUNKCE (Business Logic) ---
def parse_land_area(text):
    """Vytáhne velikost pozemku z textu (Bulletproof verze)."""
    if not isinstance(text, str):
        return None

    try:
        clean = text.replace("\xa0", "").replace(" ", "").replace(".", "")
        match = re.search(r"pozemek(\d+)m", clean, re.IGNORECASE)
        return int(match.group(1)) if match else None
    except Exception:
        return None


# --- HLAVNÍ APLIKACE ---
st.title("🏡 Real Estate Watchdog (Příbram)")
st.markdown("Přehled aktuálních inzerátů z Sreality (a dalších zdrojů).")

df = load_data()

if df.empty:
    st.warning("Zatím žádná data. Spusť pipeline!")
else:
    # 1. Transformace (Dopočítání sloupců)
    df["land_m2"] = df["title"].apply(parse_land_area)

    # 2. Metriky v záhlaví
    col1, col2, col3 = st.columns(3)
    col1.metric("Počet inzerátů", len(df))
    col2.metric("Průměrná cena", f"{df['price'].mean():,.0f} Kč".replace(",", " "))

    # Permakultura filtr (Pozemky > 1000 m2)
    perma_count = len(df[df["land_m2"] > 1000])
    col3.metric("Permakultura potenciál (>1000m²)", perma_count)

    st.divider()

    # 3. FILTRY (Sidebar)
    with st.sidebar:
        st.header("Filtrace")
        # Filtr podle ceny
        max_price = int(df["price"].max())
        price_limit = st.slider(
            "Maximální cena (Kč)", 0, max_price, 15_000_000, step=500_000
        )

        # Filtr podle zdroje (příprava do budoucna)
        sources = df["source"].unique()
        selected_source = st.multiselect("Zdroj dat", sources, default=sources)

    # Aplikace filtrů
    mask = (df["price"] <= price_limit) & (df["source"].isin(selected_source))
    display_df = df[mask].copy()

    # 4. HLAVNÍ TABULKA
    st.subheader("📋 Seznam nemovitostí")

    st.dataframe(
        display_df[["source", "title", "locality", "price", "land_m2", "url"]],
        column_config={
            "source": "Zdroj",
            "title": "Název",
            "locality": "Lokalita",
            "price": st.column_config.NumberColumn("Cena", format="%d Kč"),
            "land_m2": st.column_config.NumberColumn("Pozemek", format="%d m²"),
            "url": st.column_config.LinkColumn("Odkaz", display_text="Otevřít"),
        },
        width="stretch",  # Opravený warning
        hide_index=True,
    )

    # 5. Patička
    st.caption(f"Naposledy aktualizováno: {df['scraped_at'].max()}")
