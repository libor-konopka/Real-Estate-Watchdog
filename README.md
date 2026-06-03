# Real-Estate Watchdog 🏠

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Code style: PEP 8](https://img.shields.io/badge/code%20style-PEP%208-black.svg)](https://peps.python.org/pep-0008/)

**Real-Estate Watchdog** je automatizovaná asynchronní ETL pipeline pro agregaci, čištění a analýzu dat z českých realitních portálů (Sreality, iDnes).

Původně navržen jako osobní nástroj pro detekci podhodnocených pozemků vhodných pro **permakulturní soběstačnost**, systém se architektonicky vyvinul do robustního řešení s využitím moderních best practices datového inženýrství.

---

## 🏗 Architektura & Technologie

Projekt striktně dodržuje oddělení zodpovědností (Separation of Concerns) a využívá čistý, typovaný přístup (Type Hinting).

* **Extrakce (Async):** `aiohttp` & `BeautifulSoup4` pro bleskurychlý a neblokující sběr dat z vícero portálů současně.
* **Transformace (DTO & Validace):** `Pydantic V2` slouží jako neprostupná membrána pro validaci, sanitaci a normalizaci datových toků.
* **Ukládání (ORM & Persistence):** `SQLAlchemy 2.0` pro bezpečný zápis do relační struktury (SQLite) využívající kompozitní klíče a ochranu proti duplicitám (UPSERT logika).
* **Konfigurace (Singleton):** Centralizovaná správa přes Pydantic modely (čtení z `config.json`).
* **Analytika (Vektorizace):** Nativní vektorové operace v `Pandas` napojené přímo na SQLAlchemy engine (odklon od pomalých iterací).
* **Vizualizace:** `Seaborn` a `Matplotlib` pro grafickou manifestaci datových uzlů.

---

## 🚀 Jak systém nasadit a spustit

### 1. Inicializace prostředí
Systém vyžaduje čisté ukotvení. Vytvoř složku pro databázi a nainstaluj závislosti.
```bash
# Naklonování repozitáře
git clone [https://github.com/libor-konopka/Real-Estate-Watchdog.git](https://github.com/libor-konopka/Real-Estate-Watchdog.git)
cd Real-Estate-Watchdog

# Stvoření prostoru pro uložení hmoty (databáze)
mkdir data

# Vytvoření virtuálního prostředí a instalace
python -m venv .venv
# Windows aktivace: .venv\Scripts\activate
# Linux/Mac aktivace: source .venv/bin/activate
pip install -r requirements.txt
