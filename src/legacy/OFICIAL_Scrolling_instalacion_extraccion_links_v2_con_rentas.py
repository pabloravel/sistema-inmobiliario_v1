#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OFICIAL_Scrolling_instalacion_extraccion_links_v2_con_rentas.py

Tu versión estable de extracción de links de Facebook Marketplace,
que crea la carpeta de resultados con la fecha, verifica el repositorio
 de links, hace scrolling en oferta y rentas, y guarda todo en
resultados/links/repositorio_unico.json sin barras de progreso extra.
Se han restaurado las impresiones de progreso y de nuevos links.
"""

import sys
import os
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright

# ---------- Auto-verificación de entorno virtual ----------
MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    sys.exit(f"ERROR: Requiere Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")

in_venv = (
    hasattr(sys, 'real_prefix')
    or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    or bool(os.environ.get('VIRTUAL_ENV'))
)
if not in_venv:
    print("⚠️ No estás en venv. Creando uno en ./venv...")
    subprocess.check_call([sys.executable, "-m", "venv", "venv"])
    python_exec = "venv/bin/python" if os.name == 'posix' else "venv\\Scripts\\python.exe"
    os.execvp(python_exec, [python_exec] + sys.argv)

# ---------- Chequeo de dependencias ----------
REQUIRED = ["playwright", "time", "json", "logging"]
missing = []
for pkg in REQUIRED:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)
if missing:
    print("ERROR: Faltan dependencias:", ", ".join(missing))
    sys.exit(1)

# ─── Parámetros y rutas ────────────────────────────────────────
BASE_URL      = "https://www.facebook.com"
STATE_FILE    = "fb_state.json"
LINKS_REPO    = Path("resultados/links/repositorio_unico.json")
RESULTS_LINKS = Path("resultados/links")
RESULTS_LINKS.mkdir(parents=True, exist_ok=True)
TODAY         = datetime.now().strftime("%Y-%m-%d")

# ─── Carga repositorio existente ──────────────────────────────
repositorio_links = set()
if LINKS_REPO.exists():
    with open(LINKS_REPO, "r", encoding="utf-8") as f:
        prev = json.load(f)
        for item in prev:
            href = item if isinstance(item, str) else item.get("link") or item.get("url") or item.get("href") or ''
            repositorio_links.add(href.split("?")[0])

# ─── Función de extracción ─────────────────────────────────────
def extract_links_from(page):
    nuevos = set()
    elems = page.query_selector_all("a[href*='/marketplace/item/']")
    for el in elems:
        href = el.get_attribute("href")
        if href:
            clean = href.split("?")[0]
            if clean not in repositorio_links:
                nuevos.add(clean)
    return nuevos

# ─── Función que recorre URLs de una ciudad ────────────────────
def extraer_links_ciudad(ciudad, enlaces):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    salida = RESULTS_LINKS / f"links_extraidos_{ciudad.lower()}_{timestamp}.json"
    nuevos_links = set()
    print(f"\n🌎 Comenzando {ciudad} — {len(enlaces)} URLs por procesar")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()
        for etiqueta, url in enlaces.items():
            print(f"⏮ [{etiqueta}] {url}")
            page.goto(url)
            time.sleep(4)
            sin_nuevos = 0
            scroll_count = 0
            while sin_nuevos < 5:
                scroll_count += 1
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                print(f"  🔄 Scroll {scroll_count}")
                time.sleep(4)
                found = extract_links_from(page)
                if not found:
                    sin_nuevos += 1
                    print(f"    ⚠️ Sin nuevos links (intento {sin_nuevos})")
                else:
                    for link in sorted(found):
                        print(f"    ✅ Nuevo link: {link}")
                    # Evitar re-detección en scrolls posteriores
                    repositorio_links.update(found)
                    nuevos_links |= found
                    sin_nuevos = 0
            print(f"  ✔️ Fin scrolling [{etiqueta}], nuevos en esta URL: {len(nuevos_links)}")
        browser.close()

    with open(salida, "w", encoding="utf-8") as f:
        json.dump(sorted(nuevos_links), f, ensure_ascii=False, indent=2)
    print(f"🎯 Guardados {len(nuevos_links)} links de {ciudad} en {salida}")
    return nuevos_links

# ─── Main ──────────────────────────────────────────────────────
def main():
    print(f"🚀 Iniciando extracción de links — Corrida {TODAY}")
    ciudades = {
        "Cuernavaca": {
            "venta_general":           f"{BASE_URL}/marketplace/cuernavaca/propertyforsale",
            "venta_0_5500000":         f"{BASE_URL}/marketplace/cuernavaca/propertyforsale?minPrice=0&maxPrice=5500000",
            "venta_5500001_10500000":  f"{BASE_URL}/marketplace/cuernavaca/propertyforsale?minPrice=5500001&maxPrice=10500000",
            "venta_10500001_15000000": f"{BASE_URL}/marketplace/cuernavaca/propertyforsale?minPrice=10500001&maxPrice=15000000",
        },
        "Jiutepec": {
            "venta_general":           f"{BASE_URL}/marketplace/107963212565853/propertyforsale",
            "venta_0_5500000":         f"{BASE_URL}/marketplace/107963212565853/propertyforsale?minPrice=0&maxPrice=5500000",
            "venta_5500001_10500000":  f"{BASE_URL}/marketplace/107963212565853/propertyforsale?minPrice=5500001&maxPrice=10500000",
            "venta_10500001_15000000": f"{BASE_URL}/marketplace/107963212565853/propertyforsale?minPrice=10500001&maxPrice=15000000",
        },
        "Temixco": {
            "venta_general":           f"{BASE_URL}/marketplace/108039299223018/propertyforsale",
            "venta_0_5500000":         f"{BASE_URL}/marketplace/108039299223018/propertyforsale?minPrice=0&maxPrice=5500000",
            "venta_5500001_10500000":  f"{BASE_URL}/marketplace/108039299223018/propertyforsale?minPrice=5500001&maxPrice=10500000",
            "venta_10500001_15000000": f"{BASE_URL}/marketplace/108039299223018/propertyforsale?minPrice=10500001&maxPrice=15000000",
        }
    }

    total_nuevos = 0
    # Primero ventas
    for ciudad, enlaces in ciudades.items():
        nuevos = extraer_links_ciudad(ciudad, enlaces)
        repositorio_links.update(nuevos)
        total_nuevos += len(nuevos)

    # Luego rentas
    print(f"\n🔄 Ahora extrayendo rentas (0–200000) para las ciudades")
    rent_urls = {
        "Cuernavaca": f"{BASE_URL}/marketplace/cuernavaca/propertyrentals?exact=false&latitude=18.9242&longitude=-99.2216&radius=16&minPrice=0&maxPrice=200000",
        "Jiutepec":   f"{BASE_URL}/marketplace/107963212565853/propertyrentals?exact=false&latitude=18.8832&longitude=-99.1669&radius=16&minPrice=0&maxPrice=200000",
        "Temixco":    f"{BASE_URL}/marketplace/108039299223018/propertyrentals?exact=false&latitude=18.8455&longitude=-99.2235&radius=16&minPrice=0&maxPrice=200000"
    }
    for ciudad, url in rent_urls.items():
        nuevos = extraer_links_ciudad(ciudad, {"renta_0_200000": url})
        repositorio_links.update(nuevos)
        total_nuevos += len(nuevos)

    # Guardar repositorio final
    with open(LINKS_REPO, "w", encoding="utf-8") as f:
        json.dump(sorted(repositorio_links), f, ensure_ascii=False, indent=2)
    print(f"\n🎉 Total links únicos extraídos: {len(repositorio_links)} (nuevos: {total_nuevos})")
    print(f"📦 Repositorio actualizado → {LINKS_REPO}")

if __name__ == "__main__":
    main()
