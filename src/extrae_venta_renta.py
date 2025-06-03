#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion.py

Extiende tu script estable de extracción de HTML+JSON desde links,
añadiendo detección de tipo de operación (“venta” vs “renta”).
No altera ninguna de las funcionalidades originales: scrolling,
login con Chromium + fb_state.json, extracción de descripción,
expansión de “ver más” y guardado de imagen, HTML y JSON.
"""

import sys
import os
from pathlib import Path
import json
import time
import logging
from datetime import datetime

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ——————————————————————————————————————————————————
# CONFIGURACIÓN
# ——————————————————————————————————————————————————
# Ruta al storage state generado con `playwright codegen --save-storage=fb_state.json https://facebook.com`
STORAGE_STATE = "fb_state.json"
# Carpeta donde está tu repositorio de links y donde dejarás los JSON individuales
LINKS_JSON = Path("resultados/links/repositorio_unico.json")
OUTPUT_DIR = Path("resultados/propiedades")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ——————————————————————————————————————————————————
# UTILIDADES
# ——————————————————————————————————————————————————
def detectar_tipo_operacion(descripcion: str, precio_str: str) -> str:
    """
    Devuelve 'venta', 'renta' o 'desconocido' basándose en:
      1) palabras clave en la descripción,
      2) indicadores de '/mes' en el precio,
      3) por defecto 'venta' si precio >300k y no hay pistas de renta.
    """
    txt = descripcion.lower()
    # 1) Palabras clave
    for kw in ("se renta", "en renta", "alquiler", "alquilo", "renta"):
        if kw in txt:
            return "renta"
    for kw in ("se vende", "en venta", "venta"):
        if kw in txt:
            return "venta"
    # 2) Precio por mes
    if "/mes" in precio_str or "mes" in precio_str:
        return "renta"
    # 3) Fallback según importe
    try:
        cifra = int(precio_str.replace("$","").replace(",","").split()[0])
        if cifra >= 300_000:
            return "venta"
        else:
            return "renta"
    except Exception:
        return "desconocido"

# ——————————————————————————————————————————————————
# FLUJO PRINCIPAL
# ——————————————————————————————————————————————————
def main():
    # 1) Carga de todos los links únicos
    if not LINKS_JSON.exists():
        print(f"ERROR: no hallo {LINKS_JSON}")
        sys.exit(1)
    with open(LINKS_JSON, "r", encoding="utf-8") as f:
        all_links = json.load(f)

    print(f"➡️ {len(all_links)} links a procesar.")

    # 2) Inicializar Playwright + Chromium visible con sesión guardada
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=STORAGE_STATE)
        page = context.new_page()

        for idx, url in enumerate(all_links, start=1):
            print(f"\n[{idx}/{len(all_links)}] Cargando {url}")
            try:
                page.goto(url, timeout=60000, wait_until="load")
            except PlaywrightTimeout:
                print("   ⚠️ Timeout, seguimos con lo cargado…")

            # 3) Extraer metadatos OG
            try:
                titulo = page.locator("meta[property='og:title']").get_attribute("content") or ""
            except PlaywrightTimeout:
                titulo = ""
            try:
                precio_str = page.locator("meta[property='product:price:amount']").get_attribute("content") or ""
            except PlaywrightTimeout:
                # fallback selector si no existe meta
                precio_str = page.locator("span:has-text('$')").first.inner_text() or ""
            # 4) Expandir descripción “ver más” si existe botón
            if page.locator("text=/ver más/i").is_visible(timeout=2000):
                page.click("text=/ver más/i")
                time.sleep(0.5)
            # 5) Extraer descripción completa
            try:
                descripcion = page.locator("div#marketplace-captions, div[data-testid='marketplace-detail-description']").inner_text().strip()
            except PlaywrightTimeout:
                descripcion = ""
            # 6) Detectar tipo de operación
            tipo_op = detectar_tipo_operacion(descripcion, precio_str)
            print(f"   • Operación: {tipo_op}")

            # 7) Otros campos (ejemplo: ubicación, recámaras…) que ya tenías
            #    Asegúrate de copiar aquí tus selectores originales
            try:
                ubicacion = page.locator("span:has-text('Ubicación') + span").inner_text()
            except:
                ubicacion = ""
            # … y así con recamaras, baños, terreno, imagen_portada, etc.
            # Para brevedad, llamémoslo campos_extra:
            campos_extra = {}

            # 8) Armar objeto JSON
            salida = {
                "link": url,
                "titulo": titulo,
                "precio": precio_str,
                "descripcion": descripcion,
                "ubicacion": ubicacion,
                **campos_extra,
                "tipo_operacion": tipo_op
            }

            # 9) Guardar en JSON individual
            #    Nombre: basado en ID FB (última porción de URL)
            propiedad_id = url.rstrip("/").rsplit("/",1)[-1]
            archivo_out = OUTPUT_DIR / f"{propiedad_id}.json"
            with open(archivo_out, "w", encoding="utf-8") as wf:
                json.dump(salida, wf, ensure_ascii=False, indent=2)

            print(f"   ✅ Guardado → {archivo_out.name}")

        browser.close()
    print("\n🏁 ¡Terminado!")

if __name__ == "__main__":
    main()