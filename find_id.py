import requests

# Hledáme frázi "Příbram"
url = "https://www.sreality.cz/api/cs/v2/suggest?phrase=Příbram"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers)
    data = response.json()

    print("--- VÝSLEDKY HLEDÁNÍ ---")
    # API vrací různé typy (obce, okresy, ulice). Nás zajímá "district" (okres).
    for item in data["results"]:
        typ = item["category"]
        nazev = item["userData"]["suggestTitle"]
        id_lokality = item["userData"]["id"]

        print(f"Typ: {typ} | Název: {nazev} | ID: {id_lokality}")

except Exception as e:
    print(e)
