#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion.py

Versión estable original de extracción de Facebook Marketplace,
con la única adición de “tipo_operacion” enriquecida para:
  • Venta: incluye “se remata”, “remato”, “remate”
  • Renta: incluye “jardin de fiestas”, “jardin de juegos”
Sin modificar ninguna otra funcionalidad (HTML, JSON, imágenes,
estructura de carpetas `resultados/YYYY-MM-DD/...`).
"""

import os
import json
import requests
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

# Barra de progreso idéntica a la tuya
class ProgressBar:
    MAGENTA = "\033[35m"
    RESET   = "\033[0m"
    def __init__(self, total, desc='', unit=''):
        self.total = total; self.n = 0; self.ok = 0; self.err = 0
        self.last_time = 0.0; self.desc = desc; self.unit = unit
        self.length = 40; self.start_time = time.time(); self._print()
    def _print(self):
        filled = int(self.length * self.n / self.total) if self.total else self.length
        bar = '█' * filled + '-' * (self.length - filled)
        percent = (self.n / self.total * 100) if self.total else 100
        faltan = self.total - self.n
        print(f"\r{self.desc}: {percent:3.0f}%|"
              f"{self.MAGENTA}{bar}{self.RESET}| "
              f"{self.n}/{self.total}  Faltan: {faltan} de {self.total}  "
              f"[procesadas={self.n}, ok={self.ok}, err={self.err}, t={self.last_time:.2f}s]",
              end='', flush=True)
    def update(self, n=1, ok=None, err=None, last_time=None):
        self.n += n
        if ok is not None:   self.ok       = ok
        if err is not None:  self.err      = err
        if last_time is not None: self.last_time = last_time
        self._print()
    def close(self):
        print()

# Rutas sin tocar
CARPETA_LINKS       = "resultados/links/repositorio_unico.json"
CARPETA_RESULTADOS  = "resultados"
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
ESTADO_FB           = "fb_state.json"
BASE_URL            = "https://www.facebook.com"

# Carga maestro
data_master = {}
if os.path.exists(CARPETA_REPO_MASTER):
    with open(CARPETA_REPO_MASTER, "r", encoding="utf-8") as f:
        data_master = json.load(f)
existing_ids = set(data_master.keys())

# Carga y normaliza links
with open(CARPETA_LINKS, "r", encoding="utf-8") as f:
    raw_links = json.load(f)
links = []
for item in raw_links:
    if isinstance(item, str):
        href = BASE_URL + item if item.startswith("/") else item
        city = "cuernavaca"
    elif isinstance(item, dict):
        href = item.get("link","")
        href = BASE_URL + href if href.startswith("/") else href
        city = item.get("ciudad","cuernavaca").lower()
    else:
        continue
    if not href.startswith(BASE_URL):
        continue
    pid = href.rstrip("/").split("/")[-1]
    links.append({"link": href, "id": pid, "ciudad": city})

# Filtra pendientes
pending = [l for l in links if l["id"] not in existing_ids]

# Carpeta diaria
date_str = datetime.now().strftime("%Y-%m-%d")
carpeta   = os.path.join(CARPETA_RESULTADOS, date_str)
os.makedirs(carpeta, exist_ok=True)

# Funciones originales
def extraer_descripcion_estable(soup):
    for div in soup.find_all("div"):
        if div.get_text(strip=True) in ["Descripción", "Detalles"]:
            sig = div.find_next_sibling("div")
            if sig:
                return sig.get_text(separator="\n", strip=True).replace("Ver menos","").strip()
    return ""

def extraer_precio(soup):
    for span in soup.find_all("span"):
        t = span.get_text(strip=True)
        if t.startswith("$") and len(t) < 30:
            return t
    return ""

def extraer_vendedor(soup):
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "facebook.com/profile.php?id=" in href:
            link_v = href.split("?")[0]
            strong = a.find("strong")
            vendedor = strong.get_text(strip=True) if strong else (a.find("span").get_text(strip=True) if a.find("span") else "")
            return vendedor, link_v
    return "", ""

# Descargar imagen
def descargar_imagen_por_playwright(page, ciudad, pid):
    try:
        src = page.locator('img[alt^="Foto de"]').first.get_attribute('src')
    except:
        try:
            src = page.locator('img').first.get_attribute('src')
        except:
            return ""
    if not src or not src.startswith("http"):
        return ""
    filename = f"{ciudad}-{date_str}-{pid}.jpg"
    path_img = os.path.join(carpeta, filename)
    try:
        resp = requests.get(src, timeout=10)
        if resp.status_code == 200:
            with open(path_img, "wb") as f:
                f.write(resp.content)
            return filename
    except:
        pass
    return ""

# Guardar HTML y JSON
def guardar_html_y_json(html, datos, ciudad, pid):
    base     = f"{ciudad}-{date_str}-{pid}"
    ruta_html= os.path.join(carpeta, base + ".html")
    ruta_json= os.path.join(carpeta, base + ".json")
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

# ─── NUEVA detección avanzada de tipo_operacion ────────────────
def detectar_tipo_operacion(titulo, descripcion, precio_str):
    txt = " ".join([titulo, descripcion, precio_str]).lower()
    # Venta keywords
    venta_kw = ["en venta", "venta", "vender", "vendo", "vende", "se remata", "remato", "remate"]
    if any(re.search(rf"\b{re.escape(k)}\b", txt) for k in venta_kw):
        return "Venta"
    # Renta keywords
    renta_kw = ["renta", "alquiler", "mensual", "/mes", "jardin de fiestas", "jardin de juegos"]
    if any(k in txt for k in renta_kw):
        return "Renta"
    # Fallback monto
    m = re.search(r"([\d\.,]+)", precio_str)
    if m and int(m.group(1).replace(".", "").replace(",", "")) >= 300_000:
        return "Venta"
    return "Desconocido"
# ─────────────────────────────────────────────────────────────

def main():
    print(f"Propiedades ya procesadas: {len(existing_ids)}")
    pbar = ProgressBar(len(pending), desc="Extrayendo propiedades", unit="propiedad")
    ok = err = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        ctx     = browser.new_context(storage_state=ESTADO_FB)
        page    = ctx.new_page()

        for item in pending:
            pid    = item["id"]
            url    = item["link"]
            ciudad = item["ciudad"]
            t0     = time.time()
            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(3000)

                # Expandir Ver más
                try:
                    vm = page.locator("text=Ver más").first
                    if vm.is_visible():
                        vm.click()
                        page.wait_for_timeout(1000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                titulo      = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
                descripcion = extraer_descripcion_estable(soup)
                precio      = extraer_precio(soup)
                vendedor, link_v = extraer_vendedor(soup)
                img_portada = descargar_imagen_por_playwright(page, ciudad, pid)

                # Detección de operación actualizada
                tipo_op = detectar_tipo_operacion(titulo, descripcion, precio)

                datos = {
                    "id": pid,
                    "link": url,
                    "titulo": titulo,
                    "precio": precio,
                    "ciudad": ciudad,
                    "vendedor": vendedor,
                    "link_vendedor": link_v,
                    "descripcion": descripcion,
                    "imagen_portada": img_portada,
                    "tipo_operacion": tipo_op
                }

                guardar_html_y_json(html, datos, ciudad, pid)

                data_master[pid] = datos
                with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as mf:
                    json.dump(data_master, mf, ensure_ascii=False, indent=2)

                ok += 1
            except Exception as e:
                err += 1
                print(f"❌ Error en {pid}: {e}")
            finally:
                pbar.update(1, ok=ok, err=err, last_time=time.time()-t0)

        pbar.close()
        page.close()
        browser.close()

    print(f"\nTotal de propiedades en el repositorio maestro: {len(data_master)}")

if __name__ == '__main__':
    main()