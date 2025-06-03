#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
actualiza_precios.py

Script para actualizar solo los precios en el repositorio maestro
usando la función simple de extracción de precios.
"""

import os
import json
from datetime import datetime
from bs4 import BeautifulSoup
from tqdm import tqdm

# Rutas
CARPETA_RESULTADOS = "resultados"
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
BACKUP_REPO = os.path.join(CARPETA_RESULTADOS, f"repositorio_propiedades_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

def extraer_precio(soup):
    """Función simple para extraer precio."""
    for span in soup.find_all("span"):
        t = span.get_text(strip=True)
        if t.startswith("$") and len(t) < 30:
            return t
    return ""

def actualizar_precios():
    # 1. Crear backup del repositorio actual
    if os.path.exists(CARPETA_REPO_MASTER):
        with open(CARPETA_REPO_MASTER, "r", encoding="utf-8") as f:
            repo_master = json.load(f)
        
        # Guardar backup
        with open(BACKUP_REPO, "w", encoding="utf-8") as f:
            json.dump(repo_master, f, ensure_ascii=False, indent=2)
        
        print(f"Backup creado en: {BACKUP_REPO}")
    else:
        print("Error: No se encontró el repositorio maestro")
        return

    # 2. Procesar cada propiedad
    propiedades_actualizadas = 0
    propiedades_sin_html = 0
    
    print("\nActualizando precios...")
    for pid, datos in tqdm(repo_master.items(), desc="Procesando propiedades"):
        try:
            # Obtener la fecha de extracción
            fecha_str = datos.get("fecha_extraccion", "").split("T")[0]
            if not fecha_str:
                print(f"Advertencia: Propiedad {pid} no tiene fecha de extracción")
                continue
                
            # Construir ruta al archivo HTML
            ciudad = datos.get("ciudad", "cuernavaca").lower()
            ruta_html = os.path.join(CARPETA_RESULTADOS, fecha_str, f"{ciudad}-{fecha_str}-{pid}.html")
            
            if not os.path.exists(ruta_html):
                propiedades_sin_html += 1
                continue
                
            # Leer archivo HTML
            with open(ruta_html, "r", encoding="utf-8") as f:
                html = f.read()
                
            # Extraer nuevo precio
            soup = BeautifulSoup(html, "html.parser")
            nuevo_precio = extraer_precio(soup)
            
            if nuevo_precio:
                # Actualizar precio en el repositorio
                datos["precio"] = nuevo_precio
                propiedades_actualizadas += 1
                
        except Exception as e:
            print(f"\nError procesando propiedad {pid}: {str(e)}")
            
    # 3. Guardar repositorio actualizado
    with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as f:
        json.dump(repo_master, f, ensure_ascii=False, indent=2)
        
    print(f"\nProceso completado:")
    print(f"- Total de propiedades en repositorio: {len(repo_master)}")
    print(f"- Propiedades actualizadas: {propiedades_actualizadas}")
    print(f"- Propiedades sin HTML: {propiedades_sin_html}")
    print(f"- Backup guardado en: {BACKUP_REPO}")
    print(f"- Repositorio actualizado guardado en: {CARPETA_REPO_MASTER}")

if __name__ == "__main__":
    actualizar_precios() 