import os
import sys

# Přidáme aktuální adresář do cesty, aby Python viděl balíček 'src'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config_loader import load_config  # Helper funkce (vytvoříme níže)
from src.extract import SrealityExtractor
from src.load import Loader
from src.logger import logger
from src.transform import Transformer


def main():
    logger.info("🚀 START: Spouštím Real Estate Watchdog Pipeline")

    # 1. Načtení konfigurace
    try:
        config = load_config()
    except Exception as e:
        logger.critical(f"Chyba konfigurace: {e}")
        return

    # 2. Dependency Injection (Příprava nástrojů)
    extractor = SrealityExtractor(config["sreality"])
    loader = Loader(config["database"]["connection_string"])

    # 3. ETL Proces
    try:
        # A) EXTRACT
        logger.info("--- Fáze 1: Extraction ---")
        raw_data = extractor.extract()
        logger.info(f"Staženo {len(raw_data)} položek.")

        if not raw_data:
            logger.warning("Žádná data ke zpracování. Končím.")
            return

        # B) TRANSFORM
        logger.info("--- Fáze 2: Transformation ---")
        clean_data = Transformer.transform(raw_data)
        logger.info(f"Zvalidováno {len(clean_data)} položek.")

        # C) LOAD
        logger.info("--- Fáze 3: Loading ---")
        loader.load(clean_data)

        logger.info("✅ SUCCESS: Pipeline úspěšně dokončena.")

    except Exception as e:
        logger.critical(f"🔥 FATAL ERROR: Pipeline spadla: {e}")
        raise e


if __name__ == "__main__":
    main()
