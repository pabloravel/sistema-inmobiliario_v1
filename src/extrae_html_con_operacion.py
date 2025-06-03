#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion.py

Versión mejorada de extracción de Facebook Marketplace,
con mejoras en la detección de tipo de operación, ubicación
y características de las propiedades.
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
CARPETA_LINKS_VENTA = "resultados/links/ventas/repositorio_unico_ventas.json"
CARPETA_LINKS_RENTA = "resultados/links/rentas/repositorio_unico_rentas.json"
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

def procesar_numero_mexicano(numero):
    """
    Procesa un número en formato mexicano con manejo especial de separadores.
    Retorna el valor numérico o None si no se puede procesar.
    """
    try:
        # Limpiar el texto
        numero = str(numero).replace(' ', '').replace('$', '').strip()
        
        # Si no hay números, retornar None
        if not any(c.isdigit() for c in numero):
            return None
            
        # Remover sufijos comunes
        numero = numero.rstrip('.')  # Quitar punto final si existe
        numero = numero.replace('.000', '').replace(',000', '')
        
        # Detectar si es un formato con millones
        if 'millones' in numero.lower() or 'mdp' in numero.lower():
            base = re.search(r'(\d+(?:[.,]\d+)?)', numero)
            if base:
                valor_base = base.group(1).replace(',', '.')
                return float(valor_base) * 1_000_000
        
        # Detectar formato con punto como separador de miles (2.524.000)
        if numero.count('.') > 1:
            numero = numero.replace('.', '')
        
        # Detectar formato con coma como separador de miles (2,524,000)
        if numero.count(',') > 1:
            numero = numero.replace(',', '')
        
        # Si queda una coma, es decimal
        if ',' in numero:
            numero = numero.replace(',', '.')
            
        # Convertir a float y luego a int si es posible
        valor = float(numero)
        
        # Validar rangos lógicos
        if valor < 100:  # Probablemente es un error
            return None
            
        if valor < 1000:  # Probablemente es en miles
            valor *= 1000
            
        return int(valor) if valor.is_integer() else valor
        
    except Exception as e:
        return None

def validar_precio(valor, tipo_operacion=None):
    """
    Valida que el precio esté en un rango razonable según el tipo de operación.
    Retorna (es_valido, confianza, mensaje_error).
    """
    if not valor or valor <= 0:
        return False, 0.0, "Precio inválido o cero"
    
    if valor > 100_000_000:
        return False, 0.0, "Precio excede el límite máximo de 100 millones"
    
    confianza = 0.8  # Confianza base
    mensaje = None
    
    # Rangos por tipo de operación
    rangos = {
        "Venta": {
            "min": 100_000,
            "max": 50_000_000,
            "optimo_min": 500_000,
            "optimo_max": 20_000_000
        },
        "Renta": {
            "min": 1_000,
            "max": 100_000,
            "optimo_min": 3_000,
            "optimo_max": 50_000
        }
    }
    
    if tipo_operacion in rangos:
        rango = rangos[tipo_operacion]
        
        # Verificar límites estrictos
        if valor < rango["min"]:
            return False, 0.0, f"Precio muy bajo para {tipo_operacion}"
        if valor > rango["max"]:
            return False, 0.0, f"Precio muy alto para {tipo_operacion}"
        
        # Ajustar confianza según el rango óptimo
        if rango["optimo_min"] <= valor <= rango["optimo_max"]:
            confianza = 0.9
        else:
            confianza = 0.7
            mensaje = "Precio fuera del rango óptimo"
    
    # Ajustar confianza por números redondos
    if valor % 1_000_000 == 0:
        confianza *= 0.95  # Menos confianza en números muy redondos
        if not mensaje:
            mensaje = "Precio en millones exactos"
    elif valor % 100_000 == 0:
        confianza *= 0.98
        if not mensaje:
            mensaje = "Precio en cientos de miles exactos"
    elif valor % 1_000 == 0:
        confianza *= 0.99
        if not mensaje:
            mensaje = "Precio en miles exactos"
    
    # Ajustar confianza por magnitud del precio
    if valor >= 10_000_000:
        confianza *= 0.95  # Menor confianza en precios muy altos
        if not mensaje:
            mensaje = "Precio muy alto"
    elif valor <= 200_000:
        confianza *= 0.95  # Menor confianza en precios muy bajos
        if not mensaje:
            mensaje = "Precio muy bajo"
    
    return True, confianza, mensaje

def extraer_precio_mejorado(soup):
    """
    Extrae y normaliza el precio, devolviendo un diccionario con el formato requerido:
    {
        "texto": "$8.500/mes",
        "valor": 8500,
        "es_valido": true,
        "confianza": 0.9,
        "mensaje": null
    }
    """
    precio = {
        "texto": "",
        "valor": None,
        "es_valido": False,
        "confianza": 0.0,
        "mensaje": "No se encontró precio"
    }
    
    # Buscar precio en spans (más preciso)
    for span in soup.find_all("span"):
        texto = span.get_text(strip=True)
        if texto.startswith("$") and len(texto) < 30:
            precio["texto"] = texto
            try:
                # Procesar el número
                valor_num = procesar_numero_mexicano(texto)
                if valor_num:
                    # Validar el precio
                    es_valido, confianza, mensaje = validar_precio(valor_num)
                    precio["valor"] = valor_num
                    precio["es_valido"] = es_valido
                    precio["confianza"] = confianza
                    precio["mensaje"] = mensaje
                    return precio
            except Exception as e:
                precio["mensaje"] = f"Error al procesar precio: {str(e)}"
                
    # Si no se encontró en spans, buscar en el texto completo
    texto_completo = soup.get_text(" ", strip=True).lower()
    patrones_precio = [
        r'\$\s*[\d,.]+\s*(?:millones?)?(?:/mes)?',
        r'precio:?\s*\$?\s*[\d,.]+(?:/mes)?',
        r'[\d,.]+\s*(?:millones?)?(?:\s*de\s*pesos)?(?:/mes)?'
    ]
    
    for patron in patrones_precio:
        if match := re.search(patron, texto_completo):
            texto_precio = match.group(0).strip()
            precio["texto"] = texto_precio
            try:
                valor = procesar_numero_mexicano(texto_precio)
                if valor:
                    es_valido, confianza, mensaje = validar_precio(valor)
                    precio["valor"] = valor
                    precio["es_valido"] = es_valido
                    precio["confianza"] = confianza
                    precio["mensaje"] = mensaje
                    return precio
            except:
                continue
    
    return precio

def extraer_vendedor(soup):
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "facebook.com/profile.php?id=" in href:
            link_v   = href.split("?")[0]
            strong   = a.find("strong")
            vendedor = strong.get_text(strip=True) if strong else ""
            return vendedor, link_v
    return "", ""

def guardar_archivos(html, datos, ciudad, pid, carpeta, date_str):
    """
    Guarda los archivos HTML, JSON y la imagen en la carpeta diaria
    """
    base = f"{ciudad}-{date_str}-{pid}"
    ruta_html = os.path.join(carpeta, base + ".html")
    ruta_json = os.path.join(carpeta, base + ".json")
    
    # Guardar HTML para depuración
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)
    
    # Guardar JSON con los datos
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    
    return ruta_html, ruta_json

def descargar_imagen_por_playwright(page, ciudad, pid, carpeta, date_str):
    """
    Descarga la imagen principal de la propiedad
    """
    try:
        src = page.locator('img[alt^="Foto de"]').first.get_attribute('src')
    except:
        try:
            src = page.locator('img').first.get_attribute('src')
        except:
            return {
                "nombre_archivo": "",
                "ruta_absoluta": "",
                "ruta_relativa": ""
            }
            
    if not src or not src.startswith("http"):
        return {
            "nombre_archivo": "",
            "ruta_absoluta": "",
            "ruta_relativa": ""
        }
        
    filename = f"{ciudad}-{date_str}-{pid}.jpg"
    path_img = os.path.join(carpeta, filename)
    
    try:
        resp = requests.get(src, timeout=10)
        if resp.status_code == 200:
            with open(path_img, "wb") as f:
                f.write(resp.content)
            
            # Construir rutas para fácil acceso
            ruta_absoluta = os.path.abspath(path_img)
            # Construir ruta relativa desde la raíz del proyecto
            ruta_relativa = os.path.relpath(path_img, CARPETA_RESULTADOS).replace("\\", "/")
            
            return {
                "nombre_archivo": filename,
                "ruta_absoluta": ruta_absoluta,
                "ruta_relativa": ruta_relativa
            }
    except:
        pass
    
    return {
        "nombre_archivo": "",
        "ruta_absoluta": "",
        "ruta_relativa": ""
    }

def extraer_ubicacion_desde_dom(soup):
    """
    Extrae la ubicación desde el DOM, buscando en múltiples lugares y formatos
    """
    ubicacion = {
        "direccion_completa": "",
        "ciudad": "",
        "estado": "",
        "texto_original": ""
    }
    
    ciudades_conocidas = ["cuernavaca", "jiutepec", "temixco", "zapata", "yautepec", "tres de mayo", "burgos"]
    
    try:
        # Método 1: Buscar en elementos con atributos específicos de ubicación
        for elemento in soup.find_all(['span', 'div', 'a']):
            if elemento.get('aria-label') and 'ubicación' in elemento.get('aria-label').lower():
                texto = elemento.get_text(strip=True)
                if texto and any(ciudad in texto.lower() for ciudad in ciudades_conocidas):
                    ubicacion["texto_original"] = texto
                    ubicacion["direccion_completa"] = texto
                    break

        # Método 2: Buscar en la estructura de metadatos
        meta_location = soup.find('meta', {'property': 'og:locality'}) or soup.find('meta', {'property': 'place:location:locality'})
        if meta_location and meta_location.get('content'):
            texto = meta_location.get('content')
            if any(ciudad in texto.lower() for ciudad in ciudades_conocidas):
                ubicacion["texto_original"] = texto
                ubicacion["direccion_completa"] = texto

        # Método 3: Buscar en elementos cercanos al precio
        precio_elemento = None
        for elemento in soup.find_all(['span', 'div']):
            if elemento.get_text(strip=True).startswith('$'):
                precio_elemento = elemento
                break
        
        if precio_elemento:
            # Buscar en los siguientes 3 elementos hermanos
            siguiente = precio_elemento.find_next_sibling()
            for _ in range(3):
                if siguiente:
                    texto = siguiente.get_text(strip=True)
                    if texto and any(ciudad in texto.lower() for ciudad in ciudades_conocidas):
                        ubicacion["texto_original"] = texto
                        ubicacion["direccion_completa"] = texto
                        break
                    siguiente = siguiente.find_next_sibling()

        # Método 4: Buscar en cualquier texto que contenga las ciudades conocidas
        if not ubicacion["direccion_completa"]:
            for elemento in soup.find_all(['span', 'div'], class_=True):
                texto = elemento.get_text(strip=True)
                if len(texto) < 100 and any(ciudad in texto.lower() for ciudad in ciudades_conocidas):
                    if not any(palabra in texto.lower() for palabra in ["descripción", "ver menos", "inbox", "info"]):
                        ubicacion["texto_original"] = texto
                        ubicacion["direccion_completa"] = texto
                        break

        # Procesar la ubicación encontrada
        if ubicacion["direccion_completa"]:
            texto = ubicacion["direccion_completa"].lower()
            
            # Extraer ciudad
            for ciudad in ciudades_conocidas:
                if ciudad in texto:
                    if ciudad == "zapata" and "emiliano zapata" in texto:
                        ubicacion["ciudad"] = "Emiliano Zapata"
                    elif ciudad == "tres de mayo":
                        ubicacion["ciudad"] = "Tres de Mayo"
                    else:
                        ubicacion["ciudad"] = ciudad.title()
                    break
            
            # Extraer estado
            if any(estado in texto for estado in ["mor", "mor.", "morelos"]):
                ubicacion["estado"] = "Morelos"

    except Exception as e:
        print(f"Error al extraer ubicación: {str(e)}")
    
    return ubicacion

def guardar_datos_propiedad(datos, ruta_base):
    """
    Guarda los datos de la propiedad en formato JSON
    """
    ruta_json = os.path.join(ruta_base, "data.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def detectar_tipo_operacion(texto, descripcion=None, precio_str=None, precio_num=None):
    """
    Detecta el tipo de operación (Venta/Renta) basado en el texto y el precio.
    """
    texto = texto.lower() if texto else ""
    descripcion = descripcion.lower() if descripcion else ""
    texto_completo = f"{texto} {descripcion}"
    
    # Palabras clave ampliadas
    renta_keywords = [
        'renta', 'alquiler', '/mes', 'mensual', 'rentar',
        'arrendamiento', 'arriendo', 'mensualidad', 'rento',
        'se renta', 'en renta', 'para rentar', 'rentamos'
    ]
    venta_keywords = [
        'venta', 'se vende', 'remato', 'vendo', 'oportunidad de compra',
        'precio de venta', 'vende', 'vendemos', 'en venta',
        'para vender', 'precio de contado', 'oferta de venta'
    ]
    
    # Verificar por palabras clave
    if any(k in texto_completo for k in renta_keywords):
        return "Renta"
    if any(k in texto_completo for k in venta_keywords):
        return "Venta"
        
    # Análisis por precio si está disponible
    if precio_num and precio_num > 0:
        if precio_num < 100_000:
            return "Renta"
        if precio_num > 500_000:
            return "Venta"
    
    return "Desconocido"

def extraer_caracteristicas(texto):
    """
    Extrae características detalladas de la propiedad.
    """
    caracteristicas = {
        "recamaras": None,
        "banos": None,
        "medio_bano": None,
        "niveles": None,
        "estacionamientos": None,
        "superficie_m2": None,
        "construccion_m2": None,
        "edad": None,
        "recamara_planta_baja": False,
        "cisterna": False,
        "capacidad_cisterna": None
    }
    
    texto = texto.lower()
    
    # Patrones mejorados para recámaras
    patrones_recamaras = [
        r'(\d+)\s*(?:rec(?:amaras?|ámaras?)?|hab(?:itaciones?)?|dormitorios?|cuartos?|alcobas?)',
        r'(?:rec(?:amaras?|ámaras?)?|hab(?:itaciones?)?|dormitorios?)\s*(?::|con)?\s*(\d+)',
        r'(?:casa|depto|departamento)\s+(?:de|con)\s+(\d+)\s*(?:rec|hab)',
        r'(\d+)\s*(?:habitaciones?|cuartos?)\s+(?:para\s+)?dormir'
    ]
    
    # Patrones para baños
    patrones_banos = [
        r'(\d+(?:\.\d+)?)\s*(?:baños?|banos?|wc|sanitarios?)',
        r'(?:baños?|banos?|wc|sanitarios?)\s*(?:completos?|principales?)?\s*(?::|con)?\s*(\d+(?:\.\d+)?)',
        r'(\d+)\s*(?:baños?|banos?)\s+(?:completos?|principales?)',
        r'medio\s+baño',
        r'baño\s+completo'
    ]
    
    # Patrones para superficie
    patrones_superficie = [
        r'(?:superficie|terreno|lote)\s*(?:de|:)?\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros?|mt2|mts2)',
        r'(\d+(?:\.\d+)?)\s*(?:m²|m2|metros?|mt2|mts2)\s*(?:de\s*terreno|superficie)',
        r'(\d+)\s*x\s*(\d+)\s*(?:m²|m2|metros?)?',
        r'(\d+)\s*por\s*(\d+)\s*(?:m²|m2|metros?)?'
    ]
    
    # Patrones para construcción
    patrones_construccion = [
        r'(?:construccion|construcción)\s*(?:de|:)?\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros?|mt2|mts2)',
        r'(\d+(?:\.\d+)?)\s*(?:m²|m2|metros?|mt2|mts2)\s*(?:de\s*construccion|de\s*construcción)',
        r'area\s*construida\s*(?:de|:)?\s*(\d+(?:\.\d+)?)\s*(?:m²|m2|metros?)'
    ]
    
    # Patrones para estacionamientos
    patrones_estacionamiento = [
        r'(\d+)\s*(?:cajone?s?|lugares?|espacios?)\s*(?:de\s*)?(?:estacionamiento|auto|coche|carro)',
        r'(?:estacionamiento|cochera|garage)\s*(?:para|con|de)\s*(\d+)\s*(?:auto|carro|coche)',
        r'(\d+)\s*(?:autos?|carros?|coches?)\s*(?:en\s*)?(?:cochera|garage|estacionamiento)',
        r'(?:con|incluye)\s*(\d+)\s*(?:lugares?|cajone?s?)\s*(?:de\s*)?estacionamiento'
    ]
    
    # Buscar recámaras
    for patron in patrones_recamaras:
        if match := re.search(patron, texto):
            try:
                caracteristicas["recamaras"] = int(match.group(1))
                break
            except:
                continue
    
    # Buscar baños
    total_banos = 0
    medio_bano = False
    
    for patron in patrones_banos:
        if match := re.search(patron, texto):
            try:
                if 'medio' in match.group(0):
                    medio_bano = True
                else:
                    num = float(match.group(1))
                    if num.is_integer():
                        total_banos = int(num)
                    else:
                        total_banos = int(num)
                        medio_bano = True
                break
            except:
                continue
    
    if total_banos > 0:
        caracteristicas["banos"] = total_banos
    if medio_bano:
        caracteristicas["medio_bano"] = 1
    
    # Buscar superficie
    for patron in patrones_superficie:
        if match := re.search(patron, texto):
            try:
                if 'x' in patron or 'por' in patron:
                    largo = float(match.group(1))
                    ancho = float(match.group(2))
                    caracteristicas["superficie_m2"] = int(largo * ancho)
                else:
                    caracteristicas["superficie_m2"] = int(float(match.group(1)))
                break
            except:
                continue
    
    # Buscar construcción
    for patron in patrones_construccion:
        if match := re.search(patron, texto):
            try:
                caracteristicas["construccion_m2"] = int(float(match.group(1)))
                break
            except:
                continue
    
    # Buscar estacionamientos
    for patron in patrones_estacionamiento:
        if match := re.search(patron, texto):
            try:
                caracteristicas["estacionamientos"] = int(match.group(1))
                break
            except:
                continue
    
    # Detectar recámara en planta baja
    if re.search(r'rec[aá]mara\s+(?:en\s+)?(?:planta\s+)?baja|rec[aá]mara\s+principal\s+abajo', texto):
        caracteristicas["recamara_planta_baja"] = True
    
    # Detectar cisterna
    if 'cisterna' in texto:
        caracteristicas["cisterna"] = True
        # Buscar capacidad de cisterna
        if match := re.search(r'cisterna\s*(?:de|con)?\s*(\d+)\s*(?:m3|litros?|metros?3?)', texto):
            try:
                caracteristicas["capacidad_cisterna"] = int(match.group(1))
            except:
                pass
    
    return caracteristicas

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
            
        return filename
    except Exception as e:
        print(f"Error al extraer DOM para {pid}: {e}")
        return ""

# ── Flujo principal ───────────────────────────────────────────────────
def main():
    # 1) Maestro previo
    data_master = {}
    if os.path.exists(CARPETA_REPO_MASTER):
        with open(CARPETA_REPO_MASTER, "r", encoding="utf-8") as f:
            data_master = json.load(f)

    # 2) Carga y normaliza enlaces de venta y renta
    links = []
    
    # Cargar enlaces de venta
    if os.path.exists(CARPETA_LINKS_VENTA):
        with open(CARPETA_LINKS_VENTA, "r", encoding="utf-8") as f:
            raw_links_venta = json.load(f)
            for item in raw_links_venta:
                if isinstance(item, str):
                    href = BASE_URL + item if item.startswith("/") else item
                    city = "cuernavaca"
                    tipo = "Venta"
                elif isinstance(item, dict):
                    href = item.get("link","")
                    href = BASE_URL + href if href.startswith("/") else href
                    city = item.get("ciudad","cuernavaca").lower()
                    tipo = "Venta"
                else:
                    continue
                pid = href.rstrip("/").split("/")[-1]
                links.append({"link": href, "id": pid, "ciudad": city, "tipo": tipo})

    # Cargar enlaces de renta
    if os.path.exists(CARPETA_LINKS_RENTA):
        with open(CARPETA_LINKS_RENTA, "r", encoding="utf-8") as f:
            raw_links_renta = json.load(f)
            for item in raw_links_renta:
                if isinstance(item, str):
                    href = BASE_URL + item if item.startswith("/") else item
                    city = "cuernavaca"
                    tipo = "Renta"
                elif isinstance(item, dict):
                    href = item.get("link","")
                    href = BASE_URL + href if href.startswith("/") else href
                    city = item.get("ciudad","cuernavaca").lower()
                    tipo = "Renta"
                else:
                    continue
                pid = href.rstrip("/").split("/")[-1]
                links.append({"link": href, "id": pid, "ciudad": city, "tipo": tipo})

    # 3) Filtra pendientes
    pending = [l for l in links if l["id"] not in data_master]

    # ── PRINT RESUMEN ANTES DE EMPEZAR ──
    total = len(links)
    total_venta = len([l for l in links if l["tipo"] == "Venta"])
    total_renta = len([l for l in links if l["tipo"] == "Renta"])
    falta = len(pending)
    falta_venta = len([p for p in pending if p["tipo"] == "Venta"])
    falta_renta = len([p for p in pending if p["tipo"] == "Renta"])
    
    print(f"\n=== RESUMEN DE PROPIEDADES ===")
    print(f"Total en repositorio: {total}")
    print(f"- Propiedades en venta: {total_venta}")
    print(f"- Propiedades en renta: {total_renta}")
    print(f"\nPendientes de procesar: {falta}")
    print(f"- Ventas pendientes: {falta_venta}")
    print(f"- Rentas pendientes: {falta_renta}")
    print("=" * 30 + "\n")

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
            tipo_esperado = item["tipo"]  # Tipo de operación esperado según el origen del link
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
                
                titulo      = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
                descripcion = extraer_descripcion_estable(soup)
                precio_str  = extraer_precio_mejorado(soup)["texto"]
                precio_num  = procesar_numero_mexicano(precio_str) if precio_str else None
                vendedor, link_v = extraer_vendedor(soup)
                img_portada = descargar_imagen_por_playwright(page, ciudad, pid, carpeta, date_str)
                
                # Detectar tipo de operación con más contexto
                tipo_detectado = detectar_tipo_operacion(titulo, descripcion, precio_str, precio_num)
                
                # Validar coherencia entre tipo esperado y detectado
                tipo_final = tipo_esperado
                confianza_tipo = "alta" if tipo_detectado == tipo_esperado else "baja"
                
                # Validar precio según tipo de operación
                es_precio_valido, confianza_precio, mensaje_precio = validar_precio(precio_num, tipo_final)
                
                ubicacion   = extraer_ubicacion_desde_dom(soup)
                caracteristicas = extraer_caracteristicas(descripcion)
                
                datos = {
                    "id": pid,
                    "link": url,
                    "titulo": titulo,
                    "precio": {
                        "texto": precio_str,
                        "valor": precio_num,
                        "es_valido": es_precio_valido,
                        "confianza": confianza_precio,
                        "mensaje": mensaje_precio
                    },
                    "ciudad": ciudad,
                    "vendedor": vendedor,
                    "link_vendedor": link_v,
                    "descripcion": descripcion,
                    "imagen_portada": img_portada,
                    "tipo_operacion": {
                        "tipo": tipo_final,
                        "tipo_detectado": tipo_detectado,
                        "confianza": confianza_tipo
                    },
                    "ubicacion": ubicacion,
                    "caracteristicas": caracteristicas,
                    "fecha_extraccion": datetime.now().isoformat(),
                    "archivos": {
                        "html": f"{ciudad}-{date_str}-{pid}.html",
                        "json": f"{ciudad}-{date_str}-{pid}.json",
                        "imagen": img_portada["nombre_archivo"]
                    }
                }
                
                # Guardar archivos
                ruta_html, ruta_json = guardar_archivos(html, datos, ciudad, pid, carpeta, date_str)
                
                # Actualizar repositorio maestro
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

    # Imprimir resumen final
    print(f"\n=== RESUMEN FINAL ===")
    print(f"Total de propiedades procesadas: {ok + err}")
    print(f"- Exitosas: {ok}")
    print(f"- Con errores: {err}")
    print(f"\nTotal en repositorio maestro: {len(data_master)}")
    print("=" * 30 + "\n")

if __name__ == '__main__':
    main()