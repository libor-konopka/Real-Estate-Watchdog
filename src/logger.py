import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(module)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        # Výstup do konzole
        logging.StreamHandler(sys.stdout),
        # Výstup do souboru
        logging.FileHandler("logs/pipeline.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger("watchdog")
