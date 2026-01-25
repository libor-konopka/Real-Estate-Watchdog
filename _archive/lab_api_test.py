import json

import requests

# 1. URL z tvého prohlížeče (API endpoint s filtry)
# Příklad: Hledání domů v Příbrami
url = "https://www.sreality.cz/api/cs/v2/estates?category_main_cb=2&category_type_cb=1&locality_district_id=36&per_page=20"

# 2. Hlavičky (Maskování)
# Tohle je klíčové. Bez 'User-Agent' nás server pozná jako bota a zablokuje.
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
}

try:
    # 3. Odeslání požadavku
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Vyhodí chybu, pokud není status 200 OK

    # 4. Parsování JSONu
    data = response.json()

    # 5. Výpis pro kontrolu
    # Vypíšeme jen první inzerát, abychom viděli strukturu
    print(f"Nalezeno celkem inzerátů: {data.get('result_size')}")

    if "_embedded" in data and "estates" in data["_embedded"]:
        first_estate = data["_embedded"]["estates"][0]
        print("\n--- První inzerát ---")
        print(f"Název: {first_estate.get('name')}")
        print(f"Cena: {first_estate.get('price_czk')} Kč")
        print(f"Lokalita: {first_estate.get('locality')}")

        # Uložíme si vzorek JSONu do souboru pro analýzu
        with open("sample_data.json", "w", encoding="utf-8") as f:
            json.dump(first_estate, f, indent=4, ensure_ascii=False)
        print("\n✅ Vzorek dat uložen do sample_data.json")

    else:
        print("⚠️ JSON má jinou strukturu, než jsme čekali.")
        print(data.keys())

except requests.exceptions.RequestException as e:
    print(f"❌ Chyba při stahování: {e}")
