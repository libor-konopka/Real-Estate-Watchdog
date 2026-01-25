import json
import logging
import os
import sys


def setup_logger():
    # 1. Zjištění absolutní cesty k rootu projektu
    # Soubor je v /src/logger.py, takže jdeme o dvě úrovně výš (..)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(current_dir)
    config_path = os.path.join(root_dir, "config.json")

    # Načtení configu
    if not os.path.exists(config_path):
        # Fallback pro případ katastrofy
        log_file = "pipeline.log"
        log_level = "INFO"
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        log_file = config["logging"]["file"]
        log_level = config["logging"]["level"]

    # 2. Sestavení cesty k log souboru (vždy absolutně k rootu)
    # Ošetřuje situaci, kdy je v configu "logs/pipeline.log"
    log_file_path = os.path.join(root_dir, log_file)

    # 3. Automatické vytvoření složky logs (pokud neexistuje)
    log_dir = os.path.dirname(log_file_path)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 4. Singleton Pattern (Zabrání duplicitním výpisům)
    logger = logging.getLogger("RealEstateWatchdog")
    if logger.hasHandlers():
        return logger

    logger.setLevel(getattr(logging, log_level.upper()))

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # File Handler
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console Handler (Explicitně na stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# 5. Vytvoření instance, kterou budou importovat ostatní moduly
logger = setup_logger()
