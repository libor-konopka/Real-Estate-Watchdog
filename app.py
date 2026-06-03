import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine

# --- 1. UKOTVENÍ PROSTORU A ENERGIE ---
# Cesta do src pro načtení konfigurace
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

try:
    from src.settings import get_settings
except ImportError:
    st.error("❌ Chyba: Nemohu najít src.settings. Zkontroluj strukturu projektu.")
    st.stop()


# --- 2. CACHOVANÉ NAČÍTÁNÍ HMOTY (Optimalizace) ---
# Streamlit spouští skript znovu při každé interakci. @st.cache_data zajistí,
# že do databáze sáhneme jen jednou, dokud se data nezmění.
@st.cache_data(ttl=3600)  # Data žijí v mezipaměti 1 hodinu
def load_data() -> pd.DataFrame:
    settings = get_settings()
    engine = create_engine(settings.database.connection_string)

    query = """
    SELECT
        e.source, e.external_id, e.title, e.locality, e.url, p.price
    FROM estates e
    JOIN prices p ON e.id = p.estate_id
    WHERE p.scraped_at = (
        SELECT MAX(scraped_at) FROM prices WHERE estate_id = e.id
    )
    """
    with engine.connect() as conn:
        df = pd.read_sql(query, conn)

    # Rychlá vektorová extrakce velikosti pozemku (z předchozích analýz)
    clean_titles = df["title"].str.replace(r"[\xa0 \.]", "", regex=True)
    df["land_m2"] = clean_titles.str.extract(r"(?i)pozemek(\d+)m")[0].astype(float)
    df["price_per_m2"] = df["price"] / df["land_m2"]

    return df


# --- 3. UI A ROZVRŽENÍ ---
st.set_page_config(page_title="Real-Estate Watchdog", page_icon="🏠", layout="wide")
st.title("🌱 Permakulturní Radar (Real-Estate Watchdog)")

# Načtení dat
with st.spinner("Stahuji aktuální energii trhu..."):
    df_raw = load_data()

if df_raw.empty:
    st.warning("Databáze je prázdná. Spusť nejprve proces stahování (main.py).")
    st.stop()

# --- 4. INTERAKTIVNÍ FILTRY (Sidebar) ---
st.sidebar.header("Filtry pro tvou vizi")

# Rozsahy pro slidery
min_price, max_price = int(df_raw["price"].min()), int(df_raw["price"].max())
min_land, max_land = 0, int(df_raw["land_m2"].max() or 10000)

# Uživatelské vstupy
price_range = st.sidebar.slider(
    "Cenové rozpětí (Kč)",
    min_value=min_price,
    max_value=max_price,
    value=(100000, 5000000),
    step=100000,
)

# Chceme pozemky pro permakulturu, takže nastavíme smysluplný základ (např. 1000 m2)
land_range = st.sidebar.slider(
    "Velikost pozemku (m²)",
    min_value=min_land,
    max_value=max_land,
    value=(1000, max_land),
    step=100,
)

only_with_land = st.sidebar.checkbox(
    "Zobrazit pouze inzeráty s rozlohou pozemku", value=True
)

# --- 5. APLIKACE FILTRŮ ---
mask = (df_raw["price"] >= price_range[0]) & (df_raw["price"] <= price_range[1])

if only_with_land:
    mask = (
        mask
        & (df_raw["land_m2"].notna())
        & (df_raw["land_m2"] >= land_range[0])
        & (df_raw["land_m2"] <= land_range[1])
    )

df_filtered = df_raw[mask].copy()

# --- 6. MANIFESTACE (Zobrazení výsledků) ---
st.subheader(f"Nalezeno: {len(df_filtered)} inzerátů splňujících tvé vize")

# Formátování tabulky pro čistší vzhled
if not df_filtered.empty:
    # Seřazení od nejlepší ceny za m2
    df_display = df_filtered.sort_values("price_per_m2", ascending=True)

    # Vybereme jen to důležité a přejmenujeme pro UI
    df_display = df_display[
        ["title", "locality", "price", "land_m2", "price_per_m2", "url"]
    ]
    df_display.columns = [
        "Titulek",
        "Lokalita",
        "Cena (Kč)",
        "Pozemek (m²)",
        "Cena za m²",
        "Odkaz",
    ]

    # Zobrazení pomocí Streamlit Dataframe (umožňuje řazení kliknutím)
    st.dataframe(
        df_display,
        column_config={
            "Cena (Kč)": st.column_config.NumberColumn(format="%d Kč"),
            "Cena za m²": st.column_config.NumberColumn(format="%d Kč"),
            "Odkaz": st.column_config.LinkColumn("Otevřít inzerát"),
        },
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("Žádné inzeráty neodpovídají tvému nastavení. Zkus uvolnit filtry.")
