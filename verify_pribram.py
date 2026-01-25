import requests

# Zkoušíme ID 41 (Teoreticky Okres Příbram)
url = "https://www.sreality.cz/api/cs/v2/estates?category_main_cb=2&category_type_cb=1&locality_district_id=41&per_page=1"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers)
    data = response.json()

    first_estate = data["_embedded"]["estates"][0]
    print("--- TEST ID 41 ---")
    print(f"Název: {first_estate['name']}")
    print(f"Lokalita: {first_estate['locality']}")

    if (
        "Příbram" in first_estate["locality"]
        or "okres Příbram" in first_estate["locality"]
    ):
        print("\n✅ BINGO! ID 41 je Příbram.")
    else:
        print("\n❌ Vedle. ID 41 není Příbram.")

except Exception as e:
    print(f"Chyba: {e}")
