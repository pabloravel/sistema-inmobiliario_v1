# extract_full_json.py

import re
import json
import sys
from bs4 import BeautifulSoup

def extract_preloaded_json(html):
    """
    Busca en los <script> el bloque window.__PRELOADED_STATE__ = { ... };
    Devuelve ese objeto JSON como dict, o None si no lo encuentra.
    """
    soup = BeautifulSoup(html, 'html.parser')
    # Regex para capturar window.__PRELOADED_STATE__ = {...};
    pattern = re.compile(r'window\.__PRELOADED_STATE__\s*=\s*({.*?});\s*\n', re.DOTALL)
    for script in soup.find_all('script'):
        text = script.string or ''
        match = pattern.search(text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError as e:
                print("Error parseando JSON:", e)
                return None
    return None

def main(html_path):
    # 1) Carga del HTML
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # 2) Extracción del JSON completo
    data = extract_preloaded_json(html)
    if not data:
        print("No se encontró window.__PRELOADED_STATE__ en el HTML.")
        sys.exit(1)

    # 3) Guarda el JSON en un archivo para inspección manual
    out_path = 'preloaded.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"JSON completo volc    ado a {out_path}")

    # 4) Si existe 'listing' dentro, muéstralo y su modo
    listing = data.get('listing') or data.get('marketplace') or {}
    mode = listing.get('mode')
    print("Extracted listing object:")
    print(json.dumps(listing, indent=2, ensure_ascii=False))
    print("Detected listing.mode =", mode)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python extract_full_json.py <archivo.html>")
        sys.exit(1)
    main(sys.argv[1])