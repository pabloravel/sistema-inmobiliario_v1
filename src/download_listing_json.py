# download_listing_json.py

import re
import json
import sys
import requests
from bs4 import BeautifulSoup

def extract_listing_data(html):
    """
    Extrae el objeto JSON bajo "listing": { ... } del HTML.
    """
    soup = BeautifulSoup(html, 'html.parser')
    pattern = re.compile(r'"listing":\s*({.*?})', re.DOTALL)
    for script in soup.find_all('script'):
        text = script.get_text()
        m = pattern.search(text)
        if m:
            fragment = '{' + m.group(1) + '}'
            try:
                return json.loads(fragment)
            except json.JSONDecodeError:
                continue
    return None

def main(url):
    print(f"Descargando página…")
    resp = requests.get(url)
    resp.raise_for_status()
    listing = extract_listing_data(resp.text)
    if not listing:
        print("❌ No encontré el objeto listing en esa página.")
        sys.exit(1)
    # Guardar solo el fragmento listing
    with open('listing.json', 'w', encoding='utf-8') as f:
        json.dump(listing, f, ensure_ascii=False, indent=2)
    print("✅ He creado `listing.json` con el contenido de `listing`:\n")
    print(json.dumps(listing, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    if len(sys.argv)!=2:
        print("Uso: python download_listing_json.py <URL_de_la_publicación>")
        sys.exit(1)
    main(sys.argv[1])