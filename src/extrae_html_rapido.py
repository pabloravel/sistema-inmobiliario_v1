#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_rapido.py

Versión optimizada que solo extrae datos básicos:
- Título
- Descripción expandida
- Precio
- HTML completo
"""

import os
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

class ProgressBar:
    def __init__(self, total):
        self.total = total
        self.n = 0
        self.start_time = time.time()
        
    def update(self):
        self.n += 1
        tiempo_transcurrido = time.time() - self.start_time
        tiempo_promedio = tiempo_transcurrido / self.n if self.n > 0 else 0
        tiempo_restante = tiempo_promedio * (self.total - self.n)
        
        print(f"\rProcesando: {self.n}/{self.total} "
              f"[{self.n/self.total*100:.1f}%] "
              f"Tiempo promedio: {tiempo_promedio:.1f}s "
              f"Restante: {tiempo_restante/60:.1f}min", 
              end="")

def expandir_descripcion(page):
    """Intenta expandir el 'Ver más' de manera eficiente"""
    try:
        # Buscar y hacer clic en todos los "Ver más" visibles
        ver_mas = page.locator("text=Ver más").all()
        for boton in ver_mas:
            if boton.is_visible():
                boton.click(force=True)
                time.sleep(0.5)  # Espera mínima
    except:
        pass

def extraer_datos_basicos(page, soup):
    """Extrae los datos básicos de la propiedad"""
    # Expandir descripción
    expandir_descripcion(page)
    
    # Obtener HTML actualizado
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    
    # Extraer título
    titulo = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
    
    # Extraer descripción
    descripcion = ""
    for div in soup.find_all("div"):
        if div.get_text(strip=True) in ["Descripción", "Detalles"]:
            if siguiente := div.find_next_sibling("div"):
                descripcion = siguiente.get_text(strip=True)
                break
    
    # Extraer precio
    precio = "0"
    for span in soup.find_all("span"):
        texto = span.get_text(strip=True)
        if texto.startswith("$") and len(texto) < 30:
            precio = texto
            break
    
    return {
        "titulo": titulo,
        "descripcion": descripcion,
        "precio": precio,
        "html": html
    }

def procesar_propiedad(page, link, id_propiedad, ciudad="cuernavaca"):
    """Procesa una propiedad y retorna sus datos"""
    try:
        # Navegar a la página
        page.goto(link, timeout=30000)
        page.wait_for_timeout(2000)
        
        # Extraer datos básicos
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        datos_basicos = extraer_datos_basicos(page, soup)
        
        # Construir estructura de datos
        datos = {
            "id": id_propiedad,
            "link": link,
            "datos_basicos": datos_basicos,
            "metadata": {
                "fecha_extraccion": datetime.now().isoformat(),
                "status": "completo",
                "errores": []
            }
        }
        
        # Validar datos básicos
        if not datos_basicos["titulo"] or not datos_basicos["descripcion"]:
            datos["metadata"]["status"] = "incompleto"
            if not datos_basicos["titulo"]:
                datos["metadata"]["errores"].append("Falta título")
            if not datos_basicos["descripcion"]:
                datos["metadata"]["errores"].append("Falta descripción")
        
        return datos
        
    except Exception as e:
        print(f"❌ Error procesando {id_propiedad}: {str(e)}")
        return None

def main():
    # Cargar enlaces
    with open("resultados/links/repositorio_unico.json", "r", encoding="utf-8") as f:
        enlaces = json.load(f)
    
    # Limitar a 10 publicaciones
    enlaces = enlaces[:10]
    
    # Preparar directorio de resultados
    fecha_str = datetime.now().strftime("%Y-%m-%d")
    carpeta_resultados = f"resultados/datos_crudos/{fecha_str}"
    os.makedirs(carpeta_resultados, exist_ok=True)
    
    print(f"\n🔍 Procesando {len(enlaces)} publicaciones")
    print(f"📁 Guardando resultados en: {carpeta_resultados}\n")
    
    # Inicializar progreso
    total = len(enlaces)
    progress = ProgressBar(total)
    
    # Estadísticas
    tiempos = []
    errores = 0
    completos = 0
    
    # Procesar propiedades
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        
        for item in enlaces:
            t0 = time.time()
            
            # Normalizar formato de enlace
            if isinstance(item, str):
                link = item
                pid = item.rstrip("/").split("/")[-1]
                ciudad = "cuernavaca"
            else:
                link = item.get("link", "")
                pid = item.get("id", link.rstrip("/").split("/")[-1])
                ciudad = item.get("ciudad", "cuernavaca").lower()
            
            # Asegurar URL completa
            if link.startswith("/"):
                link = "https://www.facebook.com" + link
            
            try:
                # Procesar propiedad
                datos = procesar_propiedad(page, link, pid, ciudad)
                
                if datos:
                    # Guardar resultados
                    ruta_json = os.path.join(carpeta_resultados, f"{ciudad}-{pid}.json")
                    with open(ruta_json, "w", encoding="utf-8") as f:
                        json.dump(datos, f, ensure_ascii=False, indent=2)
                    
                    if datos["metadata"]["status"] == "completo":
                        completos += 1
                    else:
                        errores += 1
                else:
                    errores += 1
                
            except Exception as e:
                print(f"\n❌ Error en {pid}: {str(e)}")
                errores += 1
            
            # Actualizar estadísticas
            tiempo = time.time() - t0
            tiempos.append(tiempo)
            tiempo_promedio = sum(tiempos) / len(tiempos)
            
            # Actualizar progreso
            progress.update()
            
            # Mostrar estadísticas cada 5 propiedades
            if len(tiempos) % 5 == 0:
                print(f"\n📊 Estadísticas parciales:")
                print(f"   ✓ Completados: {completos}")
                print(f"   ❌ Errores: {errores}")
                print(f"   ⏱️  Tiempo promedio: {tiempo_promedio:.1f}s")
        
        # Cerrar navegador
        browser.close()
    
    # Mostrar resumen final
    print("\n=== RESUMEN FINAL ===")
    print(f"✅ Propiedades completadas: {completos}")
    print(f"❌ Errores: {errores}")
    print(f"⏱️  Tiempo promedio por propiedad: {sum(tiempos)/len(tiempos):.1f}s")
    print(f"📁 Resultados guardados en: {carpeta_resultados}")

if __name__ == "__main__":
    main() 