#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# scraper_playwright_con_rentas.py
# Playwright + Chromium visible con fb_state.json para sesión

import sys
import json
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ——————————————————————————————————————————————————————————————————————
# Verificación mínima de Python
MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    sys.exit(f"ERROR: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ requerido.")

# ——————————————————————————————————————————————————————————————————————
# Ruta a tu archivo de estado de sesión de Facebook (login)
STATE_FILE = Path("fb_state.json")
if not STATE_FILE.exists():
    sys.exit("ERROR: No encontré fb_state.json. Genera tu estado de sesión con Playwright.")

# ——————————————————————————————————————————————————————————————————————
# Endpoints de VENTA (tu original)
CIUDADES_VENTA = {
    "Cuernavaca": {"general": "https://www.facebook.com/marketplace/cuernavaca/propertyforsale"},
    "Jiutepec":   {"general": "https://www.facebook.com/marketplace/107963212565853/propertyforsale"},
    "Temixco":    {"general": "https://www.facebook.com/marketplace/108039299223018/propertyforsale"},
}

# Parámetros de RENTAS
RENTAL_QUERIES = [
    (18.9242, -99.2216, "cuernavaca", 0, 200000),
    (18.8832, -99.1669, "jiutepec",   0, 200000),
    (18.8455, -99.2235, "temixco",    0, 200000),
]
BAD_KEYWORDS = {"moto", "reloj", "ropa", "celulares"}

# Repositorio de links
OUT_DIR    = Path("resultados") / "links"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE   = OUT_DIR / "repositorio_unico.json"

def load_existing():
    if not OUT_FILE.exists():
        return set()
    return set(json.loads(OUT_FILE.read_text(encoding="utf-8")))

def save_existing(s):
    with OUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(sorted(s), f, ensure_ascii=False, indent=2)

def extract_items(page):
    lst = page.evaluate("""
        () => Array.from(
            document.querySelectorAll('a[href*="/marketplace/item/"]'),
            a => a.href
        )
    """)
    return [u for u in set(lst) if not any(b in u.lower() for b in BAD_KEYWORDS)]

def rental_urls():
    urls = []
    for lat, lng, city, pmin, pmax in RENTAL_QUERIES:
        urls.append(
            f"https://www.facebook.com/marketplace/{city}/propertyrentals"
            f"?exact=false&latitude={lat}&longitude={lng}"
            f"&radius=16&minPrice={pmin}&maxPrice={pmax}"
        )
    return urls

def main():
    print(f"🚀 Inicio — {datetime.now():%Y-%m-%d %H:%M:%S}")
    existing = load_existing()
    all_links = set(existing)

    with sync_playwright() as pw:
        # Lanzar Chromium en visible
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(storage_state=str(STATE_FILE))
        page = context.new_page()

        # 1) Venta
        for city, endpoints in CIUDADES_VENTA.items():
            print(f"\n🌎 Ventas en {city}")
            for label, url in endpoints.items():
                print(f"  ↪ {label}: {url}")
                page.goto(url, timeout=60000)
                page.wait_for_timeout(2000)
                found = extract_items(page)
                added = sum(1 for u in found if u not in all_links)
                all_links.update(found)
                print(f"    ✅ Añadidos: {added}")

        # 2) Renta
        print("\n🔄 Rentas (0–200k)")
        for url in rental_urls():
            print(f"  ↪ Renta: {url}")
            page.goto(url, timeout=60000)
            page.wait_for_timeout(2000)
            found = extract_items(page)
            added = sum(1 for u in found if u not in all_links)
            all_links.update(found)
            print(f"    ✅ Añadidos: {added}")

        context.close()
        browser.close()

    save_existing(all_links)
    print(f"\n🎉 Total links: {len(all_links)} guardados en {OUT_FILE}")

if __name__ == "__main__":
    main()