#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG_Scrolling_extraccion_links.py

Versión de depuración del extractor de links de Facebook Marketplace,
con scrolling en oferta y rentas, captura de título para depuración,
y guardado en resultados/links con limpieza de parámetros.

Ahora imprime:
- Número de nuevos links por ciudad/etiqueta.
- Qué “página” de scroll (iteración) se está procesando.
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
    hasattr(sys, 'real_prefix') or
    (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
    bool(os.environ.get('VIRTUAL_ENV'))
)
if not in_venv:
    print("⚠️ No estás en venv. Creando uno...")
    subprocess.check_call([sys.executable, "-m", "venv", "venv"])
    python_exec = os.path.join(os.getcwd(), 'venv', 'bin', 'python') if os.name=='posix' else os.path.join(os.getcwd(), 'venv', 'Scripts', 'python.exe')
    os.execvp(python_exec, [python_exec] + sys.argv)

# ---------- Dependencias ----------
REQUIRED = ["playwright"]
missing = []
for pkg in REQUIRED:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)
if missing:
    print("ERROR: faltan dependencias:", ", ".join(missing))
    sys.exit(1)

# Parámetros y rutas
BASE_URL      = "https://www.facebook.com"
STATE_FILE    = "fb_state.json"
LINKS_REPO    = Path("resultados/links/repositorio_unico.json")
RESULTS_LINKS = Path("resultados/links")
RESULTS_LINKS.mkdir(parents=True, exist_ok=True)
TODAY         = datetime.now().strftime("%Y-%m-%d")

# Carga repositorio existente
repositorio_links = set()
if LINKS_REPO.exists():
    for item in json.loads(LINKS_REPO.read_text(encoding='utf-8')):
        href = item['link'] if isinstance(item, dict) else item
        repositorio_links.add(href.split('?')[0])

# Extrae links y título del elemento
def extract_links_from(page):
    nuevos = []
    elems = page.query_selector_all("a[href*='/marketplace/item/']")
    for el in elems:
        href = el.get_attribute('href') or ''
        clean = href.split('?')[0]
        if clean not in repositorio_links and not any(d['link']==clean for d in nuevos):
            title = el.text_content().strip().replace('\n',' ')[:80]
            nuevos.append({'link': clean, 'title': title})
    return nuevos

# Scrolling por ciudad
def extract_and_debug_links(ciudad, enlaces):
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    salida = RESULTS_LINKS / f"debug_links_{ciudad.lower()}_{timestamp}.json"
    todos_nuevos = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STATE_FILE)
        page = context.new_page()
        for etiqueta, url in enlaces.items():
            print(f"\n🌎 Abriendo {ciudad} [{etiqueta}]: {url}")
            page.goto(url)
            time.sleep(4)

            page_num = 1  # ← NUEVO: contador de "páginas" de scroll
            nuevos_totales_etiqueta = 0  # ← NUEVO: contador nuevos por etiqueta
            intentos = 0

            while intentos < 5:
                print(f"   📄 Página {page_num}")  # ← NUEVO: aviso de página actual
                nuevos = extract_links_from(page)
                if nuevos:
                    for d in nuevos:
                        print(f"     ✅ {d['title']} -> {d['link']}")
                        todos_nuevos.append(d)
                        repositorio_links.add(d['link'])
                    nuevos_totales_etiqueta += len(nuevos)  # ← NUEVO
                    intentos = 0
                else:
                    intentos += 1
                    print(f"     ⚠️ Sin nuevos links (intento {intentos})")
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(4)
                page_num += 1  # ← NUEVO
            print(f"  ✔️ Scroll finalizado [{etiqueta}] — Nuevos links: {nuevos_totales_etiqueta}")  # ← NUEVO
        browser.close()

    with open(salida, 'w', encoding='utf-8') as f:
        json.dump(todos_nuevos, f, ensure_ascii=False, indent=2)
    print(f"🎯 Guardados {len(todos_nuevos)} entries en {salida}")
    return todos_nuevos

# Main
if __name__ == '__main__':
    print(f"🚀 Iniciando depuración de links — {TODAY}")
    ciudades = {
        'Cuernavaca': {
            'general':         f"{BASE_URL}/marketplace/cuernavaca/propertyforsale",
            '0_5500000':       f"{BASE_URL}/marketplace/cuernavaca/propertyforsale?minPrice=0&maxPrice=5500000",
            '5500001_10500000':f"{BASE_URL}/marketplace/cuernavaca/propertyforsale?minPrice=5500001&maxPrice=10500000",
            '10500001_15500000':f"{BASE_URL}/marketplace/cuernavaca/propertyforsale?minPrice=10500001&maxPrice=15500000"
        },
        'Jiutepec': {
            'general': f"{BASE_URL}/marketplace/107963212565853/propertyforsale",
            # TODO: añade otras rutas si las necesitas
        },
        'Temixco': {
            'general': f"{BASE_URL}/marketplace/108039299223018/propertyforsale",
            # TODO: añade otras rutas si las necesitas
        }
    }
    total = 0
    all_nuevos = []
    for ciudad, enlaces in ciudades.items():
        nuevos = extract_and_debug_links(ciudad, enlaces)
        total += len(nuevos)
        all_nuevos.extend(nuevos)

    # Actualiza repositorio maestro de links
    with open(LINKS_REPO, 'w', encoding='utf-8') as f:
        json.dump([{'link':d['link']} for d in all_nuevos], f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Total extraído: {total}")