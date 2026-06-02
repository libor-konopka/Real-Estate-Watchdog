import requests


def verify_source() -> None:
    """Izolovaný test čisté dostupnosti Sreality API."""
    url = "https://www.sreality.cz/api/cs/v2/estates"
    params = {
        "category_main_cb": 2,
        "category_type_cb": 1,
        "locality_district_id": 58,
        "per_page": 60,
        "page": 1,
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    print("📡 Zkoumám aktuální odezvu prostředí...")
    response = requests.get(url, params=params, headers=headers)

    print(f"Status kód: {response.status_code}")
    print(f"Výsledná URL: {response.url}")

    if response.status_code == 200:
        print("✅ API dýchá. Tvar dotazu je správný, problém leží v aiohttp.")
    elif response.status_code == 404:
        print("❌ 404: Původní cesta zanikla. Parametry nebo endpoint se změnily.")
    else:
        print(f"⚠️ Neočekávaná anomálie: {response.status_code}")


if __name__ == "__main__":
    verify_source()
