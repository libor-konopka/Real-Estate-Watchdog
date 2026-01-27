import asyncio
import sys

import aiohttp

# Importy z našeho balíčku
from src.config_loader import load_config
from src.extract import IdnesScraper, SrealityScraper
from src.load import Loader
from src.logger import logger
from src.transform import Transformer


async def run_extraction(config):
    """Spustí oba scrapery PARALELNĚ."""
    scrapers = [SrealityScraper(config), IdnesScraper(config)]

    all_results = []

    # Jedna session pro všechny requesty (efektivnější)
    async with aiohttp.ClientSession() as session:
        # Vytvoříme 'tasky' pro spuštění
        tasks = [scraper.scrape(session) for scraper in scrapers]

        # Spustíme je naráz a čekáme, až doběhnou všechny
        results_list = await asyncio.gather(*tasks)

        # Sloučíme výsledky ze všech zdrojů do jednoho seznamu
        for res in results_list:
            all_results.extend(res)

    return all_results


def main():
    logger.info("🚀 PIPELINE STARTED (Async Mode)")

    try:
        # 1. Konfigurace
        config = load_config()

        # 2. Extract (Async)
        # Musíme použít asyncio.run pro spuštění async funkce v sync světě
        raw_data = asyncio.run(run_extraction(config))

        if not raw_data:
            logger.warning("⚠️ Žádná data nebyla stažena.")
            return

        # 3. Transform (Sync)
        # Transformace je CPU-bound, tam async tolik nepomůže, stačí sync
        clean_data = Transformer.transform(raw_data)

        # 4. Load (Sync)
        # SQLite nemá rádo async zápisy z více vláken, držíme to sync
        loader = Loader(config)
        loader.load(clean_data)

        logger.info("🏁 PIPELINE FINISHED SUCCESSFULLY")

    except Exception as e:
        logger.critical(f"🔥 FATAL ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
