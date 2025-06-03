#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# extrae_html_estable.py
# Versión estable original (sin lógica de “/mes”)
# • Expande la descripción con el selector probado
# • Detecta “Venta” y “Renta” según palabras clave en título/descr
# • Usa umbral de 300 000 MXN para clasificar ventas si no hay mención de renta
# • Guarda JSON con campo "operacion"

import sys
import os
import subprocess
import time
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ─── Verificación de Python y venv ─────────────────────────────────
MIN_PYTHON = (3, 7)
if sys.version_info < MIN_PYTHON:
    sys.exit(f"ERROR: Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ requerido")

in_venv = (
    hasattr(sys, 'real_prefix')
    or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    or bool(os.environ.get('VIRTUAL_ENV'))
)
if not in_venv:
    print("⚠️ Creando y activando venv…")
    subprocess.check_call([sys.executable, "-m", "venv", "venv"])
    python_exec = (
        os.path.join(os.getcwd(), "venv", "bin", "python")
        if os.name == "posix"
        else os.path.join(os.getcwd(), "venv", "Scripts", "python.exe")
    )
    os.execvp(python_exec, [python_exec] + sys.argv)

# ─── Dependencias ─────────────────────────────────────────────────
REQUIRED = ["playwright", "time", "json", "logging", "re"]
missing = []
for pkg in REQUIRED:
    try:
        __import__(pkg)
    except ImportError:
        missing.append(pkg)
if missing:
    print("ERROR: faltan dependencias:", ", ".join(missing))
    sys.exit(1)

# ─── Función de detección de operación ─────────────────────────────
def detectar_tipo_operacion(titulo: str, descripcion: str, precio_str: str) -> str:
    texto = (titulo + " " + descripcion).lower()
    if re.search(r"\b(renta|alquiler|mensual)\b", texto):
        return "Renta"
    if re.search(r"\b(en venta|venta|vender)\b", texto):
        return "Venta"
    nums = re.findall(r"[\d\.,]+", precio_str)
    if nums:
        valor = float(nums[0].replace(".", "").replace(",", ""))
        if valor >= 300_000:
            return "Venta"
    return "Desconocido"

# ─── Lógica principal ──────────────────────────────────────────────
def main():
    enlaces_path = Path("resultados/links/repositorio_unico.json")
    output_path  = Path("resultados/repositorio_propiedades.json")
    output_path.parent.mkdir(exist_ok=True, parents=True)

    enlaces = json.loads(enlaces_path.read_text(encoding="utf-8"))
    resultados = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="fb_state.json")
        page = context.new_page()

        for orig in enlaces:
            url = orig if orig.startswith("http") else f"https://www.facebook.com{orig}"
            print("➡️ Procesando:", url)
            page.goto(url, timeout=60000)
            time.sleep(2)

            # ─── Título ────────────────────────────────────────
            try:
                titulo = page.locator("meta[property='og:title']").get_attribute("content", timeout=5000) or ""
            except PlaywrightTimeoutError:
                titulo = ""
            titulo = titulo.strip()

            # ─── Precio (metatag) ──────────────────────────────
            try:
                precio_str = page.locator("meta[property='product:price:amount']").get_attribute("content", timeout=5000) or ""
            except PlaywrightTimeoutError:
                precio_str = ""
            precio_str = precio_str.strip()

            # ─── Expandir descripción ──────────────────────────
            try:
                page.locator("div[data-testid='marketplace_feed_subtitle'] button").first.click(timeout=2000)
                time.sleep(0.5)
            except:
                pass

            # ─── Descripción ───────────────────────────────────
            try:
                descripcion = page.locator("div[data-testid='marketplace_feed_description']").inner_text(timeout=5000) or ""
            except PlaywrightTimeoutError:
                descripcion = ""
            descripcion = descripcion.strip()

            # ─── Detectar operación ────────────────────────────
            oper = detectar_tipo_operacion(titulo, descripcion, precio_str)
            print(f"   • Operación: {oper}")

            # ─── Imagen principal ──────────────────────────────
            try:
                img_url = page.locator("meta[property='og:image']").get_attribute("content", timeout=3000) or ""
            except PlaywrightTimeoutError:
                img_url = ""
            img_url = img_url.strip()

            # ─── HTML completo ─────────────────────────────────
            html = page.content()

            resultados.append({
                "url": url,
                "titulo": titulo,
                "precio": precio_str,
                "descripcion": descripcion,
                "operacion": oper,
                "imagen_principal": img_url,
                "html": html
            })

        browser.close()

    output_path.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n✅ Guardadas {len(resultados)} propiedades en {output_path}")

if __name__ == "__main__":
    main()