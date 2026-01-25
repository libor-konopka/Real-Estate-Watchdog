import time

import requests

# Hlavičky jako prohlížeč
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

print("🕵️‍♂️ Spouštím skener okresů (ID 1-80)...")

# Projedeme IDs od 1 do 80
for district_id in range(1, 81):
    # Stáhneme jen 1 inzerát pro dané ID, abychom zjistili lokalitu
    url = f"https://www.sreality.cz/api/cs/v2/estates?category_main_cb=2&category_type_cb=1&locality_district_id={district_id}&per_page=1"

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data["result_size"] > 0:
                first_estate = data["_embedded"]["estates"][0]
                # Vypíšeme ID a lokalitu
                print(f"🆔 {district_id:02d} -> {first_estate['locality']}")

                # Pokud najdeme Příbram, rovnou to stopneme a zvýrazníme
                if "Příbram" in first_estate["locality"]:
                    print(f"\n🎯 NALEZENO! ID pro Příbram je: {district_id}")
                    print("--------------------------------------------------")
                    break
            else:
                pass  # Prázdný region (žádné inzeráty)
        else:
            pass  # Chyba API

    except Exception:
        pass  # Ignorujeme chyby sítě

    # Malá pauza, ať neshodíme API
    time.sleep(0.1)

print("🏁 Skener dokončen.")
