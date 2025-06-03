#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: extrae_html_desde_links.py
Descripción: Extrae HTMLs e imágenes solo para los links nuevos comparados contra repositorio_unico.json.
"""
import os
import json
import requests
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from tqdm import tqdm  # Para barra de progreso

# Rutas y constantes
enlace_repo = Path("resultados/links/repositorio_unico.json")
CARPETA_RESULTADOS = Path("resultados")
ESTADO_FB = "fb_state.json"
BASE_URL = "https://www.facebook.com"

# 1) Cargar IDs ya procesados
def cargar_processed_ids():
    if not enlace_repo.exists():
        return set()
    raw = json.loads(enlace_repo.read_text(encoding="utf-8"))
    items = raw.values() if isinstance(raw, dict) else raw
    ids = set()
    for item in items:
        if isinstance(item, dict) and "id" in item:
            ids.add(item["id"])
        elif isinstance(item, str) and item.startswith(BASE_URL):
            ids.add(item.rstrip("/").split('/')[-1])
    return ids

# 2) Cargar y filtrar enlaces nuevos de repositorio_unico.json
def cargar_links_nuevos():
    raw_links = json.loads(enlace_repo.read_text(encoding="utf-8"))
    processed = cargar_processed_ids()
    nuevos = []
    # raw_links puede ser lista de dicts o de strings
    for item in raw_links if isinstance(raw_links, list) else raw_links.values():
        if isinstance(item, str):
            href = item
        elif isinstance(item, dict):
            href = item.get("link", "")
        else:
            continue
        if href.startswith("/"):
            href = BASE_URL + href
        if BASE_URL not in href or "/marketplace/" not in href:
            continue
        precio_id = href.rstrip("/").split('/')[-1]
        if precio_id in processed:
            continue  # ya procesado
        link_data = {"link": href, "id": precio_id}
        nuevos.append(link_data)
    return nuevos

# Función de extracción

def process_link(link_data, carpeta_destino):
    id_publicacion = link_data["id"]
    url = link_data["link"]
    ciudad = link_data.get("ciudad", "unknown").lower()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=ESTADO_FB)
        page = context.new_page()
        page.goto(url, timeout=60000)
        page.wait_for_timeout(2000)
        # Expandir "Ver más"
        while True:
            try:
                more = page.locator("text=Ver más").first
                if not more.is_visible(): break
                more.click()
                page.wait_for_timeout(500)
            except:
                break
        html = page.content()
        context.close()
        browser.close()

    # Parsear
    soup = BeautifulSoup(html, "html.parser")
    # Extraer campos
    titulo_tag = soup.find("h1")
    titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
    # ... demás extracciones según tu lógica estable

    # Guardar HTML y JSON
    fecha = datetime.now().strftime("%Y-%m-%d")
    carpeta = carpeta_destino / fecha
    carpeta.mkdir(parents=True, exist_ok=True)
    base = f"{ciudad}-{fecha}-{id_publicacion}"
    (carpeta / (base + ".html")).write_text(html, encoding="utf-8")
    meta = {"id":id_publicacion, "link": url, "titulo": titulo}
    (carpeta / (base + ".json")).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

# Main
def main():
    nuevos = cargar_links_nuevos()
    total = len(nuevos)
    if total == 0:
        print("✅ No hay links nuevos para procesar.")
        return
    print(f"🔍 Procesando {total} links nuevos...")
    pbar = tqdm(nuevos, desc="Extrayendo propiedades", unit="link")
    for link_data in pbar:
        try:
            process_link(link_data, CARPETA_RESULTADOS)
        except Exception as e:
            print(f"❌ Error procesando {link_data['id']}: {e}")
    # Actualizar repositorio_unico.json añadiendo nuevos IDs
    repo = json.loads(enlace_repo.read_text(encoding="utf-8"))
    combined = []
    if isinstance(repo, dict):
        combined = list(repo.values())
    else:
        combined = repo
    combined.extend(nuevos)
    enlace_repo.write_text(json.dumps(combined, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"🎉 Finalizado. Repositorio actualizado con {len(nuevos)} IDs nuevos.")

if __name__ == "__main__":
    main()
