#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion_v2.py

Versión 2.0 - Mejora en la extracción de datos de Facebook Marketplace
- Extracción mejorada de ubicación exacta
- Detección precisa de recámaras y baños
- Información detallada del vendedor
- Guardado de DOM y estado completo
"""

import os
import json
import requests
import time
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

# Barra de progreso (idéntica a la tuya)
class ProgressBar:
    MAGENTA = "\033[35m"
    RESET   = "\033[0m"
    def __init__(self, total, desc='', unit=''):
        self.total = total; self.n = 0; self.ok = 0; self.err = 0
        self.last_time = 0.0; self.desc = desc; self.unit = unit
        self.length = 40; self.start_time = time.time(); self._print()
    def _print(self):
        filled = int(self.length * self.n / self.total) if self.total else self.length
        bar    = '█' * filled + '-' * (self.length - filled)
        pct    = (self.n / self.total * 100) if self.total else 100
        faltan = self.total - self.n
        print(f"\r{self.desc}: {pct:3.0f}%|"
              f"{self.MAGENTA}{bar}{self.RESET}| "
              f"{self.n}/{self.total}  Faltan: {faltan} de {self.total}  "
              f"[ok={self.ok}, err={self.err}, t={self.last_time:.2f}s]",
              end='', flush=True)
    def update(self, n=1, ok=None, err=None, last_time=None):
        self.n += n
        if ok       is not None: self.ok = ok
        if err      is not None: self.err = err
        if last_time is not None: self.last_time = last_time
        self._print()
    def close(self):
        print()

# ── Rutas y constantes ────────────────────────────────────────────────
CARPETA_LINKS       = "resultados/links/repositorio_unico.json"
CARPETA_RESULTADOS  = "resultados"
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
ESTADO_FB           = "fb_state.json"
BASE_URL            = "https://www.facebook.com"

# ── Funciones de extracción ────────────────────────────────────────────
def extraer_descripcion_estable(soup):
    for div in soup.find_all("div"):
        if div.get_text(strip=True) in ["Descripción", "Detalles"]:
            siguiente = div.find_next_sibling("div")
            if siguiente:
                return siguiente.get_text(separator="\n", strip=True).replace("Ver menos","").strip()
    return ""

def extraer_precio(soup):
    for span in soup.find_all("span"):
        t = span.get_text(strip=True)
        if t.startswith("$") and len(t) < 30:
            return t
    return ""

def extraer_ubicacion(soup):
    # Buscar la ubicación en el DOM
    for div in soup.find_all("div"):
        if "Ubicación de la vivienda" in div.get_text(strip=True):
            siguiente = div.find_next_sibling("div")
            if siguiente:
                return siguiente.get_text(strip=True)
    return ""

def extraer_caracteristicas(soup):
    caracteristicas = {
        "recamaras": 0,
        "banos": 0,
        "metros_terreno": 0,
        "metros_construccion": 0
    }
    
    # Buscar en la descripción y en todo el DOM
    texto_completo = soup.get_text(" ", strip=True).lower()
    
    # Buscar recámaras
    rec_match = re.search(r"(\d+)\s*(?:recámaras?|recamaras?|habitaciones?|dormitorios?)", texto_completo)
    if rec_match:
        caracteristicas["recamaras"] = int(rec_match.group(1))
    
    # Buscar baños
    ban_match = re.search(r"(\d+)\s*(?:baños?|banos?)\s*(?:completos?)?", texto_completo)
    if ban_match:
        caracteristicas["banos"] = int(ban_match.group(1))
    
    # Buscar metros de terreno
    terr_match = re.search(r"terreno\s*(?:de)?\s*(\d+)\s*(?:m2|mts|metros?)", texto_completo)
    if terr_match:
        caracteristicas["metros_terreno"] = int(terr_match.group(1))
    
    # Buscar metros de construcción
    cons_match = re.search(r"construcción\s*(?:de)?\s*(\d+)\s*(?:m2|mts|metros?)", texto_completo)
    if cons_match:
        caracteristicas["metros_construccion"] = int(cons_match.group(1))
    
    return caracteristicas

def extraer_vendedor_mejorado(page):
    try:
        # Intentar obtener el nombre del vendedor y su link del DOM
        vendedor_info = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a'));
            for (const link of links) {
                if (link.href.includes('/profile.php?id=') || link.href.match(/facebook\\.com\\/[^\\/]+$/) ) {
                    return {
                        nombre: link.textContent.trim(),
                        link: link.href
                    }
                }
            }
            return null;
        }""")
        
        if vendedor_info:
            return vendedor_info.get("nombre", ""), vendedor_info.get("link", "")
    except:
        pass
    
    return "", ""

def descargar_imagen_por_playwright(page, ciudad, pid, carpeta, date_str):
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

def guardar_html_y_json(html, datos, ciudad, pid, carpeta, date_str):
    base      = f"{ciudad}-{date_str}-{pid}"
    ruta_html = os.path.join(carpeta, base + ".html")
    ruta_json = os.path.join(carpeta, base + ".json")
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def guardar_dom_y_estado(page, ciudad, pid, carpeta, date_str):
    try:
        # Guardar el DOM completo
        dom = page.content()
        dom_path = os.path.join(carpeta, f"{ciudad}-{date_str}-{pid}-dom.html")
        with open(dom_path, "w", encoding="utf-8") as f:
            f.write(dom)
        
        # Guardar el estado de la página (incluyendo JavaScript)
        state = page.evaluate("""() => {
            return {
                title: document.title,
                url: window.location.href,
                innerText: document.body.innerText,
                scripts: Array.from(document.scripts).map(s => s.src),
            }
        }""")
        state_path = os.path.join(carpeta, f"{ciudad}-{date_str}-{pid}-state.json")
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"Error guardando DOM/estado para {pid}: {e}")

def detectar_tipo_operacion(titulo, descripcion, precio_str):
    txt = " ".join([titulo, descripcion, precio_str]).lower()
    if any(k in txt for k in ("renta", "alquiler", "/mes", "mensual")):
        return "Renta"
    if any(k in txt for k in ("en venta", "venta", "vender", "vendo", "vende")):
        return "Venta"
    m = re.search(r"([\d\.,]+)", precio_str)
    if m and int(m.group(1).replace(".", "").replace(",", "")) >= 300_000:
        return "Venta"
    return "Desconocido"

# ── Flujo principal ───────────────────────────────────────────────────
def main():
    # 1) Maestro previo
    data_master = {}
    if os.path.exists(CARPETA_REPO_MASTER):
        with open(CARPETA_REPO_MASTER, "r", encoding="utf-8") as f:
            data_master = json.load(f)
    existing_ids = set(data_master.keys())

    # 2) Carga y normaliza enlaces
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
        pid = href.rstrip("/").split("/")[-1]
        links.append({"link": href, "id": pid, "ciudad": city})

    # 3) Filtra pendientes
    pending = [l for l in links if l["id"] not in existing_ids]

    # ── PRINT RESUMEN ANTES DE EMPEZAR ──
    total = len(links)
    falta = len(pending)
    print(f"Total de propiedades: {total}, pendientes por procesar: {falta}")

    # 4) Carpeta diaria
    date_str = datetime.now().strftime("%Y-%m-%d")
    carpeta  = os.path.join(CARPETA_RESULTADOS, date_str)
    os.makedirs(carpeta, exist_ok=True)

    # 5) Lanzar navegador y barra de progreso
    pbar = ProgressBar(falta, desc="Extrayendo propiedades", unit="propiedad")
    ok = err = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=ESTADO_FB)
        page    = context.new_page()

        for item in pending:
            pid    = item["id"]
            url    = item["link"]
            ciudad = item["ciudad"]
            t0     = time.time()
            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(3000)
                # expandir "Ver más"
                try:
                    vm = page.locator("text=Ver más").first
                    if vm.is_visible():
                        vm.click(); page.wait_for_timeout(1000)
                except:
                    pass
                
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                
                # Guardar DOM y estado
                guardar_dom_y_estado(page, ciudad, pid, carpeta, date_str)
                
                # Extraer información mejorada
                titulo = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
                descripcion = extraer_descripcion_estable(soup)
                precio = extraer_precio(soup)
                ubicacion = extraer_ubicacion(soup)
                caracteristicas = extraer_caracteristicas(soup)
                vendedor, link_v = extraer_vendedor_mejorado(page)
                img_portada = descargar_imagen_por_playwright(page, ciudad, pid, carpeta, date_str)
                tipo_op = detectar_tipo_operacion(titulo, descripcion, precio)
                
                datos = {
                    "id": pid,
                    "link": url,
                    "titulo": titulo,
                    "precio": precio,
                    "ciudad": ciudad,
                    "ubicacion_exacta": ubicacion,
                    "recamaras": caracteristicas["recamaras"],
                    "banos": caracteristicas["banos"],
                    "metros_terreno": caracteristicas["metros_terreno"],
                    "metros_construccion": caracteristicas["metros_construccion"],
                    "vendedor": vendedor,
                    "link_vendedor": link_v,
                    "descripcion": descripcion,
                    "imagen_portada": img_portada,
                    "tipo_operacion": tipo_op
                }
                guardar_html_y_json(html, datos, ciudad, pid, carpeta, date_str)
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