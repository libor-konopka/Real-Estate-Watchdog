import json
import os


def load_config(path="config.json"):
    # Získáme absolutní cestu k adresáři, kde leží tento skript
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, path)

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"❌ Config file not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)
