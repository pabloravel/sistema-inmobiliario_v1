#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion_v4.py

Versión optimizada para extracción rápida con mejoras en:
- Reducción de timeouts
- Procesamiento paralelo
- Extracción eficiente
- Mejor manejo de errores
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple
import logging
from tqdm import tqdm

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Constantes optimizadas
TIMEOUT_NAVEGACION = 15  # segundos
TIMEOUT_ELEMENTO = 5     # segundos
MAX_WORKERS = 4         # workers para procesamiento paralelo
MAX_REINTENTOS = 2      # máximo de reintentos por propiedad

# Rutas
CARPETA_LINKS = "resultados/links/repositorio_unico.json"
CARPETA_RESULTADOS = "resultados"
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
BASE_URL = "https://www.facebook.com"

# Configuración de almacenamiento de sesión
STORAGE_DIR = ".localstorage"
ESTADO_FB = os.path.join(STORAGE_DIR, "facebook.storage.local")

# Crear directorios necesarios
os.makedirs(STORAGE_DIR, exist_ok=True)
os.makedirs(CARPETA_RESULTADOS, exist_ok=True)

def extraer_descripcion_estable(soup, page) -> str:
    """Extrae la descripción de la propiedad de manera robusta"""
    descripcion = ""
    
    # 1. Buscar por el contenedor principal de descripción
    for div in soup.find_all("div"):
        if div.get_text(strip=True) in ["Descripción", "Detalles"]:
            siguiente = div.find_next_sibling("div")
            if siguiente:
                descripcion = siguiente.get_text(separator="\n", strip=True)
                break
    
    # 2. Si no se encontró, buscar por estructura alternativa
    if not descripcion:
        # Buscar divs que contengan texto largo
        for div in soup.find_all("div"):
            texto = div.get_text(strip=True)
            if len(texto) > 100 and any(palabra in texto.lower() for palabra in 
                ["recámara", "baño", "m2", "metros", "construcción", "terreno"]):
                descripcion = texto
                break
    
    # 3. Limpiar la descripción
    descripcion = descripcion.replace("Ver menos", "").strip()
    descripcion = re.sub(r'\s+', ' ', descripcion)  # Normalizar espacios
    
    return descripcion

def extraer_precio_mejorado(soup) -> Dict:
    """Extrae el precio con formato mejorado"""
    precio_str = ""
    moneda = "MXN"
    
    # 1. Buscar por span con precio
    for span in soup.find_all("span"):
        texto = span.get_text(strip=True)
        if texto.startswith("$") and len(texto) < 30:
            precio_str = texto
            break
    
    # 2. Normalizar precio
    if precio_str:
        # Eliminar caracteres no numéricos excepto punto y coma
        precio_limpio = re.sub(r'[^\d.,]', '', precio_str)
        try:
            # Convertir a float para normalización
            precio_num = float(precio_limpio.replace(',', ''))
            # Formatear con separadores de miles
            precio_str = "${:,.3f}".format(precio_num)
        except:
            pass
    
    return {
        "precio_str": precio_str,
        "moneda": moneda
    }

def extraer_ubicacion_mejorada(soup, page) -> Dict:
    """Extrae la ubicación con formato mejorado"""
    ubicacion = {
        "direccion": "",
        "colonia": "",
        "ciudad": "",
        "estado": "",
        "referencias": []
    }
    
    # 1. Buscar por sección de ubicación
    for div in soup.find_all("div"):
        if "Ubicación" in div.get_text(strip=True):
            siguiente = div.find_next_sibling("div")
            if siguiente:
                ubicacion["direccion"] = siguiente.get_text(strip=True)
                break
    
    # 2. Extraer referencias de la descripción
    descripcion = extraer_descripcion_estable(soup, page)
    referencias = re.findall(r'(?:cerca de|junto a|frente a|a \d+ minutos? de)(.*?)(?:\.|,|$)', descripcion.lower())
    ubicacion["referencias"] = [ref.strip() for ref in referencias if ref.strip()]
    
    return ubicacion

def extraer_caracteristicas(soup) -> Dict:
    """Extrae características de la propiedad"""
    texto_completo = soup.get_text(" ", strip=True).lower()
    
    caracteristicas = {
        "recamaras": None,
        "banos": None,
        "estacionamientos": None,
        "metros_terreno": None,
        "metros_construccion": None,
        "niveles": None
    }
    
    # Extraer números
    patrones = {
        "recamaras": r'(\d+)\s*(?:recámaras?|recamaras?|habitaciones?|dormitorios?)',
        "banos": r'(\d+)\s*(?:baños?|banos?)',
        "estacionamientos": r'(\d+)\s*(?:estacionamientos?|cajones?|autos?)',
        "metros_terreno": r'(?:terreno|superficie)\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts|metros?)',
        "metros_construccion": r'(?:construcción|construccion)\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts|metros?)',
        "niveles": r'(\d+)\s*(?:niveles?|pisos?|plantas?)'
    }
    
    for campo, patron in patrones.items():
        if match := re.search(patron, texto_completo):
            try:
                caracteristicas[campo] = int(match.group(1))
            except:
                pass
    
    return caracteristicas

def extraer_amenidades(soup) -> Dict[str, bool]:
    """Extrae amenidades de la propiedad"""
    texto = soup.get_text(" ", strip=True).lower()
    
    amenidades = {
        "alberca": False,
        "jardin": False,
        "seguridad": False,
        "gimnasio": False,
        "areas_comunes": False,
        "terraza": False,
        "roof_garden": False,
        "cuarto_servicio": False,
        "cocina_equipada": False
    }
    
    patrones = {
        "alberca": r'alberca|piscina|chapoteadero',
        "jardin": r'jardin|jardín|área verde',
        "seguridad": r'seguridad|vigilancia|24/7|caseta',
        "gimnasio": r'gimnasio|gym',
        "areas_comunes": r'areas?\s*comunes?|salon|salón',
        "terraza": r'terraza|balcon|balcón',
        "roof_garden": r'roof\s*garden|roofgarden|terraza',
        "cuarto_servicio": r'cuarto\s*(?:de)?\s*servicio',
        "cocina_equipada": r'cocina\s*(?:integral|equipada)'
    }
    
    for amenidad, patron in patrones.items():
        if re.search(patron, texto):
            amenidades[amenidad] = True
    
    return amenidades

def extraer_legal(soup) -> Dict:
    """Extrae información legal de la propiedad"""
    texto = soup.get_text(" ", strip=True).lower()
    
    legal = {
        "escrituras": False,
        "predial": "no especificado",
        "servicios": [],
        "creditos": []
    }
    
    # Verificar escrituras
    if re.search(r'escrituras?|título\s*de\s*propiedad', texto):
        legal["escrituras"] = True
    
    # Verificar predial
    if "predial al corriente" in texto:
        legal["predial"] = "al corriente"
    
    # Detectar servicios
    servicios = re.findall(r'(?:luz|agua|gas|internet|teléfono|telefono|drenaje)', texto)
    legal["servicios"] = list(set(servicios))
    
    # Detectar créditos aceptados
    creditos = re.findall(r'(?:infonavit|fovissste|bancario|hipotecario)', texto)
    legal["creditos"] = list(set(creditos))
    
    return legal

def extraer_datos_vendedor(soup, page) -> Dict:
    """Extrae información del vendedor"""
    vendedor = {
        "nombre": "",
        "tipo": "particular",  # o "inmobiliaria"
        "telefono": "",
        "perfil": ""
    }
    
    # Buscar link del vendedor
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "facebook.com/profile.php?id=" in href or "facebook.com/marketplace/profile" in href:
            vendedor["perfil"] = href
            nombre = a.find("strong")
            if nombre:
                vendedor["nombre"] = nombre.get_text(strip=True)
            break
    
    # Detectar si es inmobiliaria
    texto_completo = soup.get_text(" ", strip=True).lower()
    if any(palabra in texto_completo for palabra in ["inmobiliaria", "bienes raíces", "real estate", "broker"]):
        vendedor["tipo"] = "inmobiliaria"
    
    # Extraer teléfono si está visible
    telefonos = re.findall(r'(?:\+52|52)?[1-9][0-9]{9}', texto_completo)
    if telefonos:
        vendedor["telefono"] = telefonos[0]
    
    return vendedor

def detectar_tipo_operacion(titulo: str, descripcion: str, precio_str: str) -> str:
    """Detecta el tipo de operación (venta/renta) de manera más precisa"""
    texto = f"{titulo} {descripcion} {precio_str}".lower()
    
    # 1. Palabras clave de renta
    if any(palabra in texto for palabra in [
        "renta", "alquiler", "arrendamiento", "arriendo",
        "mensual", "/mes", "por mes", "al mes",
        "depósito", "deposito", "fiador",
        "mantenimiento mensual"
    ]):
        return "Renta"
    
    # 2. Palabras clave de venta
    if any(palabra in texto for palabra in [
        "venta", "vendo", "remato", "traspaso",
        "escrituras", "crédito", "credito", "infonavit",
        "fovissste", "bancario", "hipotecario",
        "cesión de derechos", "cesion de derechos"
    ]):
        return "Venta"
    
    # 3. Inferir por precio
    try:
        precio_num = float(re.sub(r'[^\d.]', '', precio_str))
        if precio_num >= 300_000:  # Si es mayor a 300mil, probablemente es venta
            return "Venta"
        elif precio_num <= 50_000:  # Si es menor a 50mil, probablemente es renta
            return "Renta"
    except:
        pass
    
    return "Venta"  # Por defecto asumimos venta

def detectar_tipo_propiedad(titulo: str, descripcion: str) -> str:
    """Detecta el tipo de propiedad"""
    texto = f"{titulo} {descripcion}".lower()
    
    if any(x in texto for x in ["casa sola", "casa individual", "casa única"]):
        return "casa sola"
    elif any(x in texto for x in ["casa", "residencia", "chalet"]):
        return "casa"
    elif any(x in texto for x in ["departamento", "depto", "apartamento"]):
        return "departamento"
    elif any(x in texto for x in ["terreno", "lote", "predio"]):
        return "terreno"
    elif any(x in texto for x in ["local", "comercial"]):
        return "local"
    elif any(x in texto for x in ["oficina"]):
        return "oficina"
    
    return "No especificado"

def extraer_cuota_mantenimiento(descripcion: str) -> str:
    """Extrae la cuota de mantenimiento de la descripción"""
    texto = descripcion.lower()
    patron = r'mantenimiento.*?(\$[\d,]+(?:\.\d{2})?)'
    if match := re.search(patron, texto):
        return match.group(1)
    return ""

def extraer_medio_bano(descripcion: str) -> int:
    """Extrae la cantidad de medios baños"""
    texto = descripcion.lower()
    patron = r'(\d+)\s*(?:medio|medios)\s*baños?'
    if match := re.search(patron, texto):
        return int(match.group(1))
    elif "medio baño" in texto:
        return 1
    return 0

def procesar_propiedad(page, link, id_propiedad, ciudad, fecha_str):
    """Procesa una propiedad y retorna sus datos"""
    try:
        # Obtener HTML y crear soup
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Extraer datos básicos
        titulo = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
        
        # Intentar expandir descripción
        try:
            # Buscar todos los "Ver más" visibles
            ver_mas = page.locator("text=Ver más").all()
            for boton in ver_mas:
                try:
                    if boton.is_visible():
                        boton.click()
                        page.wait_for_timeout(1000)
                except:
                    continue
            
            # Buscar también por selector específico
            ver_mas_alt = page.locator('span:has-text("Ver más")').all()
            for boton in ver_mas_alt:
                try:
                    if boton.is_visible():
                        boton.click()
                        page.wait_for_timeout(1000)
                except:
                    continue
        except Exception as e:
            print(f"Aviso: No se pudo expandir la descripción: {str(e)}")
        
        # Actualizar HTML y soup después de expandir
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Extraer el resto de datos
        descripcion = extraer_descripcion_estable(soup, page)
        precio = extraer_precio_mejorado(soup)
        ubicacion = extraer_ubicacion_mejorada(soup, page)
        caracteristicas = extraer_caracteristicas(soup)
        amenidades = extraer_amenidades(soup)
        legal = extraer_legal(soup)
        
        # Detectar tipo de operación y propiedad
        tipo_op = detectar_tipo_operacion(titulo, descripcion, precio["precio_str"])
        tipo_prop = detectar_tipo_propiedad(titulo, descripcion)
        
        # Construir datos completos en el formato requerido
        datos = {
            "id": id_propiedad,
            "link": link,
            "descripcion_original": descripcion,
            "ubicacion": {
                "colonia": ubicacion.get("colonia", ""),
                "calle": ubicacion.get("direccion", ""),
                "estado": "Morelos",
                "ciudad": "Cuernavaca",
                "zona": ubicacion.get("zona", ""),
                "ubicacion_referencia": ubicacion.get("direccion", ""),
                "puntos_interes": ubicacion.get("referencias", [])
            },
            "propiedad": {
                "tipo_propiedad": tipo_prop.lower(),
                "precio": precio["precio_str"],
                "mantenimiento": {
                    "cuota_mantenimiento": extraer_cuota_mantenimiento(descripcion),
                    "periodo": "mensual" if extraer_cuota_mantenimiento(descripcion) else "",
                    "incluye": []
                },
                "tipo_operacion": tipo_op,
                "moneda": "MXN"
            },
            "descripcion": {
                "caracteristicas": {
                    "recamaras": caracteristicas.get("recamaras", 0),
                    "banos": caracteristicas.get("banos", 0),
                    "medio_bano": extraer_medio_bano(descripcion),
                    "niveles": caracteristicas.get("niveles", 1),
                    "estacionamientos": caracteristicas.get("estacionamientos", 0),
                    "edad": "",
                    "recamara_planta_baja": "planta baja" in descripcion.lower(),
                    "cisterna": "cisterna" in descripcion.lower(),
                    "superficie_m2": caracteristicas.get("metros_terreno", 0),
                    "construccion_m2": caracteristicas.get("metros_construccion", 0)
                },
                "amenidades": {
                    "seguridad": amenidades.get("seguridad", False),
                    "alberca": amenidades.get("alberca", False),
                    "patio": "patio" in descripcion.lower(),
                    "bodega": "bodega" in descripcion.lower(),
                    "terraza": amenidades.get("terraza", False),
                    "jardin": amenidades.get("jardin", False),
                    "estudio": "estudio" in descripcion.lower(),
                    "roof_garden": amenidades.get("roof_garden", False)
                },
                "legal": {
                    "escrituras": legal.get("escrituras", False),
                    "cesion_derechos": "cesion" in descripcion.lower() or "cesión" in descripcion.lower(),
                    "formas_de_pago": legal.get("creditos", [])
                }
            }
        }
        
        # Guardar archivos
        carpeta = os.path.join(CARPETA_RESULTADOS, fecha_str)
        os.makedirs(carpeta, exist_ok=True)
        
        # Guardar HTML
        ruta_html = os.path.join(carpeta, f"{ciudad}-{fecha_str}-{id_propiedad}.html")
        with open(ruta_html, "w", encoding="utf-8") as f:
            f.write(html)
        
        # Guardar JSON
        ruta_json = os.path.join(carpeta, f"{ciudad}-{fecha_str}-{id_propiedad}.json")
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        return datos
        
    except Exception as e:
        print(f"Error extrayendo datos: {str(e)}")
        return None

def verificar_sesion_facebook(page) -> bool:
    """Verifica si hay una sesión activa de Facebook"""
    try:
        # Intentar acceder a una página de Facebook
        page.goto("https://www.facebook.com/marketplace/category/propertyrentals", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Verificar si hay un botón de login visible
        login_button = page.locator('text="Iniciar sesión"').first
        if login_button and login_button.is_visible():
            print("\n❌ No hay sesión activa de Facebook.")
            print("Ejecutando script de login...")
            
            # Cerrar el navegador actual
            page.close()
            browser = page.context.browser
            browser.close()
            
            # Ejecutar script de login y ESPERAR a que termine
            import subprocess
            subprocess.run(['python3', 'guarda_login.py'], check=True)
            
            print("\n✓ Script de login completado.")
            print("✓ Esperando 5 segundos para asegurar que la sesión se guardó...")
            time.sleep(5)
            
            print("✓ Sesión actualizada")
            return True
        
        # Si llegamos aquí, la sesión está activa
        print("✓ Sesión de Facebook verificada")
        return True
        
    except Exception as e:
        print(f"❌ Error verificando sesión de Facebook: {str(e)}")
        return False

def descargar_imagen_por_playwright(page, ciudad, pid, carpeta, date_str) -> str:
    """Descarga la imagen de portada usando Playwright"""
    try:
        # Buscar la primera imagen que sea portada
        img = page.locator('img[alt^="Foto de"]').first
        if not img.is_visible():
            img = page.locator('img').first
        
        if not img or not img.is_visible():
            return ""
            
        src = img.get_attribute('src')
        if not src or not src.startswith("http"):
            return ""
            
        # Crear nombre de archivo
        filename = f"{ciudad}-{date_str}-{pid}.jpg"
        path_img = os.path.join(carpeta, filename)
        
        # Descargar imagen
        try:
            resp = requests.get(src, timeout=10)
            if resp.status_code == 200:
                os.makedirs(os.path.dirname(path_img), exist_ok=True)
                with open(path_img, "wb") as f:
                    f.write(resp.content)
                return filename
        except:
            pass
            
        return ""
    except Exception as e:
        print(f"Error descargando imagen: {str(e)}")
        return ""

def main():
    """Función principal"""
    # 1) Maestro previo
    try:
        with open(CARPETA_REPO_MASTER, "r", encoding="utf-8") as f:
            data_master = json.load(f)
            print(f"Repositorio maestro cargado con {len(data_master)} propiedades\n")
    except:
        print("Creando nuevo repositorio maestro")
        data_master = {}

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

    # 3) Filtra pendientes y limita a 5 propiedades
    pending = [l for l in links if l["id"] not in data_master][:5]

    # ── PRINT RESUMEN ANTES DE EMPEZAR ──
    total = len(links)
    falta = len(pending)
    print(f"Total de propiedades: {total}, procesando {falta} propiedades de prueba")

    # 4) Carpeta diaria
    date_str = datetime.now().strftime("%Y-%m-%d")

    # 5) Inicializar contadores
    procesadas = 0
    errores = 0
    
    # Barra de progreso
    pbar = tqdm(total=falta, desc="Extrayendo propiedades", unit="propiedad")

    # 6) Procesar propiedades
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=ESTADO_FB if os.path.exists(ESTADO_FB) else None)
        
        for item in pending:
            try:
                # Crear nueva página
                page = context.new_page()
                
                # Verificar sesión en la primera iteración
                if procesadas == 0:
                    if not verificar_sesion_facebook(page):
                        raise Exception("No se pudo verificar la sesión de Facebook")
                
                # Procesar propiedad
                t0 = time.time()
                datos = procesar_propiedad(page, item["link"], item["id"], item["ciudad"], date_str)
                
                if datos:
                    # Guardar en repositorio maestro
                    data_master[item["id"]] = datos
                    with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as f:
                        json.dump(data_master, f, ensure_ascii=False, indent=2)
                    
                    procesadas += 1
                    print(f"   ✓ {item['id']} procesado en {time.time()-t0:.1f}s")
                else:
                    errores += 1
                    print(f"   ❌ Error procesando {item['id']}")
                
                # Cerrar página
                page.close()
                
            except Exception as e:
                print(f"\n❌ Error general: {str(e)}")
                print("Reintentando...")
                errores += 1
                continue
            
            finally:
                # Actualizar barra de progreso
                pbar.update(1)
        
        # Cerrar navegador
        browser.close()
    
    # Cerrar barra de progreso
    pbar.close()
    
    # Imprimir estadísticas
    print("\n=== ESTADÍSTICAS DE EXTRACCIÓN ===")
    print(f"Total propiedades procesadas: {procesadas}")
    print(f"- Exitosas: {procesadas - errores}")
    print(f"- Con errores: {errores}")
    print(f"\nTotal de propiedades en el repositorio maestro: {len(data_master)}")

if __name__ == "__main__":
    main() 