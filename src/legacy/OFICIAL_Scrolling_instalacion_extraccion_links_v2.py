#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# OFICIAL_Scrolling_instalacion_extraccion_links_v2.py
# ✅ Basado en OFICIAL_Scrolling_extraccion_links_v2.py, agregando:
#    • Autoverificación de Python (>=3.7)
#    • Creación y activación automática de venv
#    • Chequeo de dependencias
#    • Lógica original de scrolling y extracción de links

import sys
import os
import subprocess

# ---------- Auto-verificación ----------
# 1. Verificar versión de Python
MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    sys.exit(
        f"ERROR: Se requiere Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} o superior. "
        f"Tienes la versión {sys.version_info.major}.{sys.version_info.minor}."
    )

# 2. Comprobar entorno virtual
in_venv = (
    hasattr(sys, 'real_prefix') or
    (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or
    bool(os.environ.get('VIRTUAL_ENV'))
)
if not in_venv:
    print("⚠️ No estás en un entorno virtual. Creando uno en ./venv ...")
    subprocess.check_call([sys.executable, "-m", "venv", "venv"])
    print("✅ Entorno virtual creado. Reiniciando script con venv...")
    # Determinar ruta al python del venv
    if os.name == 'posix':
        python_exec = os.path.join(os.getcwd(), 'venv', 'bin', 'python')
    else:
        python_exec = os.path.join(os.getcwd(), 'venv', 'Scripts', 'python.exe')
    os.execvp(python_exec, [python_exec] + sys.argv)

# 3. Verificar dependencias
REQUIRED = ["playwright", "time", "json", "logging"]
missing = []
for pkg in REQUIRED:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)

if missing:
    print("ERROR: Faltan dependencias:", ", ".join(missing))
    print("Instálalas con: pip install -r requirements.txt")
    sys.exit(1)
# ---------------------------------------

# Importaciones originales
from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime
from pathlib import Path


def extraer_links_ciudad(ciudad, enlaces, carpeta_resultados, repositorio_links):
    """
    Extrae enlaces de Marketplace para la ciudad dada,
    filtrando aquellos que ya existen en repositorio_links.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    nombre_archivo = f"links_extraidos_{ciudad.lower()}_{timestamp}.json"
    ruta_salida = carpeta_resultados / nombre_archivo

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="fb_state.json")
        page = context.new_page()

        nuevos_links = set()
        for etiqueta, url in enlaces.items():
            print(f"\n🌎 Abriendo ciudad: {ciudad} - {url}")
            page.goto(url)
            time.sleep(4)
            intentos_sin_nuevos = 0
            while True:
                elements = page.query_selector_all("a.ui-search-result__content")
                encontrados = [el.get_attribute('href') for el in elements]
                for href in encontrados:
                    href_clean = href.split('?')[0]
                    if href_clean not in repositorio_links and href_clean not in nuevos_links:
                        nuevos_links.add(href_clean)
                if not nuevos_links:
                    intentos_sin_nuevos += 1
                    print(f"⚠️ No se encontraron nuevos links (intento {intentos_sin_nuevos})")
                    if intentos_sin_nuevos >= 5:
                        break
                else:
                    intentos_sin_nuevos = 0
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                time.sleep(4)
                if intentos_sin_nuevos >= 5:
                    break

        browser.close()

    carpeta_resultados.mkdir(parents=True, exist_ok=True)
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(sorted(list(nuevos_links)), f, indent=2, ensure_ascii=False)

    print(f"🎯 Links de {ciudad} guardados en {ruta_salida}")
    return list(nuevos_links)


if __name__ == "__main__":
    fecha_corrida = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Iniciando extracción de links — Corrida del {fecha_corrida}\n")

    carpeta_resultados = Path("resultados/links")
    carpeta_resultados.mkdir(parents=True, exist_ok=True)

    repositorio_path = carpeta_resultados / "repositorio_unico.json"
    repositorio_links = set()

    if repositorio_path.exists():
        with open(repositorio_path, "r", encoding="utf-8") as f:
            datos_previos = json.load(f)
            for item in datos_previos:
                if isinstance(item, str):
                    repositorio_links.add(item)
                elif isinstance(item, dict):
                    href = item.get('link') or item.get('url') or item.get('href')
                    if href:
                        repositorio_links.add(href.split("?")[0])

    total_nuevos_links = 0

    ciudades_y_enlaces = {
        "Cuernavaca": {
            "general": "https://www.facebook.com/marketplace/cuernavaca/propertyforsale",
            "precio_0_5500000": "https://www.facebook.com/marketplace/cuernavaca/propertyforsale?minPrice=0&maxPrice=5500000",
            "precio_5500001_10500000": "https://www.facebook.com/marketplace/cuernavaca/propertyforsale?minPrice=5500001&maxPrice=10500000",
            "precio_10500001_15500000": "https://www.facebook.com/marketplace/cuernavaca/propertyforsale?minPrice=10500001&maxPrice=15500000"
        },
        "Jiutepec": {
            "general": "https://www.facebook.com/marketplace/107963212565853/propertyforsale",
            "precio_0_5500000": "https://www.facebook.com/marketplace/107963212565853/propertyforsale?minPrice=0&maxPrice=5500000",
            "precio_5500001_10500000": "https://www.facebook.com/marketplace/107963212565853/propertyforsale?minPrice=5500001&maxPrice=10500000",
            "precio_10500001_15500000": "https://www.facebook.com/marketplace/107963212565853/propertyforsale?minPrice=10500001&maxPrice=15500000"
        },
        "Temixco": {
            "general": "https://www.facebook.com/marketplace/108039299223018/propertyforsale",
            "precio_0_5500000": "https://www.facebook.com/marketplace/108039299223018/propertyforsale?minPrice=0&maxPrice=5500000",
            "precio_5500001_10500000": "https://www.facebook.com/marketplace/108039299223018/propertyforsale?minPrice=5500001&maxPrice=10500000",
            "precio_10500001_15500000": "https://www.facebook.com/marketplace/108039299223018/propertyforsale?minPrice=10500001&maxPrice=15500000"
        }
    }

    for ciudad, enlaces in ciudades_y_enlaces.items():
        print(f"\n🌎 Procesando ciudad: {ciudad}")
        nuevos = extraer_links_ciudad(ciudad, enlaces, carpeta_resultados, repositorio_links)
        repositorio_links.update(nuevos)
        total_nuevos_links += len(nuevos)

    print(f"\n🎉 Total de links únicos extraídos en la corrida {fecha_corrida}: {total_nuevos_links}\n")

    with open(repositorio_path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(repositorio_links)), f, indent=2, ensure_ascii=False)

    print(f"📦 Repositorio actualizado → {repositorio_path} ({len(repositorio_links)} links únicos totales)")
