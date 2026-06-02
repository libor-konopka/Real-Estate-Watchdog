"""
Hlavní orchestrátor datové pipeline (Real-Estate-Watchdog).
Spouští asynchronní extrakci, synchronní transformaci a uložení do databáze.
"""

import asyncio
import itertools
import sys
from typing import Any, Dict, List

import aiohttp

from src.extract import IdnesScraper, SrealityScraper
from src.load import Loader
from src.logger import logger
from src.settings import AppConfig
from src.transform import Transformer


async def run_extraction(config: AppConfig) -> List[Dict[str, Any]]:
    """Spustí datové extraktory paralelně a sloučí jejich energetické toky."""
    scrapers = [SrealityScraper(config), IdnesScraper(config)]

    # Sdílená TCP session pro minimalizaci síťové režie
    async with aiohttp.ClientSession() as session:
        tasks = [scraper.scrape(session) for scraper in scrapers]
        results_list = await asyncio.gather(*tasks)

    # Nízkoúrovňové (C) splynutí toků bez paměťové alokace navíc
    return list(itertools.chain.from_iterable(results_list))


def main() -> None:
    """Řídí životní cyklus celé aplikace."""
    logger.info("🚀 PIPELINE STARTED (Async Mode)")

    try:
        # --- FÁZE 1: INICIALIZACE ---
        config = AppConfig.load("config.json")

        # --- FÁZE 2: EXTRAKCE (Async) ---
        run_kwargs = {}
        if sys.platform == "win32":
            # Ochrana před konflikty Windows Event Loopu v Pythonu 3.14+
            run_kwargs["loop_factory"] = asyncio.SelectorEventLoop

        raw_data = asyncio.run(run_extraction(config), **run_kwargs)

        if not raw_data:
            logger.warning("⚠️ Žádná data nebyla stažena. Ukončuji tok.")
            return

        # --- FÁZE 3: TRANSFORMACE (Sync) ---
        clean_data = Transformer.transform(raw_data)

        # --- FÁZE 4: ULOŽENÍ (Sync) ---
        loader = Loader(config)
        loader.load(clean_data)

        logger.info("🏁 PIPELINE FINISHED SUCCESSFULLY")

    except Exception:
        # Automaticky zaznamená i kompletní stack trace pro snazší diagnostiku
        logger.exception("🔥 FATAL ERROR: Zhroucení hlavního toku")
        sys.exit(1)


if __name__ == "__main__":
    main()
