# Real Estate Watchdog 🏠

Automatizovaný nástroj pro sledování a analýzu realitního trhu (Sreality).
Cílem projektu je identifikace podhodnocených nemovitostí pro permakulturní projekty (velký pozemek, nízká cena).

## Funkcionalita
* **ETL Pipeline:** Robustní stahování dat, ošetření duplicit (Upsert logika), handling API limitů.
* **Database:** Ukládání do relační databáze (SQLite/SQLAlchemy) s historií cen.
* **Analytics:** Skripty pro výpočet ceny za m² pozemku vs. užitné plochy.
* **Visualization:** Generování grafů pro identifikaci tržních příležitostí.

## Technologie
* Python 3.14
* SQLAlchemy (ORM)
* Pandas (Data Analysis)
* Matplotlib/Seaborn (Data Viz)

## Jak spustit
1. `pip install -r requirements.txt`
2. `python etl.py` (Stáhne data)
3. `python visualize_market.py` (Vygeneruje graf analýzy)