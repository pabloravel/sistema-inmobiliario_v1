#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# extrae_html_desde_links_modificado_con_tipo.py
# Versión mejorada:  
#  • Expande descripción para rentas y ventas  
#  • Detecta “/mes” en precio visible para marcar Renta  

import sys
import os
import subprocess
import time
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ─── Auto-verificación ─────────────────────────────────────────────
MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    sys.exit(f"ERROR: Se requiere Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+")

in_venv = (
    hasattr(sys, 'real_prefix')
    or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    or bool(os.environ.get('VIRTUAL_ENV'))
)
if not in_venv:
    subprocess.check_call([sys.executable, "-m", "venv", "venv"])
    python_exec = (
        os.path.join(os.getcwd(), "venv", "bin", "python")
        if os.name == "posix"
        else os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
    )
    os.execvp(python_exec, [python_exec] + sys.argv)

# ─── Dependencias ─────────────────────────────────────────────────
REQUIRED = ["playwright", "time", "json", "logging", "re"]
missing = [pkg for pkg in REQUIRED if __import__('importlib').import_module(pkg) is None]
if missing:
    print("ERROR: faltan dependencias:", ", ".join(missing))
    sys.exit(1)

# ─── Detector de operación ─────────────────────────────────────────
def detectar_tipo_operacion(titulo: str, descripcion: str, precio_str: str) -> str:
    txt = (titulo + " " + descripcion).lower()
    if re.search(r"\b(renta|alquiler|mensual)\b", txt) or "/mes" in precio_str.lower():
        return "Renta"
    if re.search(r"\b(en venta|venta|vender)\b", txt):
        return "Venta"
    nums = re.findall(r"[\d\.,]+", precio_str)
    if nums and float(nums[0].replace(".", "").replace(",", "")) >= 300_000:
        return "Venta"
    return "Desconocido"

# ─── Main ──────────────────────────────────────────────────────────
def main():
    LINKS_JSON = Path("resultados/links/repositorio_unico.json")
    OUTPUT    = Path("resultados/repositorio_propiedades.json")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    urls = json.loads(LINKS_JSON.read_text(encoding="utf-8"))
    resultado = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(storage_state="fb_state.json")
        page = context.new_page()

        for orig in urls:
            url = orig if orig.startswith("http") else f"https://www.facebook.com{orig}"
            print("➡️ Procesando:", url)
            page.goto(url, timeout=60000)
            time.sleep(2)

            # ─── Extraer título ──────────────────────────
            try:
                titulo = page.locator("meta[property='og:title']").get_attribute("content", timeout=5000) or ""
            except PlaywrightTimeoutError:
                titulo = page.evaluate("() => document.querySelector('meta[property=\\'og:title\\']')?.content") or ""

            # ─── Extraer precio visible (incluye '/mes') ─
            precio_str = ""
            try:
                precio_str = page.locator("div[data-testid='marketplace_feed_price']").inner_text(timeout=5000).strip()
            except PlaywrightTimeoutError:
                try:
                    precio_str = page.locator("meta[property='product:price:amount']").get_attribute("content", timeout=3000) or ""
                except PlaywrightTimeoutError:
                    precio_str = ""

            # ─── Expandir descripción ─────────────────────
            # Intentar varios selectores de botón "Ver más"
            for sel in [
                "div[data-testid='marketplace_feed_subtitle'] button",
                "span[data-testid='see-more-text']",
                "button[aria-label*='más']"
            ]:
                try:
                    btn = page.locator(sel).first
                    btn.click(timeout=1500)
                    time.sleep(0.5)
                except:
                    pass

            # Leer descripción
            try:
                descripcion = page.locator("div[data-testid='marketplace_feed_description']").inner_text(timeout=5000)
            except PlaywrightTimeoutError:
                descripcion = page.evaluate("() => document.querySelector('div[data-testid=\\'marketplace_feed_description\\']')?.innerText") or ""
            descripcion = descripcion.strip()

            # ─── Detectar tipo ───────────────────────────
            oper = detectar_tipo_operacion(titulo, descripcion, precio_str)
            print(f"   • Operación: {oper}")

            # ─── Extraer imagen principal ────────────────
            try:
                img_url = page.locator("meta[property='og:image']").get_attribute("content", timeout=3000) or ""
            except PlaywrightTimeoutError:
                img_url = page.evaluate("() => document.querySelector('meta[property=\\'og:image\\']')?.content") or ""

            html = page.content()

            resultado.append({
                "url": url,
                "titulo": titulo.strip(),
                "precio": precio_str,
                "descripcion": descripcion,
                "operacion": oper,
                "imagen_principal": img_url,
                "html": html
            })

        browser.close()

    OUTPUT.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Guardado {len(resultado)} propiedades en {OUTPUT}")

if __name__ == "__main__":
    main()