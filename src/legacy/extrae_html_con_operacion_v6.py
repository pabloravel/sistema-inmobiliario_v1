#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion_v6.py

Versión 6.0 - Combinación optimizada de v3 y v5
Cambios y mejoras:
- Incorpora el sistema robusto de detección de disponibilidad de v5
- Usa el sistema mejorado de extracción de datos de v3
- Mejor manejo de errores y timeouts
- Sistema de logging mejorado
- Guardado incremental de datos
- Verificación periódica de propiedades no disponibles
- Normalización mejorada de datos
- Extracción más precisa de características
- Sistema de reintentos para datos faltantes

Historial de cambios:
v6.0 (2024-03-21):
- Combinación inicial de v3 y v5
- Mejora en extracción de datos
- Sistema de detección de disponibilidad

v5.0:
- Sistema de detección de disponibilidad
- Manejo de propiedades no disponibles
- Estadísticas mejoradas

v3.0:
- Sistema robusto de extracción de datos
- Mejor normalización de texto
- Patrones mejorados de extracción
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
from concurrent.futures import ThreadPoolExecutor
import traceback
import logging
import signal
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('facebook_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Variables globales para el manejo de señales
INTERRUPT_RECEIVED = False

# ── Rutas y constantes ────────────────────────────────────────────────
CARPETA_LINKS       = "resultados/links/repositorio_unico.json"
CARPETA_RESULTADOS  = "resultados"
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
ESTADO_FB           = "fb_state.json"
BASE_URL            = "https://www.facebook.com"

class ProgressBar:
    MAGENTA = "\033[35m"
    RESET   = "\033[0m"
    def __init__(self, total, desc='', unit=''):
        self.total = total
        self.n = 0
        self.ok = 0
        self.err = 0
        self.desc = desc
        self.unit = unit
        self.width = os.get_terminal_size().columns - 40
        print(f"{self.desc}: 0/{self.total} {self.unit}")
        
    def update(self, n=1, ok=None, err=None, last_time=None):
        self.n += n
        if ok is not None: self.ok = ok
        if err is not None: self.err = err
        p = int(self.width * self.n / self.total)
        print(f"\033[A{self.desc}: {self.n}/{self.total} {self.unit}")
        print(f"{self.MAGENTA}{'█'*p}{'-'*(self.width-p)} OK:{self.ok} Err:{self.err}{self.RESET}")
        if last_time:
            print(f"Tiempo transcurrido: {last_time:.2f}s")
    
    def close(self):
        print()

def normalizar_texto(texto):
    """Normaliza un texto eliminando espacios extras y caracteres especiales"""
    if not texto:
        return ""
    # Eliminar espacios múltiples y caracteres especiales
    texto = re.sub(r'\s+', ' ', texto)
    texto = texto.strip()
    return texto.lower()

def extraer_numero(texto, patron):
    """Extrae un número de un texto usando un patrón regex"""
    if match := re.search(patron, normalizar_texto(texto)):
        try:
            return int(match.group(1))
        except:
            pass
    return None

def normalizar_precio(texto):
    """Normaliza el formato del precio"""
    if not texto:
        return {"valor": 0, "moneda": "MXN", "formato": "$0.00"}
    
    # Eliminar todo excepto números y punto decimal
    nums = ''.join(c for c in texto if c.isdigit() or c == '.')
    try:
        valor = float(nums)
        return {
            "valor": valor,
            "moneda": "MXN",
            "formato": f"${valor:,.2f}"
        }
    except:
        return {"valor": 0, "moneda": "MXN", "formato": "$0.00"}

def extraer_descripcion_mejorada(soup, page):
    """Extrae la descripción usando múltiples métodos"""
    descripcion = ""
    
    # Método 1: Buscar después de "Descripción" o "Detalles"
    for div in soup.find_all("div"):
        texto = div.get_text(strip=True)
        if any(palabra in texto.lower() for palabra in ["descripción", "detalles", "acerca de esta propiedad"]):
            # Intentar obtener el siguiente div
            if siguiente := div.find_next_sibling("div"):
                descripcion = siguiente.get_text(strip=True)
                break
            # Si no hay siguiente, buscar dentro del div padre
            elif div.parent:
                for child in div.parent.find_all("div", recursive=False):
                    if child != div and child.get_text(strip=True):
                        descripcion = child.get_text(strip=True)
                        break
    
    # Método 2: Expandir "Ver más" y buscar nuevamente
    if not descripcion or len(descripcion) < 50:
        try:
            # Intentar múltiples selectores para "Ver más"
            for selector in ["text=Ver más", '[role="button"]']:
                ver_mas = page.locator(selector).first
                if ver_mas and ver_mas.is_visible():
                    ver_mas.click()
                    page.wait_for_timeout(1000)
                    html = page.content()
                    soup_actualizado = BeautifulSoup(html, "html.parser")
                    
                    # Buscar descripción en el HTML actualizado
                    for div in soup_actualizado.find_all("div"):
                        texto = div.get_text(strip=True)
                        if any(palabra in texto.lower() for palabra in ["descripción", "detalles", "acerca de"]):
                            if siguiente := div.find_next_sibling("div"):
                                descripcion = siguiente.get_text(strip=True)
                                break
        except:
            pass
    
    # Método 3: Buscar en meta tags si aún no hay descripción
    if not descripcion:
        for meta in soup.find_all("meta", {"property": ["og:description", "description"]}):
            if contenido := meta.get("content", "").strip():
                descripcion = contenido
                break
    
    # Método 4: Buscar en elementos con roles específicos
    if not descripcion:
        for div in soup.find_all(["div", "span"], {"role": ["article", "contentinfo"]}):
            texto = div.get_text(strip=True)
            if len(texto) > 50:  # Asumimos que una descripción válida tiene al menos 50 caracteres
                descripcion = texto
                break
    
    # Método 5: Buscar en el contenido principal
    if not descripcion:
        main_content = soup.find("main") or soup.find(id=lambda x: x and "content" in x.lower())
        if main_content:
            # Filtrar divs que parezcan descripciones
            for div in main_content.find_all("div"):
                texto = div.get_text(strip=True)
                if len(texto) > 50 and not texto.startswith("$"):
                    descripcion = texto
                    break
    
    # Limpiar y normalizar
    if descripcion:
        # Eliminar textos comunes que no son parte de la descripción
        textos_a_eliminar = [
            "ver menos",
            "ver más",
            "marketplace",
            "facebook",
            "comprar y vender",
            "artículos nuevos y usados"
        ]
        descripcion_lower = descripcion.lower()
        for texto in textos_a_eliminar:
            if texto in descripcion_lower:
                descripcion = descripcion.replace(texto, "")
                descripcion = descripcion.replace(texto.capitalize(), "")
        
        # Normalizar espacios y puntuación
        descripcion = re.sub(r'\s+', ' ', descripcion)
        descripcion = descripcion.strip()
        
        # Asegurar que la descripción termine con punto
        if descripcion and not descripcion[-1] in ['.', '!', '?']:
            descripcion += '.'
    
    return descripcion

def extraer_ubicacion_mejorada(soup, page):
    """Extrae información detallada de ubicación"""
    ubicacion = {
        "ciudad": "",
        "colonia": "",
        "referencias": [],
        "coordenadas": {
            "latitud": None,
            "longitud": None
        }
    }
    
    # Método 1: Buscar en elementos específicos
    for div in soup.find_all("div"):
        if "ubicación" in div.get_text(strip=True).lower():
            if siguiente := div.find_next_sibling():
                ubicacion["referencias"].append(siguiente.get_text(strip=True))
    
    # Método 2: Buscar coordenadas en el HTML
    try:
        coords = page.evaluate("""() => {
            const elements = document.getElementsByTagName('a');
            for (const el of elements) {
                const href = el.href || '';
                if (href.includes('maps.google.com')) {
                    const match = href.match(/@(-?\d+\.\d+),(-?\d+\.\d+)/);
                    if (match) return {lat: match[1], lng: match[2]};
                }
            }
            return null;
        }""")
        if coords:
            ubicacion["coordenadas"]["latitud"] = float(coords["lat"])
            ubicacion["coordenadas"]["longitud"] = float(coords["lng"])
    except:
        pass
    
    # Método 3: Buscar colonia en el texto
    texto = soup.get_text(" ", strip=True).lower()
    patrones_colonia = [
        r"col(?:onia)?\.?\s+([^,\.]+)",
        r"fracc?\.?\s+([^,\.]+)",
        r"unidad\s+([^,\.]+)",
        r"residencial\s+([^,\.]+)"
    ]
    
    for patron in patrones_colonia:
        if match := re.search(patron, texto, re.I):
            ubicacion["colonia"] = match.group(1).strip().title()
            break
    
    return ubicacion

def extraer_caracteristicas_mejoradas(soup):
    """Extrae características detalladas de la propiedad"""
    texto = soup.get_text(" ", strip=True).lower()
    
    caracteristicas = {
        "tipo_propiedad": "otro",
        "tipo_operacion": "desconocido",
        "recamaras": None,
        "banos": None,
        "estacionamiento": None,
        "metros_terreno": None,
        "metros_construccion": None,
        "niveles": None,
        "antiguedad": None,
        "estado_conservacion": "No especificado",
        "amenidades": [],
        "servicios": []
    }
    
    # Extraer números con patrones específicos mejorados
    patrones = {
        "recamaras": [
            r"(\d+)\s*(?:rec[áa]maras?|habitaciones?|dormitorios?|cuartos?|alcobas?)",
            r"(?:rec[áa]maras?|habitaciones?|dormitorios?)\s*:\s*(\d+)",
            r"(?:con|tiene)\s*(\d+)\s*(?:rec[áa]maras?|habitaciones?)"
        ],
        "banos": [
            r"(\d+)\s*(?:ba[ñn]os?|medios?\s*ba[ñn]os?)",
            r"(?:ba[ñn]os?)\s*:\s*(\d+)",
            r"(?:con|tiene)\s*(\d+)\s*(?:ba[ñn]os?)"
        ],
        "estacionamiento": [
            r"(\d+)\s*(?:cajones?|lugares?)\s*(?:de)?\s*estacionamiento",
            r"estacionamiento\s*(?:para|:)?\s*(\d+)\s*(?:autos?|coches?|carros?)",
            r"(\d+)\s*(?:autos?|coches?|carros?)\s*(?:en)?\s*(?:cochera|garage)"
        ],
        "metros_terreno": [
            r"(?:terreno|superficie)\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts|metros?)",
            r"(\d+)\s*(?:m2|mts|metros?)\s*(?:de)?\s*terreno",
            r"terreno\s*(?:de|con|:)?\s*(\d+)\s*(?:m2|mts|metros?)"
        ],
        "metros_construccion": [
            r"(?:construcci[óo]n|construidos?)\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts|metros?)",
            r"(\d+)\s*(?:m2|mts|metros?)\s*(?:de)?\s*construcci[óo]n",
            r"[áa]rea\s*construida\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts|metros?)"
        ],
        "niveles": [
            r"(\d+)\s*(?:pisos?|niveles?|plantas?)",
            r"(?:pisos?|niveles?|plantas?)\s*:\s*(\d+)",
            r"(?:casa|propiedad)\s*(?:de)?\s*(\d+)\s*(?:pisos?|niveles?)"
        ]
    }
    
    # Probar cada patrón para cada característica
    for campo, lista_patrones in patrones.items():
        for patron in lista_patrones:
            if valor := extraer_numero(texto, patron):
                caracteristicas[campo] = valor
                break
    
    # Detectar tipo de propiedad con más variantes
    tipos_propiedad = {
        "casa": [
            "casa sola", "casa", "casa en", "casa habitación", "residencia",
            "casa unifamiliar", "chalet", "villa", "casa independiente"
        ],
        "departamento": [
            "departamento", "depto", "departamentos", "depa", "flat",
            "apartamento", "apto", "pent house", "penthouse"
        ],
        "terreno": [
            "terreno", "lote", "terrenos", "predio", "parcela",
            "solar", "tierra", "hectáreas", "m2 de terreno"
        ],
        "local": [
            "local", "locales", "local comercial", "plaza comercial",
            "negocio", "comercio", "establecimiento"
        ],
        "oficina": [
            "oficina", "oficinas", "despacho", "consultorio",
            "espacio de trabajo", "espacio comercial"
        ],
        "bodega": [
            "bodega", "bodegas", "almacén", "nave industrial",
            "galpón", "storage", "almacenamiento"
        ],
        "condominio": [
            "condominio", "condominios", "conjunto", "unidad habitacional",
            "desarrollo", "fraccionamiento", "cluster"
        ]
    }
    
    # Detectar tipo de propiedad
    for tipo, palabras in tipos_propiedad.items():
        if any(palabra in texto for palabra in palabras):
            caracteristicas["tipo_propiedad"] = tipo
            break
    
    # Detectar tipo de operación con más variantes
    palabras_renta = [
        "renta", "alquiler", "/mes", "mensual", "arrendamiento",
        "rentar", "alquilar", "precio por mes", "mensualidad"
    ]
    palabras_venta = [
        "venta", "vendo", "remato", "oportunidad", "precio de venta",
        "se vende", "en venta", "venta directa", "precio final"
    ]
    
    if any(palabra in texto for palabra in palabras_renta):
        caracteristicas["tipo_operacion"] = "renta"
    elif any(palabra in texto for palabra in palabras_venta):
        caracteristicas["tipo_operacion"] = "venta"
    
    # Detectar amenidades con más variantes
    amenidades_buscar = {
        "Alberca": ["alberca", "piscina", "pool", "chapoteadero"],
        "Jardín": ["jardín", "jardin", "área verde", "green area", "jardinado"],
        "Seguridad": ["vigilancia", "seguridad", "privada", "caseta", "guardia"],
        "Gimnasio": ["gimnasio", "gym", "área de ejercicio", "fitness center"],
        "Área común": ["área común", "area comun", "areas comunes", "espacios compartidos"],
        "Juegos infantiles": ["juegos infantiles", "área de juegos", "playground", "parque infantil"],
        "Roof garden": ["roof garden", "terraza", "rooftop", "sky garden"],
        "Elevador": ["elevador", "ascensor", "lift"],
        "Sala de juntas": ["sala de juntas", "business center", "sala de reuniones"],
        "Estacionamiento techado": ["estacionamiento techado", "cochera techada", "garage cerrado"]
    }
    
    # Detectar servicios con más variantes
    servicios_buscar = {
        "Agua": ["agua", "hidráulica", "agua potable", "cisterna"],
        "Luz": ["luz", "electricidad", "energía eléctrica", "instalación eléctrica"],
        "Gas": ["gas natural", "gas estacionario", "instalación de gas"],
        "Internet": ["internet", "wifi", "fibra óptica", "banda ancha"],
        "Mantenimiento": ["mantenimiento", "vigilancia", "cuota de mantenimiento"],
        "Aires acondicionados": ["aire acondicionado", "minisplit", "clima", "climatización"],
        "Calefacción": ["calefacción", "caldera", "sistema de calefacción"],
        "Sistema contra incendios": ["sistema contra incendios", "detectores de humo", "aspersores"]
    }
    
    # Detectar amenidades y servicios
    for amenidad, palabras in amenidades_buscar.items():
        if any(palabra in texto for palabra in palabras):
            caracteristicas["amenidades"].append(amenidad)
    
    for servicio, palabras in servicios_buscar.items():
        if any(palabra in texto for palabra in palabras):
            caracteristicas["servicios"].append(servicio)
    
    # Detectar estado de conservación
    estados = {
        "Nuevo": ["nuevo", "a estrenar", "recién construido"],
        "Excelente": ["excelente estado", "remodelado", "como nuevo"],
        "Bueno": ["buen estado", "conservado", "mantenido"],
        "Regular": ["regular", "necesita mantenimiento", "para renovar"],
        "Malo": ["mal estado", "para remodelar", "fixer upper"]
    }
    
    for estado, palabras in estados.items():
        if any(palabra in texto for palabra in palabras):
            caracteristicas["estado_conservacion"] = estado
            break
    
    # Detectar antigüedad
    patrones_antiguedad = [
        r"(\d+)\s*(?:años?)\s*(?:de)?\s*(?:antiguedad|construcción)",
        r"construi(?:do|da)\s*(?:hace|en)?\s*(\d+)\s*años?",
        r"(?:del|año)\s*(\d{4})"  # Para años específicos
    ]
    
    for patron in patrones_antiguedad:
        if match := re.search(patron, texto):
            try:
                valor = int(match.group(1))
                if valor > 1900:  # Es un año específico
                    caracteristicas["antiguedad"] = datetime.now().year - valor
                else:
                    caracteristicas["antiguedad"] = valor
                break
            except:
                pass
    
    return caracteristicas

def extraer_estado_legal(soup):
    """Extrae información legal de la propiedad"""
    texto = soup.get_text(" ", strip=True).lower()
    
    return {
        "escrituras": "escrituras" in texto or "escriturada" in texto,
        "cesion_derechos": any(x in texto for x in ["cesión", "cesion de derechos"]),
        "creditos": any(x in texto for x in ["crédito", "credito", "infonavit", "fovissste"]),
        "predial": "predial" in texto,
        "agua": "agua" in texto,
        "estado": "disponible",
        "documentacion": []
    }

def extraer_datos_vendedor(soup, page):
    """Extrae información detallada del vendedor"""
    vendedor = {
        "nombre": "",
        "tipo": "particular",  # o "inmobiliaria"
        "perfil": "",
        "telefono": "",
        "whatsapp": "",
        "correo": "",
        "otros_anuncios": []
    }
    
    try:
        # Método 1: Buscar en enlaces
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "facebook.com/profile.php?id=" in href or re.match(r"facebook\.com/[^/]+$", href):
                vendedor["perfil"] = href
                if strong := a.find("strong"):
                    vendedor["nombre"] = strong.get_text(strip=True)
                vendedor["tipo"] = "inmobiliaria" if not "profile.php?id=" in href else "particular"
                break
        
        # Método 2: Usar JavaScript para datos adicionales
        datos_js = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a'));
            for (const link of links) {
                if (link.href.includes('/marketplace/seller/')) {
                    return {
                        otros_anuncios: link.href,
                        nombre: link.textContent.trim()
                    }
                }
            }
            return null;
        }""")
        
        if datos_js:
            if datos_js.get("nombre"):
                vendedor["nombre"] = datos_js["nombre"]
            if datos_js.get("otros_anuncios"):
                vendedor["otros_anuncios"].append(datos_js["otros_anuncios"])
                
    except Exception as e:
        logging.warning(f"Error extrayendo datos del vendedor: {str(e)}")
    
    return vendedor

def detectar_estado_publicacion(soup, page):
    """Detecta si una publicación está disponible, vendida o eliminada"""
    estado = {
        "disponible": True,
        "motivo": None,
        "fecha_cambio": None
    }
    
    # Verificar texto en la página
    texto = soup.get_text(" ", strip=True).lower()
    
    # Patrones de no disponibilidad
    patrones_no_disponible = [
        "esta publicación ya no está disponible",
        "este artículo ya se vendió",
        "ya no está disponible",
        "ya no está a la venta",
        "vendido",
        "rentado",
        "apartado",
        "eliminado",
        "no disponible",
        "lo sentimos, este contenido ya no está disponible"
    ]
    
    # Verificar patrones en el texto
    for patron in patrones_no_disponible:
        if patron in texto:
            estado["disponible"] = False
            estado["motivo"] = "Publicación no disponible"
            estado["fecha_cambio"] = datetime.now().isoformat()
            return estado
    
    # Verificar elementos específicos de Facebook
    try:
        # Buscar mensaje de error específico
        error_msg = page.locator('text="Este contenido no está disponible en este momento"').is_visible()
        if error_msg:
            estado["disponible"] = False
            estado["motivo"] = "Contenido no disponible"
            estado["fecha_cambio"] = datetime.now().isoformat()
            return estado
        
        # Verificar redirección a página principal
        if page.url == "https://www.facebook.com/marketplace/":
            estado["disponible"] = False
            estado["motivo"] = "Redirección a página principal"
            estado["fecha_cambio"] = datetime.now().isoformat()
            return estado
    except:
        pass
    
    return estado

def procesar_propiedad(page, link, id_propiedad, ciudad, fecha_str):
    """Procesa una propiedad y retorna sus datos"""
    logging.info(f"\nProcesando {id_propiedad} - {link}")
    t0 = time.time()
    
    try:
        # Configurar timeouts más agresivos
        page.set_default_timeout(15000)  # 15 segundos máximo para cualquier operación
        
        # Navegar y esperar solo los elementos críticos
        page.goto(link, wait_until='domcontentloaded')  # Más rápido que 'networkidle'
        
        # Esperar solo elementos críticos con timeout reducido
        try:
            page.wait_for_selector('h1', timeout=5000)  # 5 segundos para el título
        except:
            pass  # Continuar incluso si no encuentra el título
        
        # Obtener HTML inmediatamente
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Verificar si la publicación está disponible
        if any(texto in html.lower() for texto in [
            "esta publicación no está disponible",
            "this listing is no longer available",
            "this item is not available",
            "lo sentimos, este artículo no está disponible"
        ]):
            logging.info(f"Propiedad no disponible: {id_propiedad}")
            return {
                "id": id_propiedad,
                "link": link,
                "metadata": {
                    "status": "no_disponible",
                    "fecha_verificacion": datetime.now().isoformat()
                }
            }
        
        # Extraer datos básicos rápidamente
        titulo = ""
        if h1 := soup.find("h1"):
            titulo = normalizar_texto(h1.get_text(strip=True))
        
        # Extraer precio de manera eficiente
        precio = extraer_precio_mejorado(soup)
        
        # Extraer descripción sin esperas innecesarias
        descripcion = extraer_descripcion_mejorada(soup, page)
        
        # Si no hay datos críticos, marcar como error
        if not titulo and not descripcion:
            logging.error(f"Datos críticos faltantes para {id_propiedad}")
            return None
        
        # Crear directorios necesarios
        carpeta = os.path.join(CARPETA_RESULTADOS, fecha_str)
        os.makedirs(carpeta, exist_ok=True)
        
        # Extraer el resto de datos sin esperas adicionales
        caracteristicas = extraer_caracteristicas_mejoradas(soup)
        ubicacion = extraer_ubicacion_mejorada(soup, page)
        estado_legal = extraer_estado_legal(soup)
        vendedor = extraer_datos_vendedor(soup, page)
        
        # Construir objeto de datos
        datos = {
            "id": id_propiedad,
            "link": link,
            "titulo": titulo,
            "descripcion": descripcion,
            "precio": precio,
            "ubicacion": ubicacion,
            "caracteristicas": caracteristicas,
            "estado_legal": estado_legal,
            "vendedor": vendedor,
            "metadata": {
                "fecha_extraccion": datetime.now().isoformat(),
                "ultima_actualizacion": datetime.now().isoformat(),
                "fuente": "facebook_marketplace",
                "status": "completo",
                "tiempo_procesamiento": time.time() - t0
            }
        }
        
        # Guardar HTML y JSON rápidamente
        base = f"{ciudad}-{fecha_str}-{id_propiedad}"
        ruta_html = os.path.join(carpeta, base + ".html")
        ruta_json = os.path.join(carpeta, base + ".json")
        
        with open(ruta_html, "w", encoding="utf-8") as f:
            f.write(html)
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        
        tiempo_total = time.time() - t0
        logging.info(f"✓ Datos extraídos en {tiempo_total:.1f}s")
        return datos
        
    except PlaywrightTimeout:
        logging.error(f"❌ Timeout al cargar {id_propiedad}")
        return None
    except Exception as e:
        logging.error(f"❌ Error procesando {id_propiedad}: {str(e)}")
        return None

def signal_handler(signum, frame):
    """Manejador de señales para interrupciones"""
    global INTERRUPT_RECEIVED
    if not INTERRUPT_RECEIVED:
        logging.info("\n⚠️ Señal de interrupción recibida. Guardando progreso...")
        INTERRUPT_RECEIVED = True
    else:
        logging.info("\n⚠️ Segunda interrupción recibida. Saliendo inmediatamente...")
        sys.exit(1)

def extraer_precio_mejorado(soup):
    """Extrae y normaliza el precio"""
    precio = {
        "valor": 0,
        "valor_normalizado": 0.0,
        "moneda": "MXN",
        "es_valido": False,
        "error": None
    }
    
    # Buscar precio en el texto
    for span in soup.find_all("span"):
        texto = span.get_text(strip=True)
        if texto.startswith("$") and len(texto) < 30:
            try:
                # Limpiar y convertir
                valor = texto.replace("$", "").replace(",", "").replace(" ", "")
                precio["valor"] = float(valor)
                precio["valor_normalizado"] = precio["valor"]
                precio["es_valido"] = True
                return precio
            except ValueError as e:
                precio["error"] = str(e)
                
    return precio

def main():
    """Función principal con manejo de interrupciones"""
    # Registrar manejador de señales
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 1) Maestro previo
    data_master = {}
    if os.path.exists(CARPETA_REPO_MASTER):
        with open(CARPETA_REPO_MASTER, "r", encoding="utf-8") as f:
            data_master = json.load(f)
    existing_ids = set(data_master.keys())
    logging.info(f"Repositorio maestro cargado con {len(data_master)} propiedades")

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
    pending = [l for l in links if l["id"] not in existing_ids][:5]  # Limitar a 5 propiedades
    
    # Estadísticas iniciales
    total = len(links)
    falta = len(pending)
    no_disponibles = sum(1 for pid in existing_ids if data_master[pid].get("metadata", {}).get("status") == "no_disponible")
    ya_procesadas = len(existing_ids) - no_disponibles
    
    logging.info(f"\nTotal de propiedades en repositorio: {total}")
    logging.info(f"Procesando solo: {falta} propiedades")
    logging.info(f"No disponibles: {no_disponibles}")
    logging.info(f"Ya procesadas: {ya_procesadas}")

    # 4) Carpeta diaria
    date_str = datetime.now().strftime("%Y-%m-%d")
    carpeta = os.path.join(CARPETA_RESULTADOS, date_str)
    os.makedirs(carpeta, exist_ok=True)

    # 5) Lanzar navegador y barra de progreso
    pbar = ProgressBar(falta, desc="Extrayendo propiedades", unit="propiedad")
    ok = err = 0
    
    try:
        with sync_playwright() as p:
            # Configurar navegador para máxima velocidad
            browser = p.chromium.launch(
                headless=False,
                args=['--disable-gpu', '--no-sandbox', '--disable-dev-shm-usage']
            )
            context = browser.new_context(
                storage_state=ESTADO_FB if os.path.exists(ESTADO_FB) else None,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            
            # Configurar página para máxima velocidad
            page = context.new_page()
            page.set_default_timeout(15000)  # 15 segundos máximo global
            
            # Deshabilitar recursos no necesarios
            page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf}", lambda route: route.abort())

            for item in pending:
                if INTERRUPT_RECEIVED:
                    logging.info("Interrupción detectada, guardando progreso...")
                    break
                    
                pid = item["id"]
                url = item["link"]
                ciudad = item["ciudad"]
                t0 = time.time()
                
                try:
                    # Extraer datos
                    datos = procesar_propiedad(page, url, pid, ciudad, date_str)
                    
                    if datos:
                        # Actualizar repositorio maestro
                        data_master[pid] = datos
                        ok += 1
                    else:
                        err += 1
                        
                except Exception as e:
                    err += 1
                    logging.error(f"❌ Error en {pid}: {str(e)}")
                finally:
                    pbar.update(1, ok=ok, err=err, last_time=time.time()-t0)
                    
                    # Guardar progreso cada 2 propiedades
                    if (ok + err) % 2 == 0:
                        with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as f:
                            json.dump(data_master, f, ensure_ascii=False, indent=2)
                        logging.info("Progreso guardado")

            pbar.close()
            page.close()
            browser.close()

    except Exception as e:
        logging.error(f"Error general: {str(e)}")
    finally:
        # Guardar progreso final
        with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as f:
            json.dump(data_master, f, ensure_ascii=False, indent=2)
        
        # Resumen final
        total_final = len(data_master)
        no_disponibles_final = sum(1 for pid in data_master if data_master[pid].get("metadata", {}).get("status") == "no_disponible")
        procesadas_final = total_final - no_disponibles_final
        
        logging.info("\n=== RESUMEN FINAL ===")
        logging.info(f"Total de propiedades en el repositorio: {total_final}")
        logging.info(f"Procesadas exitosamente: {procesadas_final}")
        logging.info(f"No disponibles: {no_disponibles_final}")
        logging.info(f"Con errores: {err}")
        logging.info(f"Porcentaje de éxito: {(ok/falta*100 if falta else 0):.1f}%")

if __name__ == "__main__":
    main() 