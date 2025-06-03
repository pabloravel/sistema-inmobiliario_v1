#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extractor_propiedades_v10.py

Versión unificada y mejorada que combina:
- extrae_html_con_operacion_v3.py
- extractor_propiedades_v9.py

Mejoras:
1. Unificación de campos en español
2. Estructura de datos consistente
3. Mejor manejo de errores y logging
4. Optimización de rendimiento
5. Mejor detección de propiedades
6. Sistema de validación mejorado
"""

import os
import json
import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Dict, Union, List, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup

# Constantes globales
CARPETA_RESULTADOS = "resultados"
CARPETA_LINKS = os.path.join(CARPETA_RESULTADOS, "links/repositorio_unico.json")
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
ESTADO_FB = "fb_state.json"
BASE_URL = "https://www.facebook.com"

# Estructura de datos unificada
ESTRUCTURA_PROPIEDAD = {
    "id": "",
    "url": "",
    "fecha_extraccion": "",
    "descripcion": {
        "texto_original": "",
        "texto_limpio": ""
    },
    "ubicacion": {
        "ciudad": "",
        "colonia": "",
        "calle": "",
        "referencias": [],
        "coordenadas": {
            "latitud": None,
            "longitud": None
        }
    },
    "caracteristicas": {
        "tipo_propiedad": "",
        "tipo_operacion": "",
        "superficie_terreno": 0,
        "superficie_construccion": 0,
        "recamaras": 0,
        "banos": 0,
        "estacionamientos": 0,
        "niveles": 0
    },
    "precios": {
        "valor": 0.0,
        "moneda": "MXN",
        "tipo": "",  # venta/renta
        "incluye_mantenimiento": False,
        "cuota_mantenimiento": 0.0
    },
    "amenidades": [],
    "estado_legal": {
        "escrituras": False,
        "predial": False,
        "servicios_pagados": False,
        "libre_gravamen": False
    },
    "metadata": {
        "vendedor": {
            "nombre": "",
            "tipo": "",  # particular/inmobiliaria
            "perfil": ""
        },
        "estado_listado": "activo",
        "ultima_actualizacion": ""
    }
}

class ProgressBar:
    """Barra de progreso mejorada con estadísticas"""
    MAGENTA = "\033[35m"
    RESET = "\033[0m"
    
    def __init__(self, total: int, desc: str = '', unit: str = ''):
        self.total = total
        self.n = 0
        self.ok = 0
        self.err = 0
        self.desc = desc
        self.unit = unit
        self.width = os.get_terminal_size().columns - 40
        print(f"{self.desc}: 0/{self.total} {self.unit}")
        
    def update(self, n: int = 1, ok: int = None, err: int = None):
        self.n += n
        if ok is not None: self.ok = ok
        if err is not None: self.err = err
        p = int(self.width * self.n / self.total)
        print(f"\033[A{self.desc}: {self.n}/{self.total} {self.unit}")
        print(f"{self.MAGENTA}{'█'*p}{'-'*(self.width-p)} OK:{self.ok} Err:{self.err}{self.RESET}")
    
    def close(self):
        print()

def normalizar_texto(texto: str) -> str:
    """Normaliza un texto eliminando caracteres especiales y espacios extras"""
    if not texto:
        return ""
    
    # Eliminar emojis y caracteres especiales
    texto = re.sub(r'[^\w\s\-\.,;:()¿?¡!$%]', '', texto)
    
    # Normalizar espacios
    texto = ' '.join(texto.split())
    
    return texto.strip()

def normalizar_precio(texto: str) -> Tuple[float, str]:
    """Normaliza el formato del precio y retorna (valor, moneda)"""
    texto = texto.lower()
    valor = 0.0
    moneda = 'MXN'
    
    # Buscar precio en formato específico primero
    if match := re.search(r'precio.*?\$\s*([\d,]+(?:,\d{3})*)', texto):
        try:
            valor_str = match.group(1)
            valor = float(valor_str.replace(',', ''))
            return valor, moneda
        except ValueError:
            pass
    
    # Patrones generales de precio
    patrones = [
        r'\$\s*([\d,]+(?:,\d{3})*)',  # $3,680,000
        r'([\d,]+(?:,\d{3})*)\s*\$',  # 3,680,000$
    ]
    
    for patron in patrones:
        if match := re.search(patron, texto):
            try:
                valor_str = match.group(1)
                valor = float(valor_str.replace(',', ''))
                break
            except ValueError:
                continue
    
    # Detectar moneda
    if any(m in texto for m in ['usd', 'dlls', 'dolar']):
        moneda = 'USD'
    elif 'euro' in texto:
        moneda = 'EUR'
    
    return valor, moneda

def extraer_tipo_operacion(texto: str) -> str:
    """Extrae el tipo de operación de forma más precisa"""
    texto = texto.lower()
    
    # Palabras clave para cada tipo
    indicadores = {
        'venta': [
            r'\b(?:en\s+)?venta\b',
            r'\bvendo\b',
            r'\bse\s+vende\b',
            r'\bremato\b',
            r'\boportunidad\b'
        ],
        'renta': [
            r'\b(?:en\s+)?renta\b',
            r'\balquiler\b',
            r'\barriendo\b',
            r'\bse\s+renta\b',
            r'\bpor\s+mes\b',
            r'\bmensual\b'
        ]
    }
    
    # Buscar indicadores explícitos
    for tipo, patrones in indicadores.items():
        if any(re.search(patron, texto) for patron in patrones):
            return tipo.capitalize()
    
    # Si no hay indicadores explícitos, inferir por precio
    if match := re.search(r'[\$\€]?\s*([\d,]+(?:\.\d{1,2})?)', texto):
        try:
            precio = float(match.group(1).replace(',', ''))
            return 'Venta' if precio >= 500000 else 'Renta'
        except:
            pass
    
    return 'Desconocido'

def extraer_superficie(texto: str) -> Dict[str, int]:
    """Extrae información de superficie de forma más precisa"""
    resultado = {
        "superficie_terreno": 0,
        "superficie_construccion": 0
    }
    
    # Patrones mejorados para terreno
    patrones_terreno = [
        r'terreno\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts?2|metros?2?|m²)',
        r'superficie\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts?2|metros?2?|m²)',
        r'lote\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts?2|metros?2?|m²)',
        r'(\d+)\s*(?:m2|mts?2|metros?2?|m²)\s*(?:de)?\s*terreno'
    ]
    
    # Patrones mejorados para construcción
    patrones_construccion = [
        r'construcci[oó]n\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts?2|metros?2?|m²)',
        r'construidos?\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts?2|metros?2?|m²)',
        r'(\d+)\s*(?:m2|mts?2|metros?2?|m²)\s*(?:de)?\s*construcci[oó]n'
    ]
    
    # Buscar superficie de terreno
    for patron in patrones_terreno:
        if match := re.search(patron, texto, re.IGNORECASE):
            try:
                valor = int(float(match.group(1)))
                if 20 <= valor <= 10000:  # Rango razonable
                    resultado["superficie_terreno"] = valor
                    break
            except ValueError:
                continue
    
    # Buscar superficie construida
    for patron in patrones_construccion:
        if match := re.search(patron, texto, re.IGNORECASE):
            try:
                valor = int(float(match.group(1)))
                if 20 <= valor <= 5000:  # Rango razonable
                    resultado["superficie_construccion"] = valor
                    break
            except ValueError:
                continue
    
    return resultado

def extraer_caracteristicas(texto: str) -> Dict[str, Union[int, str]]:
    """Extrae características básicas de la propiedad"""
    caracteristicas = {
        "recamaras": 0,
        "banos": 0,
        "estacionamientos": 0,
        "niveles": 0
    }
    
    texto = texto.lower()
    
    # Patrones para cada característica
    patrones = {
        "recamaras": [
            r'(\d+)\s*(?:recámara|recamara|habitación|habitacion|dormitorio)s?',
            r'(\d+)\s*(?:rec|hab)\b'
        ],
        "banos": [
            r'(\d+)(?:\.\d+)?\s*(?:baño|sanitario|wc)s?(?:\s*completos?)?',
            r'(\d+)(?:\.\d+)?\s*(?:medio)s?\s*baño'
        ],
        "estacionamientos": [
            r'(\d+)\s*(?:estacionamiento|cochera|garage|lugar|cajón)s?',
            r'estacionamiento\s*para\s*(\d+)'
        ],
        "niveles": [
            r'(\d+)\s*(?:nivel|piso|planta)s?',
            r'(\d+)\s*(?:story|floor)s?'
        ]
    }
    
    # Buscar cada característica
    for caract, lista_patrones in patrones.items():
        for patron in lista_patrones:
            if match := re.search(patron, texto):
                try:
                    valor = int(float(match.group(1)))
                    if 1 <= valor <= 10:  # Rango razonable
                        caracteristicas[caract] = valor
                        break
                except ValueError:
                    continue
    
    return caracteristicas

def extraer_tipo_propiedad(texto: str) -> str:
    """Extrae el tipo de propiedad de forma más precisa"""
    texto = texto.lower()
    
    # Mapeo de tipos con sus variantes
    tipos = {
        'Casa': [
            r'\bcasa\b',
            r'\bcasa\s+(?:sola|habitaci[oó]n|residencial)\b',
            r'\bresidencia\b',
            r'\bvilla\b'
        ],
        'Departamento': [
            r'\bdepartamento\b',
            r'\bdepto\b',
            r'\bdpto\b',
            r'\bapartamento\b'
        ],
        'Terreno': [
            r'\bterreno\b',
            r'\blote\b',
            r'\bpredio\b'
        ],
        'Local': [
            r'\blocal\b',
            r'\blocal\s+comercial\b',
            r'\bcomercio\b'
        ],
        'Oficina': [
            r'\boficina\b',
            r'\bdespacho\b'
        ],
        'Bodega': [
            r'\bbodega\b',
            r'\balmac[ée]n\b',
            r'\bnave\s+industrial\b'
        ]
    }
    
    # Buscar coincidencias
    for tipo, patrones in tipos.items():
        if any(re.search(patron, texto) for patron in patrones):
            return tipo
    
    return 'Otro'

def extraer_ubicacion(texto: str) -> Dict[str, Any]:
    """Extrae información de ubicación de forma más precisa"""
    ubicacion = {
        "ciudad": "",
        "colonia": "",
        "calle": "",
        "referencias": [],
        "coordenadas": {
            "latitud": None,
            "longitud": None
        }
    }
    
    texto = texto.lower()
    
    # Patrones para referencias sin incluir precios
    patrones_ref = [
        r'cerca\s+de\s+([^\.,$]+)',
        r'a\s+(?:\d+\s+)?(?:minutos?|metros?)\s+de\s+([^\.,$]+)',
        r'junto\s+a\s+([^\.,$]+)',
        r'frente\s+a\s+([^\.,$]+)'
    ]
    
    referencias = []
    for patron in patrones_ref:
        if matches := re.finditer(patron, texto):
            for match in matches:
                ref = match.group(1).strip()
                # Excluir referencias que contienen precios
                if not re.search(r'[\$\€]\s*\d+', ref) and 5 <= len(ref) <= 100:
                    referencias.append(ref.title())
    
    ubicacion["referencias"] = list(set(referencias))  # Eliminar duplicados
    
    # Ciudades conocidas con sus variantes
    ciudades = {
        "cuernavaca": [
            r"\bcuernavaca\b",
            r"\bcuerna\b",
            r"\bmorelos\b"
        ],
        "jiutepec": [
            r"\bjiutepec\b",
            r"\bcivac\b"
        ],
        "temixco": [
            r"\btemixco\b",
            r"\bburgos\b"
        ]
    }
    
    # Detectar ciudad
    for ciudad, patrones in ciudades.items():
        if any(re.search(patron, texto) for patron in patrones):
            ubicacion["ciudad"] = ciudad.title()
            break
    
    # Extraer colonia
    patrones_colonia = [
        r"(?:colonia|col\.|fracc\.|fraccionamiento)\s+([a-zá-úñ\s]+)(?=\s|$)",
        r"en\s+(?:la\s+)?(?:colonia|col\.|fracc\.|fraccionamiento)\s+([a-zá-úñ\s]+)(?=\s|$)"
    ]
    
    for patron in patrones_colonia:
        if match := re.search(patron, texto):
            colonia = match.group(1).strip()
            if 3 <= len(colonia) <= 50:  # Longitud razonable
                ubicacion["colonia"] = colonia.title()
                break
    
    # Extraer calle
    patrones_calle = [
        r"(?:calle|av\.|avenida|boulevard|blvd\.|camino)\s+([a-zá-úñ\s]+(?:\s+#?\d+)?)",
        r"ubicad[oa]\s+en\s+([a-zá-úñ\s]+(?:\s+#?\d+)?)",
        r"sobre\s+([a-zá-úñ\s]+(?:\s+#?\d+)?)"
    ]
    
    for patron in patrones_calle:
        if match := re.search(patron, texto):
            calle = match.group(1).strip()
            if 3 <= len(calle) <= 50:  # Longitud razonable
                ubicacion["calle"] = calle.title()
                break
    
    return ubicacion

def expandir_descripcion(page) -> None:
    """Expande el botón 'Ver más' si existe"""
    try:
        # Intentar diferentes selectores para el botón "Ver más"
        for selector in [
            "text=Ver más",
            "text='Ver más'",
            "[aria-label='Ver más']",
            "div:has-text('Ver más')"
        ]:
            try:
                ver_mas = page.locator(selector).first
                if ver_mas and ver_mas.is_visible():
                    ver_mas.click()
                    page.wait_for_timeout(1500)  # Esperar más tiempo
                    break
            except:
                continue
    except Exception as e:
        print(f"Nota: No se pudo expandir 'Ver más': {e}")

def extraer_vendedor(page) -> Dict[str, str]:
    """Extrae información limpia del vendedor"""
    vendedor = {
        "nombre": "",
        "perfil": "",
        "tipo": "particular"
    }
    
    try:
        # Extraer datos del vendedor usando JavaScript
        vendedor_data = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a'));
            for (const link of links) {
                if (link.href.includes('/profile.php?id=') || 
                    link.href.match(/facebook\\.com\\/[^\\/]+$/)) {
                    const nombre = link.textContent.trim();
                    let perfil = link.href;
                    
                    // Limpiar el link del perfil
                    perfil = perfil.split('?')[0];  // Remover parámetros
                    perfil = perfil.replace(/\\/$/, '');  // Remover slash final
                    
                    // Si es un link de redirección, intentar extraer la URL real
                    if (perfil.includes('l.facebook.com/l.php')) {
                        try {
                            const url = new URL(perfil);
                            const realUrl = url.searchParams.get('u');
                            if (realUrl) perfil = realUrl;
                        } catch (e) {}
                    }
                    
                    return {
                        nombre: nombre,
                        perfil: perfil,
                        tipo: perfil.includes('profile.php') ? 'particular' : 'inmobiliaria'
                    };
                }
            }
            return null;
        }""")
        
        if vendedor_data:
            vendedor.update(vendedor_data)
            
            # Limpiar el nombre del vendedor
            nombre = vendedor["nombre"]
            # Remover emojis y caracteres especiales
            nombre = re.sub(r'[^\w\s\-áéíóúñÁÉÍÓÚÑ]', ' ', nombre)
            # Remover palabras comunes no deseadas
            palabras_no_deseadas = [
                'la unica plataforma',
                'inmuebles comerciales',
                'en mexico',
                'spot2',
                'bienes raices',
                'real estate',
                'agente',
                'asesor',
                'inmobiliaria',
                'única',
                'plataforma',
                'de',
                'en',
                'comerciales'
            ]
            for palabra in palabras_no_deseadas:
                nombre = re.sub(rf'\b{palabra}\b', '', nombre, flags=re.IGNORECASE)
            # Normalizar espacios y capitalizar
            nombre = ' '.join(filter(None, nombre.split()))
            nombre = nombre.title()
            vendedor["nombre"] = nombre.strip()
            
            # Limpiar la URL del perfil
            if vendedor["perfil"]:
                # Remover parámetros de tracking y otros
                perfil = re.sub(r'\?.*$', '', vendedor["perfil"])
                # Remover slash final
                perfil = perfil.rstrip('/')
                # Si es un link de redirección, intentar extraer la URL real
                if 'l.facebook.com/l.php' in perfil:
                    try:
                        from urllib.parse import parse_qs, urlparse
                        parsed = urlparse(perfil)
                        params = parse_qs(parsed.query)
                        if 'u' in params:
                            perfil = params['u'][0]
                    except:
                        pass
                vendedor["perfil"] = perfil
            
    except Exception as e:
        print(f"Error extrayendo datos del vendedor: {e}")
    
    return vendedor

def extraer_descripcion(page, soup) -> Dict[str, str]:
    """Extrae y normaliza la descripción completa"""
    descripcion = {
        "texto_original": "",
        "texto_limpio": ""
    }
    
    # Expandir el botón "Ver más"
    expandir_descripcion(page)
    
    # Obtener el HTML actualizado
    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    
    # Buscar la descripción en el DOM actualizado
    for div in soup.find_all("div"):
        if div.get_text(strip=True) in ["Descripción", "Detalles"]:
            if siguiente := div.find_next_sibling("div"):
                texto = siguiente.get_text(strip=True)
                # Limpiar el texto
                texto = texto.replace("Ver menos", "").replace("Ver más", "").strip()
                descripcion["texto_original"] = texto
                descripcion["texto_limpio"] = normalizar_texto(texto)
                break
    
    return descripcion

def extraer_precio(texto: str) -> Tuple[float, str]:
    """Extrae el precio del texto y retorna (valor, moneda)"""
    texto = texto.lower()
    
    # Buscar precio en formato específico primero
    if match := re.search(r'precio.*?\$\s*([\d,]+(?:,\d{3})*)', texto):
        try:
            valor_str = match.group(1)
            valor = float(valor_str.replace(',', ''))
            return valor, 'MXN'
        except ValueError:
            pass
    
    # Buscar otros formatos de precio
    patrones = [
        r'\$\s*([\d,]+(?:,\d{3})*)',  # $3,680,000
        r'([\d,]+(?:,\d{3})*)\s*\$',  # 3,680,000$
    ]
    
    for patron in patrones:
        if match := re.search(patron, texto):
            try:
                valor_str = match.group(1)
                valor = float(valor_str.replace(',', ''))
                
                # Detectar moneda
                moneda = 'MXN'
                if any(m in texto for m in ['usd', 'dlls', 'dolar']):
                    moneda = 'USD'
                elif 'euro' in texto:
                    moneda = 'EUR'
                
                return valor, moneda
            except ValueError:
                continue
    
    return 0.0, 'MXN'

def procesar_propiedad(datos: Dict, page) -> Dict:
    """Procesa una propiedad y extrae todos sus datos"""
    try:
        # Expandir descripción
        expandir_descripcion(page)
        
        # Obtener HTML y crear soup
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extraer datos básicos
        titulo = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
        descripcion = extraer_descripcion(page, soup)
        precio, moneda = extraer_precio(descripcion["texto_original"])
        ubicacion = extraer_ubicacion(descripcion["texto_original"])
        vendedor = extraer_vendedor(page)
        
        # Extraer características
        caracteristicas = extraer_caracteristicas(descripcion["texto_original"])
        tipo_operacion = extraer_tipo_operacion(descripcion["texto_original"])
        tipo_propiedad = extraer_tipo_propiedad(descripcion["texto_original"])
        superficies = extraer_superficie(descripcion["texto_original"])
        
        # Construir resultado
        resultado = {
            "id": datos.get("id", ""),
            "url": datos.get("link", ""),
            "fecha_extraccion": datetime.now().isoformat(),
            "descripcion": descripcion,
            "ubicacion": ubicacion,
            "caracteristicas": {
                "tipo_propiedad": tipo_propiedad,
                "tipo_operacion": tipo_operacion,
                "superficie_terreno": superficies["superficie_terreno"],
                "superficie_construccion": superficies["superficie_construccion"],
                "recamaras": caracteristicas.get("recamaras", 0),
                "banos": caracteristicas.get("banos", 0),
                "estacionamientos": caracteristicas.get("estacionamientos", 0),
                "niveles": caracteristicas.get("niveles", 0)
            },
            "precios": {
                "valor": precio,
                "moneda": moneda,
                "tipo": tipo_operacion,
                "incluye_mantenimiento": False,
                "cuota_mantenimiento": 0.0
            },
            "amenidades": [],
            "estado_legal": {
                "escrituras": False,
                "predial": False,
                "servicios_pagados": False,
                "libre_gravamen": False
            },
            "metadata": {
                "vendedor": vendedor,
                "estado_listado": "activo",
                "ultima_actualizacion": ""
            }
        }
        
        return resultado
        
    except Exception as e:
        print(f"Error procesando propiedad: {e}")
        traceback.print_exc()
        return None

def main():
    """Función principal que coordina todo el proceso"""
    try:
        # 1. Crear directorios necesarios
        fecha = datetime.now().strftime('%Y-%m-%d')
        Path(f'resultados/{fecha}').mkdir(parents=True, exist_ok=True)
        
        print("\n1. Cargando repositorio maestro...")
        try:
            with open(CARPETA_REPO_MASTER, 'r', encoding='utf-8') as f:
                repositorio = json.load(f)
                print(f"   ✓ Repositorio cargado con {len(repositorio)} propiedades")
        except:
            print("   ! Creando nuevo repositorio")
            repositorio = {}
        
        print("\n2. Cargando enlaces a procesar...")
        try:
            with open(CARPETA_LINKS, 'r', encoding='utf-8') as f:
                links = json.load(f)
                print(f"   ✓ {len(links)} enlaces cargados")
        except Exception as e:
            print(f"   ! Error cargando enlaces: {e}")
            return
        
        # Filtrar propiedades ya procesadas
        links_pendientes = []
        for item in links:
            if isinstance(item, dict):
                link = item.get('link', '')
            else:
                link = item
            
            if not link:
                continue
                
            # Extraer ID de la propiedad
            if match := re.search(r'/(\d+)/?$', link):
                id_prop = match.group(1)
                if id_prop not in repositorio:
                    links_pendientes.append({
                        'link': link,
                        'id': id_prop,
                        'ciudad': item.get('ciudad', 'cuernavaca') if isinstance(item, dict) else 'cuernavaca'
                    })
        
        print(f"\n3. Enlaces pendientes: {len(links_pendientes)}")
        if not links_pendientes:
            print("No hay nuevos enlaces para procesar")
            return
            
        pbar = ProgressBar(len(links_pendientes), "Procesando", "propiedades")
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                storage_state=ESTADO_FB,
                viewport={'width': 1280, 'height': 800}
            )
            page = context.new_page()
            
            ok = err = 0
            for item in links_pendientes:
                link = item['link']
                ciudad = item.get('ciudad', 'cuernavaca')
                id_propiedad = item['id']
                
                try:
                    # 1. Navegar a la página
                    page.goto(link, wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_selector('h1', timeout=15000)
                    
                    # 2. Verificar disponibilidad
                    html = page.content()
                    if "Este contenido no está disponible" in html:
                        err += 1
                        continue
                    
                    # 3. Extraer datos
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    datos = {
                        'id': id_propiedad,
                        'link': link,
                        'ciudad': ciudad,
                        'titulo': soup.find('h1').get_text(strip=True) if soup.find('h1') else "",
                        'descripcion': "",
                        'precio': "",
                        'vendedor': {}
                    }
                    
                    # Extraer descripción
                    for div in soup.find_all('div'):
                        if div.get_text(strip=True) in ['Descripción', 'Detalles']:
                            if siguiente := div.find_next_sibling('div'):
                                datos['descripcion'] = siguiente.get_text(strip=True)
                                break
                    
                    # Extraer precio
                    for span in soup.find_all('span'):
                        texto = span.get_text(strip=True)
                        if texto.startswith('$') and len(texto) < 30:
                            datos['precio'] = texto
                            break
                    
                    # Extraer vendedor
                    try:
                        vendedor_info = page.evaluate("""() => {
                            const links = Array.from(document.querySelectorAll('a'));
                            for (const link of links) {
                                if (link.href.includes('/profile.php?id=') || 
                                    link.href.match(/facebook\\.com\\/[^\\/]+$/)) {
                                    return {
                                        nombre: link.textContent.trim(),
                                        perfil: link.href,
                                        tipo: link.href.includes('profile.php') ? 'particular' : 'inmobiliaria'
                                    }
                                }
                            }
                            return null;
                        }""")
                        if vendedor_info:
                            datos['vendedor'] = vendedor_info
                    except:
                        pass
                    
                    # 5. Procesar propiedad
                    if propiedad_procesada := procesar_propiedad(datos, page):
                        repositorio[id_propiedad] = propiedad_procesada
                        ok += 1
                    else:
                        err += 1
                    
                except Exception as e:
                    print(f"\n   ! Error en {id_propiedad}: {str(e)}")
                    err += 1
                
                pbar.update(1, ok, err)
                
                # Guardar progreso
                with open(CARPETA_REPO_MASTER, 'w', encoding='utf-8') as f:
                    json.dump(repositorio, f, ensure_ascii=False, indent=2)
            
            pbar.close()
            page.close()
            browser.close()
        
        print(f"\nProcesamiento completado:")
        print(f"✓ Exitosos: {ok}")
        print(f"✗ Errores: {err}")
        print(f"Total en repositorio: {len(repositorio)}")
        
    except Exception as e:
        print(f"Error general: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    main() 