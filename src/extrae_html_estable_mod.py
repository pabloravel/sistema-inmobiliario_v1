#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_estable_mod.py

Versión estable original de extracción de Facebook Marketplace,
con la única adición de “tipo_operacion” (Venta/Renta) sin tocar
ninguna otra funcionalidad previa (guardado de HTML, JSON e imágenes
en resultados/YYYY-MM-DD/…).
"""

import sys
import os
import json
import re
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ─── Configuración de rutas ────────────────────────────────────────
DATE_FOLDER = datetime.now().strftime("%Y-%m-%d")
BASE_DIR    = Path("resultados") / DATE_FOLDER
LINKS_JSON  = Path("resultados/links/repositorio_unico.json")

# Carpeta donde el script guardaba antes HTML, JSON e imágenes
HTML_DIR    = BASE_DIR / "html"
IMG_DIR     = BASE_DIR / "imagenes"
JSON_DIR    = BASE_DIR / "json"
for d in (HTML_DIR, IMG_DIR, JSON_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ─── Función de detección de operación ─────────────────────────────
def detectar_operacion(titulo: str, descripcion: str, precio_str: str) -> str:
    txt = " ".join([titulo, precio_str, descripcion]).lower()
    # Renta si menciona renta, alquiler o “/mes”
    if re.search(r"\b(renta|alquiler|mensual)\b", txt) or re.search(r"/\s*mes\b", txt):
        return "Renta"
    # Venta si menciona venta, vender o vendo
    if re.search(r"\b(en venta|venta|vender|vendo)\b", txt):
        return "Venta"
    # Fallback por monto
    m = re.search(r"([\d\.,]+)", precio_str)
    if m:
        val = int(m.group(1).replace(".", "").replace(",", ""))
        return "Venta" if val >= 300_000 else "Renta"
    return "Desconocido"

# ─── Carga de links y de procesados ───────────────────────────────
if not LINKS_JSON.exists():
    sys.exit(f"ERROR: no existe {LINKS_JSON}")

links = json.loads(LINKS_JSON.read_text(encoding="utf-8"))

# Identificar IDs ya procesados (por JSON guardado)
processed_ids = {p.stem for p in JSON_DIR.glob("*.json")}
to_process = []
for raw in links:
    uid = raw.rstrip("/").rsplit("/",1)[-1]
    if uid not in processed_ids:
        to_process.append((uid, raw))

print(f"➡️ {len(to_process)} links nuevos a procesar (de {len(links)} totales).")

# ─── Iniciar Playwright ───────────────────────────────────────────
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state="fb_state.json")
    page = context.new_page()

    for idx, (uid, raw_url) in enumerate(to_process, start=1):
        url = raw_url if raw_url.startswith("http") else "https://www.facebook.com"+raw_url
        print(f"[{idx}/{len(to_process)}] Cargando {url}")
        try:
            page.goto(url, timeout=60000, wait_until="load")
        except PlaywrightTimeout:
            print("   ⚠️ Timeout, seguimos con lo cargado…")

        # — Título —
        try:
            titulo = page.locator("meta[property='og:title']").get_attribute("content", timeout=5000) or ""
        except PlaywrightTimeout:
            titulo = ""
        titulo = titulo.strip()

        # — Precio —
        try:
            precio_str = page.locator("meta[property='product:price:amount']").get_attribute("content", timeout=3000) or ""
        except PlaywrightTimeout:
            precio_str = ""
        precio_str = precio_str.strip()

        # — Expandir “Ver más” —
        try:
            page.locator("text=Ver más").first.click(force=True, timeout=2000)
            time.sleep(0.5)
        except:
            pass

        # — Descripción —
        try:
            descripcion = page.locator("div[data-testid='marketplace_feed_description']").inner_text(timeout=5000) or ""
        except PlaywrightTimeout:
            descripcion = ""
        descripcion = descripcion.strip()

        # — Detectar operación (novedad añadida) —
        tipo_op = detectar_operacion(titulo, descripcion, precio_str)
        print(f"   • Operación: {tipo_op}")

        # — Extraer imagen principal URL —
        try:
            img_url = page.locator("meta[property='og:image']").get_attribute("content", timeout=3000) or ""
        except PlaywrightTimeout:
            img_url = ""
        img_url = img_url.strip()

        # — Descargar HTML, JSON e imagen como en tu versión estable ─────
        # 1) HTML
        html_path = HTML_DIR / f"{uid}.html"
        html_path.write_text(page.content(), encoding="utf-8")

        # 2) Imagen portada
        if img_url:
            img_ext = img_url.split("?")[0].rsplit(".",1)[-1]
            img_path = IMG_DIR / f"{uid}.{img_ext}"
            try:
                import requests
                r = requests.get(img_url, timeout=10)
                if r.status_code == 200:
                    img_path.write_bytes(r.content)
            except:
                pass

        # 3) JSON
        data = {
            "url": url,
            "titulo": titulo,
            "precio": precio_str,
            "descripcion": descripcion,
            "tipo_operacion": tipo_op,
            "imagen_principal": img_url
            # …mantén aquí cualquier otro campo que ya tenías…
        }
        json_path = JSON_DIR / f"{uid}.json"
        json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    browser.close()

print(f"\n✅ Finalizado: HTML en {HTML_DIR}, imágenes en {IMG_DIR}, JSON en {JSON_DIR}")