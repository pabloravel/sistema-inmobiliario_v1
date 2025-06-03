#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion_v11_test.py

Versión de prueba que combina:
- Eficiencia de extrae_html_estable.py
- Funcionalidad mejorada de v10
- Optimización de tiempos de espera
- Mejor manejo de errores
"""

import os
import json
import time
import re
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional, List
import traceback

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
        self.total = total; self.n = 0; self.ok = 0; self.err = 0
        self.desc = desc; self.unit = unit
        self.width = os.get_terminal_size().columns - 40
        print(f"{self.desc}: 0/{self.total} {self.unit}")
        
    def update(self, n=1, ok=None, err=None):
        self.n += n
        if ok is not None: self.ok = ok
        if err is not None: self.err = err
        p = int(self.width * self.n / self.total)
        print(f"\033[A{self.desc}: {self.n}/{self.total} {self.unit}")
        print(f"{self.MAGENTA}{'█'*p}{'-'*(self.width-p)} OK:{self.ok} Err:{self.err}{self.RESET}")
    
    def close(self):
        print()

def normalizar_texto(texto: str) -> str:
    """Normaliza un texto eliminando espacios extras y caracteres especiales"""
    if not texto:
        return ""
    texto = ' '.join(texto.split())
    return texto.lower()

def normalizar_precio(precio_str: str) -> Dict[str, Any]:
    """Normaliza el formato del precio y extrae información adicional"""
    resultado = {
        'precio_str': '0',
        'precio_num': 0,
        'moneda': 'MXN',
        'periodo': None
    }
    
    if not precio_str:
        return resultado
        
    # Limpiar y extraer número
    nums = ''.join(filter(str.isdigit, precio_str))
    try:
        resultado['precio_num'] = float(nums)
        resultado['precio_str'] = f"${resultado['precio_num']:,.2f}"
    except:
        pass
    
    # Detectar periodo para rentas
    texto = precio_str.lower()
    if any(p in texto for p in ['/mes', 'mensual', 'por mes']):
        resultado['periodo'] = 'mensual'
    elif any(p in texto for p in ['/año', 'anual', 'por año']):
        resultado['periodo'] = 'anual'
        
    return resultado

def extraer_descripcion_mejorada(page, soup) -> str:
    """
    Extrae la descripción usando múltiples estrategias y mantiene la funcionalidad existente
    """
    # 1. Intentar expandir la descripción primero
    try:
        ver_mas = page.locator("div[role='button']:has-text('Ver más')").first
        if ver_mas and ver_mas.is_visible():
            ver_mas.click()
            page.wait_for_timeout(1000)
    except:
        pass
    
    descripcion = ""
    
    # 2. Intentar selectores específicos de Facebook
    try:
        for selector in [
            "div[data-testid='marketplace_listing_item_description']",
            "div[data-testid='marketplace_listing_description']",
            "div[data-testid='marketplace_feed_story_description']",
            "div[data-testid='marketplace_feed_description']",
            "div[class*='description']",
            "div[class*='details']",
            "div[class*='content']"
        ]:
            elementos = page.locator(selector).all()
            for elemento in elementos:
                if elemento.is_visible():
                    texto = elemento.inner_text().strip()
                    if texto and len(texto) > 10:
                        # Verificar que no sea un elemento de navegación o botón
                        if not any(palabra in texto.lower() for palabra in [
                            "ver más", "ver menos", "enviar mensaje", "reportar",
                            "chats no leídos", "notificaciones", "omitir", "crear pin",
                            "messenger", "facebook", "marketplace", "viviendas en venta",
                            "propiedades en venta", "casas en venta", "departamentos en venta"
                        ]):
                            descripcion = texto
                            break
            if descripcion:
                break
    except:
        pass
    
    # 3. Buscar en el HTML como respaldo
    if not descripcion:
        try:
            # Buscar divs que puedan contener la descripción
            divs = soup.find_all('div')
            for div in divs:
                texto = div.get_text(strip=True)
                if texto and len(texto) > 50:  # Mínimo 50 caracteres para ser considerado descripción
                    # Verificar que no sea un elemento de navegación o sistema
                    if not any(palabra in texto.lower() for palabra in [
                        "ver más", "ver menos", "enviar mensaje", "reportar",
                        "chats no leídos", "notificaciones", "omitir", "crear pin",
                        "messenger", "facebook", "marketplace", "cifrado", "pin",
                        "historial", "chat", "seguridad", "viviendas en venta",
                        "propiedades en venta", "casas en venta", "departamentos en venta"
                    ]):
                        descripcion = texto
                        break
        except:
            pass
    
    # 4. Buscar después de palabras clave como último recurso
    if not descripcion:
        texto_completo = soup.get_text(" ", strip=True)
        for palabra in ["Descripción", "Detalles", "Description", "Acerca de esta propiedad"]:
            if palabra in texto_completo:
                partes = texto_completo.split(palabra)
                if len(partes) > 1:
                    descripcion = partes[1]
                    break
    
    # 5. Limpiar la descripción
    if descripcion:
        # Obtener título y precio para evitar repetirlos
        try:
            titulo = page.locator("h1").first.inner_text().strip()
        except:
            try:
                if h1 := soup.find("h1"):
                    titulo = h1.get_text(strip=True)
            except:
                titulo = ""
        
        try:
            precio_elemento = page.locator("div[data-testid='marketplace_listing_item_price']").first
            if precio_elemento and precio_elemento.is_visible():
                precio = precio_elemento.inner_text().strip()
            else:
                precio = ""
        except:
            precio = ""
        
        # Eliminar secciones no deseadas
        secciones_no_deseadas = [
            "Ver menos",
            "Información del vendedor",
            "Sugerencias de hoy",
            "Publicidad",
            "Obtén",
            "Detalles del vendedor",
            "Ver más",
            "Reporta",
            "Envía un mensaje",
            "Marketplace",
            "Facebook",
            "Messenger",
            "chats no leídos",
            "Número de notificaciones",
            "Omitir",
            "Mejoramos la seguridad",
            "cifrado de extremo",
            "Cambios en el acceso",
            "historial de chat",
            "Crear PIN",
            "necesitarás un PIN",
            "Viviendas en venta",
            "Propiedades en venta",
            "Casas en venta",
            "Departamentos en venta"
        ]
        
        # Agregar título y precio a las secciones no deseadas si existen
        if titulo:
            secciones_no_deseadas.append(titulo)
        if precio:
            secciones_no_deseadas.append(precio)
        
        for seccion in secciones_no_deseadas:
            if seccion in descripcion:
                descripcion = descripcion.split(seccion)[0]
        
        # Eliminar espacios múltiples
        descripcion = ' '.join(descripcion.split())
        
        # Eliminar caracteres especiales pero mantener acentos, ñ y puntuación básica
        descripcion = re.sub(r'[^\w\s\.,;:áéíóúüñÁÉÍÓÚÜÑ¿¡-]', '', descripcion)
        
        # Eliminar emojis
        descripcion = re.sub(r'[\U0001F300-\U0001F9FF]', '', descripcion)
        
        # Eliminar URLs
        descripcion = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', descripcion)
        
        # Eliminar números de teléfono
        descripcion = re.sub(r'\b(?:\+?[0-9]{1,3}[-.]?)?\(?[0-9]{3}\)?[-.]?[0-9]{3}[-.]?[0-9]{4}\b', '', descripcion)
        
        # Eliminar correos electrónicos
        descripcion = re.sub(r'\S+@\S+', '', descripcion)
        
        # Eliminar números sueltos al inicio
        descripcion = re.sub(r'^\d+\s*', '', descripcion)
        
        # Eliminar líneas vacías y espacios al inicio/final
        descripcion = '\n'.join(linea.strip() for linea in descripcion.splitlines() if linea.strip())
        
        # Si la descripción es muy corta o parece ser un mensaje del sistema, descartarla
        if len(descripcion) < 20 or any(palabra in descripcion.lower() for palabra in [
            "chat", "notificación", "pin", "seguridad", "cifrado", "historial",
            "viviendas en venta", "propiedades en venta", "casas en venta",
            "departamentos en venta"
        ]):
            descripcion = ""
        
        # Si la descripción es igual al título, descartarla
        if descripcion.lower() == titulo.lower():
            descripcion = ""
    
    return descripcion.strip() if descripcion else "Descripción no encontrada"

def extraer_precio_mejorado(page, soup) -> Dict[str, Any]:
    """
    Extrae y normaliza el precio usando múltiples estrategias
    """
    precio_info = {
        'precio_str': '0',
        'precio_num': 0,
        'moneda': 'MXN',
        'periodo': None
    }
    
    # 1. Intentar selectores específicos
    try:
        for selector in [
            "div[data-testid='marketplace_listing_item_price']",
            "div[data-testid='marketplace_listing_price']",
            "span[class*='price']",
            "div[class*='price']"
        ]:
            elemento = page.locator(selector).first
            if elemento and elemento.is_visible():
                texto = elemento.inner_text().strip()
                if '$' in texto:
                    # Limpiar y extraer precio
                    precio_limpio = ''.join(filter(str.isdigit, texto))
                    if precio_limpio:
                        precio_info['precio_num'] = float(precio_limpio)
                        # Ajustar precio si es muy bajo para una propiedad
                        if precio_info['precio_num'] < 1000:
                            precio_info['precio_num'] *= 1000
                        precio_info['precio_str'] = f"${precio_info['precio_num']:,.2f}"
                        break
    except:
        pass
    
    # 2. Buscar en el HTML como respaldo
    if precio_info['precio_num'] == 0:
        texto_completo = soup.get_text(" ", strip=True)
        for match in re.finditer(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', texto_completo):
            precio_str = match.group(1).replace(',', '')
            try:
                precio_info['precio_num'] = float(precio_str)
                # Ajustar precio si es muy bajo para una propiedad
                if precio_info['precio_num'] < 1000:
                    precio_info['precio_num'] *= 1000
                precio_info['precio_str'] = f"${precio_info['precio_num']:,.2f}"
                break
            except:
                continue
    
    # 3. Detectar periodo para rentas
    texto_completo = soup.get_text(" ", strip=True).lower()
    if any(palabra in texto_completo for palabra in ['/mes', 'mensual', 'por mes', 'al mes']):
        precio_info['periodo'] = 'mensual'
    elif any(palabra in texto_completo for palabra in ['/año', 'anual', 'por año', 'al año']):
        precio_info['periodo'] = 'anual'
    
    # 4. Si el precio es bajo, probablemente es renta mensual
    if precio_info['precio_num'] > 0 and precio_info['precio_num'] < 50000:
        precio_info['periodo'] = 'mensual'
    
    return precio_info

def extraer_ubicacion_mejorada(page, soup) -> Dict[str, str]:
    """
    Extrae información detallada de ubicación
    """
    ubicacion = {
        'direccion': '',
        'colonia': '',
        'referencias': []
    }
    
    # 1. Intentar selectores específicos
    try:
        for selector in [
            "div[data-testid='marketplace_listing_item_location']",
            "div[data-testid='marketplace_listing_location']",
            "span[class*='location']",
            "div[class*='location']"
        ]:
            elemento = page.locator(selector).first
            if elemento and elemento.is_visible():
                ubicacion['direccion'] = elemento.inner_text().strip()
                break
    except:
        pass
    
    # 2. Extraer colonia
    texto_completo = soup.get_text(" ", strip=True).lower()
    patrones_colonia = [
        r'col(?:onia)?\.?\s+([^,\.\n]+)',
        r'fracc?(?:ionamiento)?\.?\s+([^,\.\n]+)',
        r'unidad\s+([^,\.\n]+)',
        r'residencial\s+([^,\.\n]+)'
    ]
    
    for patron in patrones_colonia:
        if match := re.search(patron, texto_completo, re.I):
            colonia = match.group(1).strip().title()
            # Limpiar la colonia
            colonia = colonia.split('\n')[0]
            ubicacion['colonia'] = colonia
            break
    
    # 3. Extraer referencias
    referencias_conocidas = [
        'cerca de', 'junto a', 'frente a', 'a un costado de',
        'entre', 'esquina con', 'sobre', 'avenida', 'boulevard'
    ]
    
    for ref in referencias_conocidas:
        if match := re.search(rf'{ref}\s+([^,\.\n]+)', texto_completo, re.I):
            ubicacion['referencias'].append(match.group(0).strip())
    
    return ubicacion

def extraer_vendedor_mejorado(page) -> Dict[str, Any]:
    """
    Extrae información completa del vendedor
    """
    vendedor = {
        'nombre': '',
        'perfil': '',
        'tipo': 'particular',
        'verificado': False
    }
    
    try:
        # 1. Extraer información básica usando JavaScript
        vendedor_info = page.evaluate("""() => {
            const resultado = {
                nombre: '',
                perfil: '',
                tipo: 'particular',
                verificado: false
            };
            
            // Buscar link del perfil
            const links = Array.from(document.querySelectorAll('a'));
            for (const link of links) {
                if (link.href.includes('/profile.php?id=') || 
                    link.href.match(/facebook\\.com\\/[^\\/]+$/)) {
                    resultado.nombre = link.textContent.trim();
                    resultado.perfil = link.href;
                    resultado.tipo = link.href.includes('profile.php') ? 'particular' : 'inmobiliaria';
                    break;
                }
            }
            
            // Buscar badge de verificación
            const badges = document.querySelectorAll('div[aria-label*="Verificado"]');
            resultado.verificado = badges.length > 0;
            
            return resultado;
        }""")
        
        if vendedor_info:
            vendedor.update(vendedor_info)
            
            # Limpiar nombre
            nombre = vendedor['nombre']
            # Eliminar emojis y caracteres especiales
            nombre = re.sub(r'[\U0001F300-\U0001F9FF]', '', nombre)
            # Eliminar texto promocional
            nombre = nombre.split("Obtén")[0]
            nombre = nombre.split("Información")[0]
            # Eliminar palabras comunes
            palabras_eliminar = [
                "marketplace", "facebook", "properties", "real estate",
                "bienes raíces", "inmobiliaria", "realty", "hasta",
                "off", "recoge", "msi", "descuento", "oferta"
            ]
            for palabra in palabras_eliminar:
                nombre = re.sub(r'(?i)' + re.escape(palabra), '', nombre)
            vendedor['nombre'] = ' '.join(nombre.split())
            
            # Limpiar perfil
            if perfil := vendedor['perfil']:
                if '?' in perfil:
                    perfil = perfil.split('?')[0]
                vendedor['perfil'] = perfil
    except Exception as e:
        print(f"Error extrayendo vendedor: {str(e)}")
    
    return vendedor

def extraer_datos_propiedad(page, soup, pid: str, url: str, ciudad: str) -> Dict[str, Any]:
    """Extrae todos los datos relevantes de la propiedad"""
    # Obtener título y descripción
    titulo = ""
    try:
        titulo = page.locator("h1").first.inner_text().strip()
    except:
        try:
            if h1 := soup.find("h1"):
                titulo = h1.get_text(strip=True)
        except:
            titulo = "Título no encontrado"
    
    descripcion = extraer_descripcion_mejorada(page, soup)
    precio_info = extraer_precio_mejorado(page, soup)
    ubicacion = extraer_ubicacion_mejorada(page, soup)
    vendedor = extraer_vendedor_mejorado(page)
    
    # Extraer características básicas
    texto_completo = soup.get_text(" ", strip=True)
    caracteristicas = {
        'tipo_propiedad': extraer_tipo_propiedad(titulo + " " + descripcion),
        'tipo_operacion': detectar_tipo_operacion(titulo, descripcion, precio_info['precio_str']),
        'recamaras': 0,
        'banos': 0,
        'estacionamiento': 0,
        'metros_terreno': 0,
        'metros_construccion': 0,
        'niveles': 0,
        'antiguedad': None,
        'estado_conservacion': "No especificado"
    }
    
    # Patrones para características
    patrones = {
        'recamaras': [
            r'(\d+)\s*(?:rec[áa]maras?|habitaciones?|dormitorios?|cuartos?)',
            r'(?:rec[áa]maras?|habitaciones?)\s*:\s*(\d+)'
        ],
        'banos': [
            r'(\d+(?:\.5)?)\s*(?:ba[ñn]os?|wc|sanitarios?)',
            r'(?:ba[ñn]os?)\s*:\s*(\d+(?:\.5)?)'
        ],
        'metros_terreno': [
            r'(\d+)\s*(?:m2|m²|mts2)\s*(?:de)?\s*(?:terreno|superficie)',
            r'terreno\s*(?:de|con)?\s*(\d+)\s*(?:m2|m²|mts2)'
        ],
        'metros_construccion': [
            r'(\d+)\s*(?:m2|m²|mts2)\s*(?:de)?\s*(?:construcci[óo]n|construidos?)',
            r'construcci[óo]n\s*(?:de|con)?\s*(\d+)\s*(?:m2|m²|mts2)'
        ],
        'estacionamiento': [
            r'(\d+)\s*(?:cajones?|lugares?)\s*(?:de)?\s*(?:estacionamiento|garage|cochera)',
            r'estacionamiento\s*(?:para)?\s*(\d+)\s*(?:autos?|coches?)'
        ],
        'niveles': [
            r'(\d+)\s*(?:pisos?|nivele?s?|plantas?)',
            r'(?:de|con)\s*(\d+)\s*(?:pisos?|nivele?s?|plantas?)'
        ]
    }
    
    # Extraer valores usando los patrones
    texto_busqueda = f"{titulo} {descripcion} {texto_completo}".lower()
    for campo, lista_patrones in patrones.items():
        for patron in lista_patrones:
            if match := re.search(patron, texto_busqueda):
                try:
                    valor = match.group(1)
                    caracteristicas[campo] = float(valor) if '.' in valor else int(valor)
                    break
                except:
                    continue
    
    # Extraer antigüedad
    patrones_antiguedad = [
        r'(\d+)\s*(?:años?)\s*(?:de)?\s*(?:antigüedad|construcción)',
        r'construida?\s*(?:en|hace)\s*(\d+)\s*años?',
        r'del\s*(?:año|anio)\s*(\d{4})'
    ]
    
    for patron in patrones_antiguedad:
        if match := re.search(patron, texto_busqueda):
            try:
                valor = match.group(1)
                if len(valor) == 4:  # Es un año
                    caracteristicas['antiguedad'] = 2025 - int(valor)
                else:
                    caracteristicas['antiguedad'] = int(valor)
                break
            except:
                continue
    
    # Extraer estado de conservación
    estados = {
        'Nuevo': ['nueva', 'nuevo', 'a estrenar', 'recién construida'],
        'Excelente': ['excelente', 'impecable', 'remodelada', 'como nueva'],
        'Bueno': ['buen estado', 'bien conservada', 'en buen estado'],
        'Regular': ['regular', 'necesita mantenimiento'],
        'Para remodelar': ['remodelar', 'renovar', 'actualizar']
    }
    
    for estado, palabras in estados.items():
        if any(palabra in texto_busqueda for palabra in palabras):
            caracteristicas['estado_conservacion'] = estado
            break
    
    # Estructura final de datos
    datos = {
        'id': pid,
        'link': url,
        'titulo': titulo,
        'descripcion': descripcion,
        'precio': {
            'valor': precio_info['precio_num'],
            'valor_normalizado': float(precio_info['precio_num']),
            'moneda': precio_info['moneda'],
            'es_valido': precio_info['precio_num'] > 0,
            'error': None
        },
        'ubicacion': {
            'ciudad': ciudad,
            'colonia': ubicacion.get('colonia', ''),
            'calle': '',
            'referencias': ubicacion.get('referencias', []),
            'coordenadas': {
                'latitud': None,
                'longitud': None
            }
        },
        'caracteristicas': caracteristicas,
        'amenidades': extraer_amenidades(texto_busqueda),
        'estado_legal': {
            'escrituras': any(palabra in texto_busqueda for palabra in ['escrituras', 'escriturada', 'título de propiedad']),
            'cesion_derechos': any(palabra in texto_busqueda for palabra in ['cesión', 'cesion de derechos']),
            'creditos': any(palabra in texto_busqueda for palabra in [
                'crédito', 'credito', 'infonavit', 'fovissste', 'bancario',
                'hipotecario', 'financiamiento'
            ]),
            'constancia_posesion': 'constancia de posesion' in texto_busqueda
        },
        'vendedor': {
            'nombre': vendedor.get('nombre', ''),
            'tipo': vendedor.get('tipo', 'particular'),
            'telefono': vendedor.get('telefono', ''),
            'correo': vendedor.get('correo', '')
        },
        'imagenes': {
            'portada': '',
            'galeria': []
        },
        'metadata': {
            'fecha_extraccion': datetime.now().isoformat(),
            'ultima_actualizacion': datetime.now().isoformat(),
            'fuente': 'facebook_marketplace',
            'status': 'completo',
            'errores': [],
            'advertencias': []
        }
    }
    
    return datos

def procesar_propiedad(page, link: str, id_propiedad: str, ciudad: str, fecha_str: str) -> Optional[Dict]:
    """Procesa una propiedad individual"""
    print(f"\nProcesando {id_propiedad} ({ciudad})")
    print(f"URL: {link}")
    
    try:
        # 1. Navegar a la página
        page.set_default_timeout(15000)  # 15 segundos máximo
        page.goto(link, wait_until="domcontentloaded")
        page.wait_for_selector('h1', timeout=10000)
        
        # 2. Obtener HTML
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        # 3. Extraer datos
        datos = extraer_datos_propiedad(page, soup, id_propiedad, link, ciudad)
        
        # 4. Guardar archivos
        guardar_archivos(html, datos, id_propiedad, ciudad, fecha_str)
        
        return datos
        
    except PlaywrightTimeout:
        print(f"❌ Timeout al cargar la página")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        traceback.print_exc()
        return None

def guardar_archivos(html: str, datos: Dict, pid: str, ciudad: str, fecha_str: str) -> None:
    """Guarda los archivos HTML y JSON de la propiedad"""
    # Crear directorios
    dirs = {
        'html': f"resultados/html/{fecha_str}",
        'json': f"resultados/json/{fecha_str}",
        'errores': f"resultados/errores/{fecha_str}"
    }
    
    for dir_path in dirs.values():
        os.makedirs(dir_path, exist_ok=True)
    
    try:
        # Guardar HTML
        with open(f"{dirs['html']}/{pid}.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("   ✓ HTML guardado")
        
        # Guardar JSON
        with open(f"{dirs['json']}/{pid}.json", "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        print("   ✓ JSON guardado")
            
    except Exception as e:
        print(f"❌ Error guardando archivos: {str(e)}")
        with open(f"{dirs['errores']}/{pid}_error.txt", "w") as f:
            f.write(str(e))

def verificar_sesion() -> bool:
    """Verifica si existe una sesión válida de Facebook"""
    if not os.path.exists(ESTADO_FB):
        print("\n❌ Error: No se encontró archivo de sesión de Facebook")
        print("   Primero debes ejecutar guarda_login.py para guardar la sesión")
        return False
    
    try:
        with open(ESTADO_FB, 'r') as f:
            estado = json.load(f)
            if not estado.get('cookies'):
                print("\n❌ Error: Archivo de sesión inválido o vacío")
                print("   Ejecuta guarda_login.py para crear una nueva sesión")
                return False
        return True
    except Exception as e:
        print(f"\n❌ Error leyendo archivo de sesión: {str(e)}")
        print("   Ejecuta guarda_login.py para crear una nueva sesión")
        return False

def detectar_tipo_operacion(titulo: str, descripcion: str, precio_str: str) -> str:
    """
    Detecta el tipo de operación basado en el título, descripción y precio
    """
    texto = f"{titulo} {descripcion} {precio_str}".lower()
    
    # Palabras clave para cada tipo
    palabras_renta = [
        "renta", "alquiler", "/mes", "mensual", "rentar", "por mes", "al mes",
        "arrendamiento", "arriendo", "arrendar"
    ]
    palabras_venta = [
        "venta", "vendo", "remato", "oportunidad", "vender", "se vende",
        "en venta", "remate", "precio de venta"
    ]
    
    # Primero buscar en el texto
    if any(palabra in texto for palabra in palabras_renta):
        return "Renta"
    if any(palabra in texto for palabra in palabras_venta):
        return "Venta"
    
    # Si no hay palabras clave, inferir por precio
    try:
        precio_num = float(''.join(filter(str.isdigit, precio_str)))
        if precio_num >= 300_000:  # Asumimos que precios altos son venta
            return "Venta"
        if precio_num <= 50_000:  # Precios bajos son renta
            return "Renta"
    except:
        pass
    
    # Si el precio tiene periodo, es renta
    if any(palabra in texto for palabra in [
        "mensual", "/mes", "por mes", "al mes", "renta mensual",
        "precio mensual", "pago mensual"
    ]):
        return "Renta"
    
    # Si es departamento con precio bajo, probablemente es renta
    if "departamento" in texto and precio_num <= 50000:
        return "Renta"
    
    return "Desconocido"

def extraer_tipo_propiedad(texto: str) -> str:
    """
    Extrae el tipo de propiedad del texto
    """
    texto = texto.lower()
    
    tipos = {
        "casa": ["casa", "residencia", "chalet", "vivienda unifamiliar"],
        "departamento": ["departamento", "depto", "apartamento", "flat", "condominio"],
        "terreno": ["terreno", "lote", "predio", "tierra"],
        "local": ["local", "comercial", "negocio", "establecimiento"],
        "oficina": ["oficina", "despacho", "consultorio"],
        "bodega": ["bodega", "almacén", "nave industrial"],
        "otro": []
    }
    
    for tipo, palabras in tipos.items():
        if any(palabra in texto for palabra in palabras):
            return tipo.capitalize()
    
    return "Otro"

def extraer_caracteristicas(soup) -> Dict[str, Any]:
    """
    Extrae características numéricas y descriptivas de la propiedad
    """
    texto = soup.get_text(" ", strip=True).lower()
    
    def extraer_numero(patron: str) -> Optional[int]:
        if match := re.search(patron, texto):
            try:
                return int(match.group(1))
            except:
                pass
        return None
    
    caracteristicas = {
        'recamaras': extraer_numero(r'(\d+)\s*(?:rec[áa]maras?|habitaciones?|dormitorios?)'),
        'banos': extraer_numero(r'(\d+)\s*(?:ba[ñn]os?|wc)'),
        'metros_terreno': extraer_numero(r'(\d+)\s*(?:m2|mts2)\s*(?:terreno|superficie)'),
        'metros_construccion': extraer_numero(r'(\d+)\s*(?:m2|mts2)\s*(?:construcci[óo]n|construidos?)'),
        'estacionamientos': extraer_numero(r'(\d+)\s*(?:cajones?|lugares?)\s*(?:estacionamiento|cochera)'),
        'antiguedad': None
    }
    
    # Extraer antigüedad
    if match := re.search(r'(\d+)\s*años?\s*(?:de)?\s*(?:antigüedad|construcción)', texto):
        try:
            caracteristicas['antiguedad'] = int(match.group(1))
        except:
            pass
    
    return caracteristicas

def extraer_amenidades(texto: str) -> List[str]:
    """
    Extrae amenidades mencionadas en el texto
    """
    texto = texto.lower()
    amenidades = []
    
    amenidades_buscar = {
        'Alberca': ['alberca', 'piscina'],
        'Gimnasio': ['gimnasio', 'gym'],
        'Jardín': ['jardín', 'jardin', 'área verde'],
        'Seguridad': ['vigilancia', 'seguridad', 'privada'],
        'Estacionamiento': ['cochera', 'estacionamiento', 'garage'],
        'Casa club': ['casa club', 'club house'],
        'Juegos infantiles': ['juegos infantiles', 'área de juegos'],
        'Roof garden': ['roof garden', 'terraza común'],
        'Elevador': ['elevador', 'ascensor']
    }
    
    for amenidad, palabras in amenidades_buscar.items():
        if any(palabra in texto for palabra in palabras):
            amenidades.append(amenidad)
    
    return sorted(amenidades)

def main():
    """Función principal"""
    # Verificar sesión antes de continuar
    if not verificar_sesion():
        return
        
    print("\n1. Cargando repositorio maestro...")
    try:
        with open("resultados/repositorio_propiedades.json", "r", encoding="utf-8") as f:
            repositorio = json.load(f)
            print(f"   ✓ Repositorio cargado con {len(repositorio)} propiedades")
    except:
        print("   ✓ Creando nuevo repositorio")
        repositorio = {}
    
    print("\n2. Cargando enlaces a procesar...")
    try:
        with open("resultados/links/repositorio_unico.json", "r", encoding="utf-8") as f:
            links_raw = json.load(f)
            
        # Normalizar formato de links
        links = []
        BASE_URL = "https://www.facebook.com"
        for link in links_raw:
            if isinstance(link, str):
                url = BASE_URL + link if link.startswith("/") else link
                pid = link.rstrip("/").split("/")[-1]
                links.append({
                    "id": pid,
                    "link": url,
                    "ciudad": "cuernavaca"  # Ciudad por defecto
                })
            elif isinstance(link, dict):
                url = link.get("link", "")
                url = BASE_URL + url if url.startswith("/") else url
                links.append({
                    "id": link.get("id", url.rstrip("/").split("/")[-1]),
                    "link": url,
                    "ciudad": link.get("ciudad", "cuernavaca").lower()
                })
        
        print(f"   ✓ {len(links)} enlaces cargados")
        
        # Tomar solo 5 propiedades para prueba
        links = links[:5]
        print(f"   ✓ Procesando {len(links)} propiedades de prueba")
            
    except Exception as e:
        print(f"   ❌ Error cargando enlaces: {str(e)}")
        return
    
    # Crear directorios necesarios
    fecha_str = datetime.now().strftime("%Y-%m-%d")
    for dir_path in ["resultados/html", "resultados/json", "resultados/errores"]:
        os.makedirs(dir_path, exist_ok=True)
    
    # Procesar propiedades
    total = len(links)
    procesadas = 0
    errores = 0
    
    # Inicializar barra de progreso
    progress = ProgressBar(total, "Procesando propiedades", "propiedades")
    
    # Crear nuevo repositorio temporal
    nuevo_repositorio = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Navegador visible
            args=[
                '--start-maximized',  # Maximizar ventana
                '--disable-notifications',  # Desactivar notificaciones
                '--disable-popup-blocking'  # Permitir popups si son necesarios
            ]
        )
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            storage_state=ESTADO_FB if os.path.exists(ESTADO_FB) else None
        )
        page = context.new_page()
        
        # Configurar timeouts
        page.set_default_timeout(10000)  # 10 segundos máximo para operaciones
        page.set_default_navigation_timeout(15000)  # 15 segundos máximo para navegación
        
        # Procesar cada propiedad
        for item in links:
            try:
                resultado = procesar_propiedad(
                    page=page,
                    link=item["link"],
                    id_propiedad=item["id"],
                    ciudad=item["ciudad"],
                    fecha_str=fecha_str
                )
                
                if resultado:
                    # Guardar en el nuevo repositorio
                    nuevo_repositorio[item["id"]] = resultado
                    procesadas += 1
                    print("   ✓ Propiedad procesada exitosamente")
                else:
                    errores += 1
                    print("   ❌ Error procesando propiedad")
                    
                    # Si hay error, mantener los datos anteriores si existen
                    if item["id"] in repositorio:
                        nuevo_repositorio[item["id"]] = repositorio[item["id"]]
                    else:
                        nuevo_repositorio[item["id"]] = {
                            "id": item["id"],
                            "link": item["link"],
                            "titulo": "",
                            "descripcion": "",
                            "precio": {
                                "valor": 0,
                                "valor_normalizado": 0.0,
                                "moneda": "MXN",
                                "es_valido": False,
                                "error": None
                            },
                            "ubicacion": {
                                "ciudad": item["ciudad"],
                                "colonia": "",
                                "calle": "",
                                "referencias": [],
                                "coordenadas": {"latitud": None, "longitud": None}
                            },
                            "caracteristicas": {
                                "tipo_propiedad": "otro",
                                "tipo_operacion": "",
                                "recamaras": 0,
                                "banos": 0,
                                "estacionamiento": 0,
                                "metros_terreno": 0,
                                "metros_construccion": 0,
                                "niveles": 0,
                                "antiguedad": None,
                                "estado_conservacion": "No especificado"
                            },
                            "amenidades": [],
                            "estado_legal": {
                                "escrituras": False,
                                "cesion_derechos": False,
                                "creditos": False,
                                "constancia_posesion": False
                            },
                            "vendedor": {
                                "nombre": "",
                                "tipo": "particular",
                                "telefono": "",
                                "correo": ""
                            },
                            "imagenes": {
                                "portada": "",
                                "galeria": []
                            },
                            "metadata": {
                                "fecha_extraccion": datetime.now().isoformat(),
                                "ultima_actualizacion": datetime.now().isoformat(),
                                "fuente": "facebook_marketplace",
                                "status": "error",
                                "errores": ["Error al procesar la propiedad"],
                                "advertencias": []
                            }
                        }
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                traceback.print_exc()
                errores += 1
            
            # Actualizar progreso
            progress.update(1, procesadas, errores)
        
        # Cerrar navegador
        browser.close()
    
    # Cerrar barra de progreso
    progress.close()
    
    # Crear copia de respaldo del repositorio actual
    backup_path = "resultados/repositorio_propiedades.json.bak"
    if os.path.exists("resultados/repositorio_propiedades.json"):
        import shutil
        shutil.copy2("resultados/repositorio_propiedades.json", backup_path)
    
    # Actualizar repositorio con los nuevos datos
    for pid, datos in nuevo_repositorio.items():
        repositorio[pid] = datos
    
    # Guardar repositorio final
    with open("resultados/repositorio_propiedades.json", "w", encoding="utf-8") as f:
        json.dump(repositorio, f, indent=2, ensure_ascii=False)
    
    print("\n=== RESUMEN ===")
    print(f"Total de propiedades: {total}")
    print(f"Procesadas exitosamente: {procesadas}")
    print(f"Con errores: {errores}")
    print(f"Porcentaje de éxito: {(procesadas/total*100):.1f}%")
    print("\n✓ Proceso completado")

if __name__ == "__main__":
    main() 