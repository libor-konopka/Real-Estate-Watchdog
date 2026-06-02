import json

import requests


def inspect_single_item() -> None:
    url = "https://www.sreality.cz/api/v1/estates/search"
    params = {
        "category_main_cb": 2,
        "category_type_cb": 1,
        "locality_country_id": 112,
        "locality_region_id": 11,
        "locality_district_id": 58,
        "limit": 1,  # Stačí nám jediný vzorek
        "offset": 0,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    response = requests.get(url, params=params, headers=headers)

    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        if results:
            item = results[0]
            print("📦 Anatomie nového inzerátu:")
            print(json.dumps(item, indent=2, ensure_ascii=False))
        else:
            print("Výsledky jsou prázdné.")


if __name__ == "__main__":
    inspect_single_item()
