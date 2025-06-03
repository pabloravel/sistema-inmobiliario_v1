# extract_mode.py

import re
import sys
from bs4 import BeautifulSoup

def extract_listing_mode(html):
    """
    Busca en todos los <script> del HTML un pattern "mode":"sell" o "mode":"rent".
    Devuelve 'sell', 'rent' o None si no encuentra nada.
    """
    soup = BeautifulSoup(html, 'html.parser')
    # Regex para buscar mode":"sell" o mode":"rent"
    mode_pattern = re.compile(r'"mode"\s*:\s*"(sell|rent)"', re.IGNORECASE)
    for script in soup.find_all('script'):
        text = script.get_text()
        match = mode_pattern.search(text)
        if match:
            return match.group(1).lower()
    return None

def main(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
    except FileNotFoundError:
        print(f"ERROR: no existe el archivo {path}")
        sys.exit(1)

    mode = extract_listing_mode(html)
    print(f"File: {path}")
    print("Detected listing mode:", mode or "NOT FOUND")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python extract_mode.py <archivo.html>")
        sys.exit(1)
    main(sys.argv[1])