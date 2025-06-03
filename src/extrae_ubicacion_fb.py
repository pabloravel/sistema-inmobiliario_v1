#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_ubicacion_fb.py

Script especializado en la extracción de ubicaciones de propiedades en Facebook Marketplace.
Basado en extrae_html_con_operacion.py pero con funciones adicionales para ubicación.
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

# Barra de progreso (idéntica a la original)
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

def extraer_y_guardar_dom(page, ciudad, pid, carpeta, date_str):
    """Extrae y guarda el DOM completo de la página"""
    try:
        # Obtener el DOM usando evaluate
        dom = page.evaluate("""() => {
            return document.documentElement.outerHTML;
        }""")
        
        # Crear nombre de archivo para el DOM
        filename = f"{ciudad}-{date_str}-{pid}-dom.html"
        path_dom = os.path.join(carpeta, filename)
        
        # Guardar el DOM
        with open(path_dom, "w", encoding="utf-8") as f:
            f.write(dom)
            
        return filename, dom
    except Exception as e:
        print(f"Error al extraer DOM para {pid}: {e}")
        return "", ""

def extraer_ubicacion_desde_dom(dom_str):
    """
    Extrae la ubicación desde el DOM guardado, específicamente del span que aparece debajo del precio
    """
    ubicacion = {
        "direccion_completa": "",
        "ciudad": "",
        "estado": "",
        "texto_original": ""
    }
    
    try:
        soup = BeautifulSoup(dom_str, 'html.parser')
        
        # Buscar el span específico que contiene la ubicación (debajo del precio)
        # Buscamos un span que tenga la clase x193iq5w y que esté dentro de un div con role="listitem"
        ubicacion_span = None
        for div in soup.find_all('div', attrs={'role': 'listitem'}):
            span = div.find('span', class_=lambda x: x and 'x193iq5w' in x)
            if span:
                texto = span.get_text(strip=True)
                if texto and any(ciudad in texto.lower() for ciudad in ["cuernavaca", "jiutepec", "temixco", "zapata", "yautepec", "morelos", "mor"]):
                    ubicacion_span = span
                    break
        
        if ubicacion_span:
            texto = ubicacion_span.get_text(strip=True)
            print(f"DEBUG - Texto de ubicación encontrado: {texto}")
            
            ubicacion["texto_original"] = texto
            ubicacion["direccion_completa"] = texto
            
            # Primero buscar el estado
            texto_lower = texto.lower()
            if any(estado in texto_lower for estado in ["mor", "mor.", "morelos"]):
                ubicacion["estado"] = "Morelos"
            
            # Luego buscar la ciudad en cualquier parte del texto
            if "cuernavaca" in texto_lower:
                ubicacion["ciudad"] = "Cuernavaca"
            elif "jiutepec" in texto_lower:
                ubicacion["ciudad"] = "Jiutepec"
            elif "temixco" in texto_lower:
                ubicacion["ciudad"] = "Temixco"
            elif "zapata" in texto_lower or "emiliano zapata" in texto_lower:
                ubicacion["ciudad"] = "Emiliano Zapata"
            elif "yautepec" in texto_lower:
                ubicacion["ciudad"] = "Yautepec"

    except Exception as e:
        print(f"Error al extraer ubicación desde DOM: {e}")
    
    return ubicacion

def main():
    # 1) Carpeta para resultados
    date_str = datetime.now().strftime("%Y-%m-%d")
    carpeta  = os.path.join(CARPETA_RESULTADOS, f"{date_str}_ubicaciones")
    os.makedirs(carpeta, exist_ok=True)

    # 2) Carpeta donde están los archivos DOM
    dom_carpeta = os.path.join(CARPETA_RESULTADOS, "2025-05-29")
    
    # 3) Obtener lista de archivos DOM
    dom_files = []
    for file in os.listdir(dom_carpeta):
        if file.endswith("-dom.html"):
            # Extraer el ID del nombre del archivo
            parts = file.split("-")
            if len(parts) >= 4:
                pid = parts[-2]  # El ID está antes de "-dom.html"
                ciudad = parts[0]
                dom_files.append({"id": pid, "ciudad": ciudad, "file": file})
    
    # Tomar 20 archivos para prueba
    dom_files = dom_files[:20]
    
    # 4) Procesar los archivos DOM
    total = len(dom_files)
    pbar = ProgressBar(total, desc="Extrayendo ubicaciones", unit="propiedad")
    ok = err = 0
    
    resultados = []
    
    for item in dom_files:
        pid = item["id"]
        ciudad = item["ciudad"]
        t0 = time.time()
        try:
            print(f"\nProcesando {pid}")
            
            # Leer el archivo DOM
            dom_file = os.path.join(dom_carpeta, item["file"])
            with open(dom_file, "r", encoding="utf-8") as f:
                dom_content = f.read()
            
            # Extraer ubicación desde el DOM
            ubicacion = extraer_ubicacion_desde_dom(dom_content)
            
            if ubicacion["texto_original"]:
                print(f"Ubicación encontrada: {ubicacion['texto_original']}")
                print(f"Ciudad normalizada: {ubicacion['ciudad']}")
                print(f"Estado: {ubicacion['estado']}")
                
                # Guardar resultados
                datos = {
                    "id": pid,
                    "ubicacion": ubicacion,
                    "dom_file": os.path.basename(dom_file),
                    "fecha_extraccion": datetime.now().isoformat()
                }
                
                resultados.append(datos)
                
                # Guardar en archivo individual
                ruta_json = os.path.join(carpeta, f"{ciudad}-{date_str}-{pid}-ubicacion.json")
                with open(ruta_json, "w", encoding="utf-8") as f:
                    json.dump(datos, f, ensure_ascii=False, indent=2)
                
                ok += 1
            else:
                print(f"No se encontró ubicación para {pid}")
                err += 1
                
        except Exception as e:
            err += 1
            print(f"\n❌ Error en {pid}: {e}")
        finally:
            pbar.update(1, ok=ok, err=err, last_time=time.time()-t0)

    pbar.close()
    
    # Guardar todos los resultados en un solo archivo
    ruta_resultados = os.path.join(carpeta, f"resultados_ubicaciones_{date_str}.json")
    with open(ruta_resultados, "w", encoding="utf-8") as f:
        json.dump({
            "total_procesados": total,
            "exitosos": ok,
            "errores": err,
            "fecha_proceso": datetime.now().isoformat(),
            "resultados": resultados
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\nTotal de ubicaciones procesadas: {ok}")
    print(f"Total de errores: {err}")
    print(f"\nResultados guardados en: {ruta_resultados}")

if __name__ == '__main__':
    main() 