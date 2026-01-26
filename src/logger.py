import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from .config_loader import load_config

# Načtení konfigurace
config = load_config()
log_cfg = config.get("logging", {})

# 1. Získání cesty a Levelu
log_path = log_cfg.get("file", "logs/pipeline.log")
log_level = log_cfg.get("level", "INFO").upper()

# 2. Bezpečné vytvoření složky (Critical fix)
# Pokud složka 'logs' neexistuje, vytvoříme ji. Jinak by to spadlo.
log_dir = os.path.dirname(log_path)
if log_dir and not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 3. Nastavení Loggeru
logger = logging.getLogger("RealEstateScraper")
logger.setLevel(log_level)

# Zabráníme duplicitním logům (pokud by se modul načetl 2x)
if not logger.hasHandlers():
    # Formátování: Čas - Level - Zpráva
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # A) Handler pro SOUBOR (s rotací)
    # maxBytes=2MB, backupCount=5 (držíme posledních 5 souborů)
    # encoding='utf-8' je nutnost pro Windows a české znaky!
    file_handler = RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # B) Handler pro KONZOLI (Terminál)
    # Abychom viděli progres i při spuštění, nejen v souboru
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

# Abychom mohli importovat 'logger' přímo
__all__ = ["logger"]
