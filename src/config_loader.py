import json
import os


def load_config(config_file="config.json"):
    # 1. Získáme absolutní cestu k tomuto skriptu (src/config_loader.py)
    current_script_path = os.path.abspath(__file__)

    # 2. Získáme složku, ve které skript leží (src/)
    src_dir = os.path.dirname(current_script_path)

    # 3. Jdeme o úroveň výš do rootu (rodič složky src)
    root_dir = os.path.dirname(src_dir)

    # 4. Sestavíme cestu k souboru v rootu
    config_path = os.path.join(root_dir, config_file)

    # Debugging: Kdyby to spadlo, ať víme, kde jsme hledali
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"❌ Config file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as file:
        return json.load(file)
