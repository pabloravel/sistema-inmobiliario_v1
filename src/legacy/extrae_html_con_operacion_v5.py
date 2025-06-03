#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion_v5.py

Versión 5.0 - Mejoras en la extracción de datos
- Verificación y manejo de sesión de Facebook
- Mejor manejo de precios con soporte para millones y miles
- Patrones más flexibles para características
- Limpieza mejorada de ubicaciones
- Procesamiento por lotes de 10 propiedades
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
import shutil
import random

# ── Rutas y constantes ────────────────────────────────────────────────
CARPETA_LINKS = "resultados/links/repositorio_unico.json"
CARPETA_RESULTADOS = "resultados"
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
ESTADO_FB = "fb_state.json"
BASE_URL = "https://www.facebook.com"

# Barra de progreso mejorada
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

def verificar_sesion(page):
    """Verifica si la sesión de Facebook está activa"""
    try:
        # Intentar acceder a una página que requiere login
        page.goto(URL_TEST, timeout=30000)
        page.wait_for_timeout(2000)
        
        # Si encontramos el botón de login, la sesión no está activa
        login_button = page.locator('text="Log In"').first
        if login_button and login_button.is_visible():
            return False
            
        # Verificar si hay elementos que indican sesión activa
        try:
            # Buscar elementos típicos de Marketplace
            page.wait_for_selector('[aria-label="Marketplace"]', timeout=5000)
            return True
        except:
            return False
            
    except Exception as e:
        print(f"Error verificando sesión: {str(e)}")
        return False

def guardar_estado_sesion(context):
    """Guarda el estado de la sesión"""
    try:
        estado = context.storage_state()
        with open(ESTADO_FB, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
        print("✓ Estado de sesión guardado")
        return True
    except Exception as e:
        print(f"❌ Error guardando estado: {str(e)}")
        return False

def extraer_descripcion_estable(soup, page):
    """Extrae la descripción usando múltiples métodos"""
    # 1. Intentar expandir la descripción
    try:
        ver_mas = page.locator("text=Ver más").first
        if ver_mas and ver_mas.is_visible():
            ver_mas.click()
            page.wait_for_timeout(1000)
    except:
        pass
    
    # 2. Buscar en el HTML actualizado
    html = page.content()
    soup_actualizado = BeautifulSoup(html, "html.parser")
    
    # 3. Intentar diferentes métodos
    descripcion = ""
    
    # Método 1: Buscar después de "Descripción" o "Detalles"
    for div in soup_actualizado.find_all("div"):
        if div.get_text(strip=True) in ["Descripción", "Detalles"]:
            siguiente = div.find_next_sibling("div")
            if siguiente:
                descripcion = siguiente.get_text(separator="\n", strip=True)
                descripcion = descripcion.replace("Ver menos","").replace("Ver más","").strip()
                if descripcion:
                    return descripcion

    # Método 2: Buscar por data-testid
    try:
        desc = page.locator('[data-testid="marketplace_listing_item_description"]').inner_text()
        if desc:
            return desc.strip()
    except:
        pass

    # Método 3: Buscar en meta tags
    for meta in soup_actualizado.find_all("meta", {"property": ["og:description", "description"]}):
        if contenido := meta.get("content", "").strip():
            return contenido
            
    # Método 4: Buscar en divs con texto largo
    for div in soup_actualizado.find_all("div"):
        texto = div.get_text(strip=True)
        # Si es un texto largo y no parece ser un menú o UI
        if len(texto) > 100 and not any(x in texto.lower() for x in ["enviar mensaje", "marketplace", "facebook"]):
            return texto

    return descripcion

def extraer_precio_mejorado(soup):
    """Extrae y normaliza el precio"""
    precio = {
        "valor": 0,
        "valor_normalizado": 0.0,
        "moneda": "MXN",
        "es_valido": False,
        "error": None
    }
    
    def normalizar_precio(texto):
        """Normaliza un texto de precio a un número"""
        # Eliminar símbolos de moneda y espacios
        valor = texto.replace("$", "").replace(" ", "")
        
        # Si usa puntos como separador de miles (ej: 2.850.000)
        if valor.count(".") > 1:
            valor = valor.replace(".", "")
        
        # Si usa coma como separador decimal
        if "," in valor:
            valor = valor.replace(",", ".")
            
        try:
            precio_num = float(valor)
            # Si el precio es muy bajo para una propiedad, multiplicar por 1000
            if precio_num < 10000:
                precio_num *= 1000
            return precio_num
        except:
            return None
    
    # Buscar precio en el texto
    texto_completo = soup.get_text(" ", strip=True)
    
    # Patrones de precio
    patrones = [
        r'\$[\d\.,]+(?:[\d\.,]*\d)?(?:\s*(?:mil|millones))?',  # Precio normal
        r'(?:precio|costo|valor)[\s:]*\$[\d\.,]+(?:[\d\.,]*\d)?',  # Precio con etiqueta
        r'[\d\.,]+(?:[\d\.,]*\d)?\s*(?:mil|millones)\s*(?:de)?\s*pesos'  # Precio en texto
    ]
    
    for patron in patrones:
        matches = re.findall(patron, texto_completo, re.I)
        for match in matches:
            # Limpiar el texto del precio
            precio_texto = re.sub(r'[^\d\.,]', '', match)
            if precio_num := normalizar_precio(precio_texto):
                # Ajustar por mil/millones
                if "millones" in match.lower():
                    precio_num *= 1_000_000
                elif "mil" in match.lower():
                    precio_num *= 1_000
                
                precio["valor"] = precio_num
                precio["valor_normalizado"] = precio_num
                precio["es_valido"] = True
                return precio
    
    return precio

def detectar_tipo_propiedad(texto, titulo=""):
    """Detecta el tipo de propiedad basado en el texto y título"""
    texto = (texto + " " + titulo).lower()
    
    # Mapeo de tipos de propiedad y sus palabras clave
    tipos = {
        "terreno": [
            "terreno", "lote", "predio", "solar",
            "terreno habitacional", "terreno comercial",
            "m²", "metros cuadrados", "mts2"
        ],
        "departamento": [
            "departamento", "depto", "dpto", "apartamento",
            "flat", "penthouse", "pent house", "loft",
            "condominio", "torre", "unidad"
        ],
        "casa": [
            "casa sola", "casa habitación", "casa en privada",
            "residencia", "chalet", "villa", "casa"
        ],
        "local": [
            "local", "local comercial", "plaza comercial",
            "bodega comercial", "oficina comercial"
        ],
        "oficina": [
            "oficina", "despacho", "consultorio",
            "suite ejecutiva", "espacio de trabajo"
        ],
        "bodega": [
            "bodega", "almacén", "almacen", "nave industrial",
            "galpón", "galpon"
        ],
        "edificio": [
            "edificio", "inmueble completo", "construcción completa",
            "propiedad vertical"
        ]
    }
    
    # Primero buscar en el título
    for tipo, palabras in tipos.items():
        if any(palabra in titulo.lower() for palabra in palabras):
            return tipo.capitalize()
    
    # Si no se encuentra en el título, buscar en el texto completo
    for tipo, palabras in tipos.items():
        if any(palabra in texto for palabra in palabras):
            return tipo.capitalize()
    
    return "Otro"

def extraer_caracteristicas(soup):
    """Extrae características de la propiedad"""
    caracteristicas = {
        "tipo_propiedad": "",
        "tipo_operacion": "",
        "recamaras": 0,
        "banos": 0,
        "estacionamiento": 0,
        "metros_terreno": 0,
        "metros_construccion": 0,
        "niveles": 0,
        "antiguedad": None,
        "estado_conservacion": "No especificado",
        "caracteristicas_adicionales": []
    }
    
    texto = soup.get_text(" ", strip=True).lower()
    
    # Detectar tipo de propiedad
    caracteristicas["tipo_propiedad"] = detectar_tipo_propiedad(texto)
    
    # Extraer números con patrones mejorados
    patrones = {
        "recamaras": [
            r"(\d+)\s*rec[áa]maras?",
            r"(\d+)\s*habitaciones?",
            r"(\d+)\s*dormitorios?",
            r"rec[áa]maras?:?\s*(\d+)"
        ],
        "banos": [
            r"(\d+)\s*ba[ñn]os?",
            r"(\d+)\s*wc",
            r"ba[ñn]os?:?\s*(\d+)"
        ],
        "estacionamiento": [
            r"(\d+)\s*(?:cajones?|lugares?)\s*(?:de)?\s*estacionamiento",
            r"(\d+)\s*autos?",
            r"cochera\s*(?:para)?\s*(\d+)",
            r"estacionamiento\s*(?:para)?\s*(\d+)",
            r"garage\s*(?:para)?\s*(\d+)",
            r"grage\s*(?:para)?\s*(\d+)"
        ]
    }
    
    # Patrones específicos para metros cuadrados
    patrones_metros = {
        "metros_terreno": [
            r"terreno:?\s*([\d,\.]+)\s*(?:m2|mts?2?|metros?2?|m²|mt)",
            r"superficie:?\s*([\d,\.]+)\s*(?:m2|mts?2?|metros?2?|m²|mt)",
            r"([\d,\.]+)\s*(?:m2|mts?2?|metros?2?|m²|mt)\s*(?:de)?\s*terreno",
            r"lote\s*(?:de)?\s*([\d,\.]+)\s*(?:m2|mts?2?|metros?2?|m²|mt)",
            r"terreno\s*(?:de)?\s*([\d,\.]+)\s*(?:m2|mts?2?|metros?2?|m²|mt)",
            r"([\d,\.]+)\s*mt(?:\s+terreno)?",
            r"([\d,\.]+)\s*m²(?:\s+terreno)?"
        ],
        "metros_construccion": [
            r"construcci[óo]n:?\s*([\d,\.]+)\s*(?:m2|mts?2?|metros?2?|m²|mc)",
            r"construidos?:?\s*([\d,\.]+)\s*(?:m2|mts?2?|metros?2?|m²|mc)",
            r"([\d,\.]+)\s*(?:m2|mts?2?|metros?2?|m²|mc)\s*(?:de)?\s*construcci[óo]n",
            r"área\s*construida:?\s*([\d,\.]+)\s*(?:m2|mts?2?|metros?2?|m²|mc)",
            r"([\d,\.]+)\s*mc(?:\s+construccion)?",
            r"([\d,\.]+)\s*m²(?:\s+construccion)?"
        ]
    }
    
    # Aplicar patrones básicos
    for campo, lista_patrones in patrones.items():
        for patron in lista_patrones:
            if match := re.search(patron, texto):
                try:
                    caracteristicas[campo] = int(match.group(1))
                    break
                except:
                    continue
    
    # Aplicar patrones de metros cuadrados
    for campo, lista_patrones in patrones_metros.items():
        for patron in lista_patrones:
            if match := re.search(patron, texto):
                try:
                    # Limpiar el valor de comas y puntos
                    valor_str = match.group(1).replace(",", "").replace(".", "")
                    valor = int(valor_str)
                    # Validar rangos razonables
                    if campo == "metros_terreno" and 20 <= valor <= 100000:
                        caracteristicas[campo] = valor
                        break
                    elif campo == "metros_construccion" and 20 <= valor <= 2000:
                        caracteristicas[campo] = valor
                        break
                except:
                    continue
    
    # Extraer antigüedad
    patrones_antiguedad = [
        (r"(\d+)\s*años?\s*(?:de\s*)?(?:antiguedad|antigüedad|construcción|construccion)", "años"),
        (r"(?:construi[td][oa]|terminad[oa])\s*(?:en|el)?\s*(?:año|ano)?\s*(\d{4})", "año"),
        (r"(?:nueva|nuevo|estrenar|recién\s*construida)", "nueva")
    ]
    
    for patron, tipo in patrones_antiguedad:
        if match := re.search(patron, texto):
            if tipo == "años":
                caracteristicas["antiguedad"] = f"{match.group(1)} años"
            elif tipo == "año":
                año_actual = datetime.now().year
                años = año_actual - int(match.group(1))
                caracteristicas["antiguedad"] = f"{años} años"
            else:
                caracteristicas["antiguedad"] = "Nueva"
            break
    
    # Extraer estado de conservación
    estados = {
        "Excelente": ["excelente", "impecable", "como nueva", "remodelada"],
        "Bueno": ["buen estado", "bien conservada", "en orden"],
        "Regular": ["regular", "necesita mantenimiento", "algunos detalles"],
        "Para remodelar": ["remodelar", "renovar", "actualizar", "fixer upper"]
    }
    
    for estado, palabras in estados.items():
        if any(palabra in texto for palabra in palabras):
            caracteristicas["estado_conservacion"] = estado
            break
    
    # Características adicionales
    caracteristicas_buscar = {
        "Cocina integral": [
            "cocina integral", "cocina equipada",
            "cocina con alacena", "cocina con barra",
            "cosina equipada", "cosina integral"
        ],
        "Closets": [
            "closets", "clósets", "vestidor",
            "walk in closet", "closet de blancos"
        ],
        "Aire acondicionado": [
            "aire acondicionado", "minisplit", "clima",
            "climatización", "a/c"
        ],
        "Calefacción": [
            "calefacción", "calefaccion", "caldera",
            "calentador", "boiler"
        ],
        "Cisterna": [
            "cisterna", "aljibe", "tanque de agua",
            "almacenamiento de agua", "cisterna de"
        ],
        "Tinaco": [
            "tinaco", "tanque elevado", "depósito de agua"
        ],
        "Bodega": [
            "bodega", "cuarto de guardado", "storage",
            "área de almacenamiento"
        ],
        "Cuarto de servicio": [
            "cuarto de servicio", "habitación de servicio",
            "cuarto de empleada", "área de servicio"
        ],
        "Cuarto de lavado": [
            "cuarto de lavado", "área de lavado",
            "lavandería", "centro de lavado"
        ],
        "Instalaciones especiales": [
            "instalación para minisplit",
            "instalaciones eléctricas nuevas",
            "cableado estructurado",
            "sistema hidroneumático",
            "planta de luz",
            "instalación de gas",
            "instalaciones ocultas",
            "gas estacionario"
        ],
        "Acabados de lujo": [
            "pisos de mármol", "cantera", "granito",
            "madera sólida", "importado", "porcelanato",
            "acabados de primera"
        ],
        "Equipamiento": [
            "paneles solares", "sistema de riego",
            "filtro de agua", "suavizador",
            "interfón", "portón eléctrico",
            "mosquiteros", "persianas"
        ],
        "Recámara en planta baja": [
            "recámara en planta baja", "recámara en pb",
            "habitación en planta baja"
        ]
    }
    
    for caracteristica, palabras in caracteristicas_buscar.items():
        if any(palabra in texto for palabra in palabras):
            caracteristicas["caracteristicas_adicionales"].append(caracteristica)
    
    # Eliminar duplicados manteniendo el orden
    caracteristicas["caracteristicas_adicionales"] = list(dict.fromkeys(caracteristicas["caracteristicas_adicionales"]))
    
    return caracteristicas

def limpiar_referencias(referencias):
    """Limpia y normaliza las referencias de ubicación"""
    referencias_limpias = []
    
    # Palabras y patrones a filtrar
    filtros = [
        r"(?i)envía(?:\s+un)?\s+mensaje",
        r"(?i)hola\.\s*¿sigue\s+(?:estando\s+)?disponible\?",
        r"(?i)ver\s+(?:más|menos)",
        r"(?i)descripción",
        r"(?i)categorías",
        r"(?i)sugerencias",
        r"(?i)publicidad",
        r"(?i)detalles del vendedor",
        r"(?i)calificación",
        r"(?i)se unió a facebook",
        r"(?i)reporta esta publicación",
        r"(?i)al vendedor",
        r"(?i)enviar",
        r"{.*?}",  # Eliminar objetos JSON
        r"\$[\d,\.]+",  # Eliminar precios
        r"·\d+\s*km",  # Eliminar distancias
        r"\d+\s*mil\s*km",  # Eliminar kilometrajes
        r"(?i)marketplace",
        r"(?i)en un radio de \d+ km",
        r"\.{3}$"  # Eliminar puntos suspensivos al final
    ]
    
    for ref in referencias:
        # Saltar referencias vacías o muy largas
        if not ref or len(ref) > 200:
            continue
            
        # Aplicar filtros
        ref_limpia = ref
        for filtro in filtros:
            ref_limpia = re.sub(filtro, "", ref_limpia)
        
        # Limpiar espacios y caracteres especiales
        ref_limpia = re.sub(r"\s+", " ", ref_limpia).strip()
        
        # Validar referencia limpia
        if ref_limpia and len(ref_limpia) > 3 and not ref_limpia.isdigit():
            # Verificar que no sea el inicio de la descripción
            if not any(x in ref_limpia.lower() for x in ["venta de", "renta de", "se vende", "se renta"]):
                referencias_limpias.append(ref_limpia)
    
    # Eliminar duplicados manteniendo el orden
    return list(dict.fromkeys(referencias_limpias))

def extraer_datos_vendedor(soup, page):
    """Extrae información del vendedor"""
    vendedor = {
        "nombre": "",
        "tipo": "desconocido",
        "telefono": "",
        "correo": "",
        "perfil": "",
        "calificacion": None,
        "antiguedad": None
    }
    
    try:
        # Buscar nombre y perfil del vendedor
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "facebook.com/profile.php?id=" in href or re.search(r"facebook\.com/[^/]+$", href):
                vendedor["perfil"] = href.split("?")[0]
                if strong := a.find("strong"):
                    vendedor["nombre"] = strong.get_text(strip=True)
                elif span := a.find("span"):
                    vendedor["nombre"] = span.get_text(strip=True)
                else:
                    vendedor["nombre"] = a.get_text(strip=True)
                break
        
        # Determinar tipo de vendedor
        nombre = vendedor["nombre"].lower()
        if any(x in nombre for x in ["inmobiliaria", "bienes raices", "broker", "asesor", "real estate"]):
            vendedor["tipo"] = "inmobiliaria"
        elif vendedor["perfil"] and "profile.php?id=" not in vendedor["perfil"]:
            vendedor["tipo"] = "inmobiliaria"
        else:
            vendedor["tipo"] = "particular"
        
        # Buscar calificación
        texto = soup.get_text(" ", strip=True).lower()
        if match := re.search(r"calificación\s*(?:alta|media|baja)", texto):
            vendedor["calificacion"] = match.group(0)
        
        # Buscar antigüedad
        if match := re.search(r"se\s+unió\s+(?:a\s+facebook\s+)?en\s+(\d{4})", texto):
            vendedor["antiguedad"] = match.group(1)
        
    except Exception as e:
        print(f"Error extrayendo datos del vendedor: {str(e)}")
    
    return vendedor

def extraer_ubicacion_mejorada(soup):
    """Extrae información de ubicación"""
    ubicacion = {
        "ciudad": "",
        "colonia": "",
        "calle": "",
        "referencias": [],
        "cerca_de": [],
        "coordenadas": {
            "latitud": None,
            "longitud": None
        }
    }
    
    texto = soup.get_text(" ", strip=True).lower()
    
    # Buscar ubicación en el texto
    for div in soup.find_all("div"):
        texto_div = div.get_text(strip=True).lower()
        if "ubicación" in texto_div or "dirección" in texto_div:
            if siguiente := div.find_next_sibling():
                ubicacion["referencias"].append(siguiente.get_text(strip=True))
    
    # Limpiar referencias
    ubicacion["referencias"] = limpiar_referencias(ubicacion["referencias"])
    
    # Detectar colonia
    colonias_conocidas = {
        "ahuatepec": ["ahuatepec", "ahuat"],
        "acapantzingo": ["acapantzingo", "acapant"],
        "bellavista": ["bella vista", "bellavista"],
        "buenavista": ["buena vista", "buenavista"],
        "chapultepec": ["chapultepec", "chapul"],
        "delicias": ["delicias"],
        "flores magón": ["flores magon", "magón"],
        "gualupita": ["gualupita"],
        "la pradera": ["pradera"],
        "las palmas": ["palmas"],
        "lomas": ["lomas de", "lomas del"],
        "ocotepec": ["ocotepec"],
        "palmira": ["palmira"],
        "reforma": ["reforma"],
        "san antón": ["san anton", "san antón"],
        "san cristóbal": ["san cristobal", "san cristóbal"],
        "san jerónimo": ["san jeronimo", "san jerónimo"],
        "san miguel acapantzingo": ["san miguel acapantzingo"],
        "santa maría": ["santa maria", "santa maría"],
        "tlaltenango": ["tlaltenango"],
        "vista hermosa": ["vista hermosa", "vistahermosa"]
    }
    
    # Buscar colonia en el texto
    for colonia, variantes in colonias_conocidas.items():
        if any(variante in texto for variante in variantes):
            ubicacion["colonia"] = colonia.title()
            break
    
    # Si no se encontró colonia, buscar patrones comunes
    if not ubicacion["colonia"]:
        patrones_colonia = [
            r"col(?:onia)?\.?\s+([^,\.]+)",
            r"fracc?\.?\s+([^,\.]+)",
            r"unidad\s+([^,\.]+)",
            r"residencial\s+([^,\.]+)",
            r"en\s+([^,\.]+?)(?:\s+(?:cuernavaca|morelos))",
            r"ubicad[oa]\s+en\s+([^,\.]+)"
        ]
        
        for patron in patrones_colonia:
            if match := re.search(patron, texto, re.I):
                colonia = match.group(1).strip()
                # Filtrar referencias no válidas
                if len(colonia) > 3 and not any(x in colonia.lower() for x in ["urgente", "barata", "venta", "renta"]):
                    ubicacion["colonia"] = colonia.title()
                    break
    
    # Extraer referencias cercanas
    lugares_conocidos = {
        "comercial": [
            "plaza", "centro comercial", "mall", "tienda departamental",
            "supermercado", "mercado", "tianguis", "comercial"
        ],
        "educación": [
            "escuela", "colegio", "universidad", "instituto",
            "preparatoria", "secundaria", "primaria", "kinder"
        ],
        "salud": [
            "hospital", "clínica", "centro médico", "consultorio",
            "farmacia", "cruz roja"
        ],
        "transporte": [
            "parada", "estación", "terminal", "central",
            "base", "taxi", "ruta"
        ],
        "recreación": [
            "parque", "jardín", "deportivo", "unidad deportiva",
            "gimnasio", "alberca", "cancha"
        ],
        "servicios": [
            "banco", "cajero", "correos", "oficina gubernamental",
            "palacio municipal", "registro civil"
        ]
    }
    
    for categoria, lugares in lugares_conocidos.items():
        for lugar in lugares:
            if lugar in texto:
                ubicacion["cerca_de"].append(f"{categoria.title()}: {lugar.title()}")
    
    # Eliminar duplicados manteniendo el orden
    ubicacion["cerca_de"] = list(dict.fromkeys(ubicacion["cerca_de"]))
    
    return ubicacion

def extraer_amenidades(soup):
    """Extrae amenidades mencionadas"""
    texto = soup.get_text(" ", strip=True).lower()
    amenidades = []
    
    # Lista de amenidades comunes
    buscar = {
        "Alberca": [
            "alberca", "piscina", "pool", "chapoteadero",
            "jacuzzi", "spa", "hidromasaje"
        ],
        "Gimnasio": [
            "gimnasio", "gym", "área de ejercicio",
            "sala de ejercicio", "equipo de ejercicio"
        ],
        "Casa club": [
            "casa club", "club house", "salón de eventos",
            "salón de fiestas", "área social", "área común"
        ],
        "Jardín": [
            "jardín", "jardin", "áreas verdes", "area verde",
            "jardines", "vegetación", "paisajismo"
        ],
        "Seguridad": [
            "vigilancia", "seguridad", "privada", "24/7",
            "24 horas", "cerca electrificada", "cámaras",
            "caseta de vigilancia", "acceso controlado"
        ],
        "Roof garden": [
            "roof garden", "rooftop", "terraza",
            "sky garden", "jardín en azotea"
        ],
        "Área de juegos": [
            "juegos infantiles", "área infantil",
            "parque infantil", "playground",
            "área de niños", "zona de juegos"
        ],
        "Elevador": [
            "elevador", "ascensor", "lift"
        ],
        "Estacionamiento techado": [
            "estacionamiento techado", "cochera techada",
            "garage techado", "carport"
        ],
        "Áreas deportivas": [
            "cancha", "court", "campo deportivo",
            "área deportiva", "zona deportiva"
        ],
        "Salón de usos múltiples": [
            "salón de usos múltiples", "sum", "salón multiusos",
            "área de eventos", "centro de reuniones"
        ],
        "Business center": [
            "business center", "centro de negocios",
            "sala de juntas", "coworking"
        ],
        "Área de asadores": [
            "asadores", "área de bbq", "zona de barbacoa",
            "parrilla", "grill"
        ],
        "Lobby": [
            "lobby", "recepción", "área de recepción",
            "vestíbulo", "entrada principal"
        ]
    }
    
    # Buscar amenidades en el texto
    for amenidad, palabras in buscar.items():
        if any(palabra in texto for palabra in palabras):
            amenidades.append(amenidad)
    
    # Eliminar duplicados manteniendo el orden
    return list(dict.fromkeys(amenidades))

def extraer_estado_legal(soup):
    """Extrae información sobre el estado legal de la propiedad"""
    texto = soup.get_text(" ", strip=True).lower()
    
    estado = {
        "escrituras": False,
        "cesion_derechos": False,
        "creditos": False,
        "constancia_posesion": False
    }
    
    # Patrones para cada estado
    patrones = {
        "escrituras": [
            r"(?:con|tiene)\s+escrituras?",
            r"escrituras?\s+(?:en\s+)?(?:regla|orden)",
            r"escrituras?\s+p[úu]blicas?",
            r"libre\s+de\s+gravamen"
        ],
        "cesion_derechos": [
            r"cesi[óo]n\s+(?:de\s+)?derechos",
            r"derechos\s+(?:de\s+)?posesi[óo]n",
            r"traspaso\s+(?:de\s+)?derechos",
            r"derechos\s+ejidales"
        ],
        "creditos": [
            r"acepta\s+cr[ée]ditos?",
            r"cr[ée]dito\s+(?:bancario|hipotecario|infonavit|fovissste)",
            r"cr[ée]ditos?\s+disponibles?",
            r"financiamiento\s+bancario"
        ],
        "constancia_posesion": [
            r"constancia\s+(?:de\s+)?posesi[óo]n",
            r"documento\s+(?:de\s+)?posesi[óo]n",
            r"posesi[óo]n\s+legal",
            r"posesi[óo]n\s+(?:en\s+)?regla"
        ]
    }
    
    # Verificar cada patrón
    for campo, lista_patrones in patrones.items():
        estado[campo] = any(re.search(patron, texto) for patron in lista_patrones)
    
    return estado

def extraer_info_descripcion(descripcion):
    """
    Extrae información estructurada de la descripción
    """
    info = {
        "caracteristicas_adicionales": [],
        "metros_construccion": 0,
        "metros_terreno": 0,
        "recamaras": 0,
        "banos": 0,
        "estacionamiento": 0,
        "niveles": 0,
        "amenidades": [],
        "estado_legal": {
            "escrituras": False,
            "cesion_derechos": False,
            "creditos": False
        },
        "ubicacion": {
            "referencias": [],
            "cerca_de": []
        }
    }
    
    texto = descripcion.lower()
    
    # Extraer metros
    patrones_metros = [
        (r"(?:construcción|construccion)\s*(?:de)?\s*(\d+)\s*(?:m2|metros?(?:\s+cuadrados)?)", "metros_construccion"),
        (r"(\d+)\s*(?:m2|metros?(?:\s+cuadrados)?)\s*(?:de)?\s*(?:construcción|construccion)", "metros_construccion"),
        (r"(?:terreno|lote)\s*(?:de)?\s*(\d+)\s*(?:m2|metros?(?:\s+cuadrados)?)", "metros_terreno"),
        (r"(\d+)\s*(?:m2|metros?(?:\s+cuadrados)?)\s*(?:de)?\s*(?:terreno|lote)", "metros_terreno")
    ]
    
    for patron, campo in patrones_metros:
        if match := re.search(patron, texto):
            info[campo] = int(match.group(1))
    
    # Extraer recámaras
    if match := re.search(r"(\d+)\s*(?:rec[áa]maras?|habitaciones?|dormitorios?)", texto):
        info["recamaras"] = int(match.group(1))
    
    # Extraer baños
    if match := re.search(r"(\d+)\s*(?:baños?|banos?)", texto):
        info["banos"] = int(match.group(1))
    
    # Extraer estacionamiento
    numeros_texto = {
        'un': 1, 'uno': 1, 'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
        'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10
    }
    
    # Buscar número de estacionamientos
    for linea in texto.split('\n'):
        # Buscar números escritos
        for num_texto, valor in numeros_texto.items():
            if f"{num_texto} estacionamiento" in linea or f"{num_texto} cajones" in linea:
                info["estacionamiento"] = valor
                break
        
        # Buscar números en dígitos
        if match := re.search(r"(\d+)\s*(?:cajones?|lugares?|espacios?)\s*(?:de)?\s*estacionamiento", linea):
            info["estacionamiento"] = int(match.group(1))
            break
    
    # Si no se encontró número pero se menciona estacionamiento
    if info["estacionamiento"] == 0 and ("estacionamiento" in texto or "cochera" in texto):
        info["estacionamiento"] = 1
    
    # Extraer niveles
    niveles_palabras = ["nivel", "piso", "planta"]
    max_nivel = 0
    numeros_texto_niveles = {
        'primer': 1, 'primero': 1, 'segundo': 2, 'tercer': 3, 'tercero': 3,
        'cuarto': 4, 'quinto': 5, 'sexto': 6
    }
    
    # Buscar niveles en el texto
    patrones_niveles = [
        r"(?:casa|propiedad)\s+(?:de|con)\s+(\d+)\s*niveles?",
        r"(\d+)\s*niveles?",
        r"(\d+)\s*plantas?"
    ]
    
    for patron in patrones_niveles:
        if match := re.search(patron, texto):
            max_nivel = max(max_nivel, int(match.group(1)))
    
    # Buscar por palabras
    for linea in texto.split('\n'):
        # Buscar números ordinales escritos
        for num_texto, valor in numeros_texto_niveles.items():
            if any(f"{num_texto} {palabra}" in linea for palabra in niveles_palabras):
                max_nivel = max(max_nivel, valor)
        
        # Buscar números en dígitos
        for palabra in niveles_palabras:
            if match := re.search(rf"(\d+)(?:er|do|to|°)?\s*{palabra}", linea):
                nivel = int(match.group(1))
                max_nivel = max(max_nivel, nivel)
    
    if max_nivel > 0:
        info["niveles"] = max_nivel
    
    # Buscar amenidades
    amenidades_buscar = {
        "Alberca": ["alberca", "piscina"],
        "Gimnasio": ["gimnasio", "gym"],
        "Casa club": ["casa club", "club house", "salón de eventos"],
        "Jardín": ["jardín", "jardin", "áreas verdes", "area verde"],
        "Seguridad": ["vigilancia", "seguridad", "privada", "24/7", "24 horas", "cerca electrificada"],
        "Roof garden": ["roof garden", "rooftop", "terraza"],
        "Área de juegos": ["juegos infantiles", "área infantil", "parque infantil"],
        "Elevador": ["elevador", "ascensor"],
        "Estacionamiento techado": ["estacionamiento techado", "cochera techada"]
    }
    
    for amenidad, palabras in amenidades_buscar.items():
        if any(palabra in texto for palabra in palabras):
            info["amenidades"].append(amenidad)
    
    # Buscar características adicionales
    caracteristicas_buscar = [
        "cocina integral",
        "cocina equipada",
        "closets",
        "aire acondicionado",
        "calefacción",
        "cisterna",
        "tinaco",
        "bodega",
        "cuarto de servicio",
        "patio de servicio",
        "portón eléctrico",
        "porton electrico",
        "hidroneumático",
        "hidroneum[aá]tico",
        "fosa s[ée]ptica",
        "vestidor",
        "almacén",
        "almacen",
        "despensa"
    ]
    
    for caract in caracteristicas_buscar:
        if re.search(caract, texto, re.I):
            info["caracteristicas_adicionales"].append(caract.title())
    
    # Estado legal
    info["estado_legal"].update({
        "escrituras": any(x in texto for x in [
            "escrituras", "escriturada", "escritura pública", "escritura publica",
            "papeleo en orden", "documentación en regla", "documentacion en regla"
        ]),
        "cesion_derechos": any(x in texto for x in ["cesión", "cesion de derechos"]),
        "creditos": any(x in texto for x in [
            "crédito", "credito", "infonavit", "fovissste", 
            "bancario", "hipotecario", "issfam", "aplica para crédito"
        ])
    })
    
    # Extraer ubicación y referencias
    cerca_de = []
    for linea in descripcion.split('\n'):
        linea = linea.strip().lower()
        if any(x in linea for x in ["cerca de", "a unos pasos", "junto a", "frente a"]):
            cerca_de.append(linea.strip())
        elif "ubicad" in linea:
            info["ubicacion"]["referencias"].append(linea.strip())
    
    if cerca_de:
        info["ubicacion"]["cerca_de"] = cerca_de
    
    return info

def detectar_tipo_operacion(texto, titulo="", precio_str=""):
    """Detecta si es venta o renta"""
    texto = (texto + " " + titulo + " " + precio_str).lower()
    
    # Palabras clave para cada tipo
    palabras_renta = [
        "renta", "alquiler", "arrendamiento",
        "/mes", "mensual", "por mes",
        "rentar", "alquilar", "arrendar"
    ]
    
    palabras_venta = [
        "venta", "vendo", "remato",
        "oportunidad", "urge vender",
        "escrituras", "cesión"
    ]
    
    # Primero buscar en el texto
    if any(palabra in texto for palabra in palabras_renta):
        return "Renta"
    if any(palabra in texto for palabra in palabras_venta):
        return "Venta"
    
    # Si no se encuentra, inferir por el precio
    try:
        precio = float(''.join(filter(str.isdigit, precio_str)))
        if precio >= 300000:  # Umbral para considerar venta
            return "Venta"
        elif 1000 <= precio < 100000:  # Rango típico de rentas
            return "Renta"
    except:
        pass
    
    return "Desconocido"

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
    print(f"\nProcesando {id_propiedad} - {link}")
    t0 = time.time()
    
    # Crear directorios necesarios
    carpeta = os.path.join(CARPETA_RESULTADOS, fecha_str)
    os.makedirs(carpeta, exist_ok=True)
    
    try:
        # Navegar y esperar carga
        page.goto(link, timeout=60000)
        page.wait_for_timeout(3000)
        
        # Verificar estado de la publicación
        estado = detectar_estado_publicacion(soup, page)
        if not estado["disponible"]:
            datos = {
                "id": id_propiedad,
                "link": link,
                "metadata": {
                    "fecha_extraccion": datetime.now().isoformat(),
                    "ultima_actualizacion": datetime.now().isoformat(),
                    "fuente": "facebook_marketplace",
                    "status": "no_disponible",
                    "motivo": estado["motivo"],
                    "fecha_cambio": estado["fecha_cambio"]
                }
            }
            # Guardar JSON con estado
            ruta_json = os.path.join(carpeta, f"{ciudad}-{fecha_str}-{id_propiedad}.json")
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            print(f"   ! Propiedad no disponible: {estado['motivo']}")
            return datos
        
        # Obtener HTML y crear soup
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Extraer datos básicos
        titulo = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
        descripcion = extraer_descripcion_estable(soup, page)
        precio = extraer_precio_mejorado(soup)
        vendedor = extraer_datos_vendedor(soup, page)
        img_portada = descargar_imagen_por_playwright(page, ciudad, id_propiedad, carpeta, fecha_str)
        
        # Extraer características usando el título
        caracteristicas = extraer_caracteristicas(soup)
        caracteristicas["tipo_propiedad"] = detectar_tipo_propiedad(descripcion, titulo)
        caracteristicas["tipo_operacion"] = detectar_tipo_operacion(
            descripcion, titulo, str(precio.get("valor", ""))
        )
        
        # Extraer otros datos
        ubicacion = extraer_ubicacion_mejorada(soup)
        ubicacion["ciudad"] = ciudad  # Asegurar que se use la ciudad proporcionada
        amenidades = extraer_amenidades(soup)
        estado_legal = extraer_estado_legal(soup)
        
        # Construir datos en el formato correcto
        datos = {
            "id": id_propiedad,
            "link": link,
            "titulo": titulo,
            "descripcion": descripcion,
            "precio": precio,
            "ubicacion": ubicacion,
            "caracteristicas": caracteristicas,
            "amenidades": amenidades,
            "estado_legal": estado_legal,
            "vendedor": vendedor,
            "imagenes": {
                "portada": img_portada,
                "galeria": []
            },
            "metadata": {
                "fecha_extraccion": datetime.now().isoformat(),
                "ultima_actualizacion": datetime.now().isoformat(),
                "fuente": "facebook_marketplace",
                "status": "completo",
                "errores": [],
                "advertencias": []
            }
        }
        
        # Validar datos
        if not titulo or not descripcion:
            datos["metadata"]["status"] = "error"
            if not titulo:
                datos["metadata"]["errores"].append("Falta el campo requerido: titulo")
            if not descripcion:
                datos["metadata"]["errores"].append("Falta el campo requerido: descripcion")
        
        # Guardar archivos
        guardar_html_y_json(html, datos, ciudad, id_propiedad, carpeta, fecha_str)
        
        print(f"   ✓ Datos extraídos en {time.time() - t0:.1f}s")
        return datos
        
    except PlaywrightTimeout:
        print(f"   ! Timeout al cargar la página ({time.time() - t0:.1f}s)")
        return None
    except Exception as e:
        print(f"   ! Error procesando propiedad: {str(e)}")
        return None

def guardar_html_y_json(html, datos, ciudad, id_propiedad, carpeta_base, fecha_str):
    """Guarda el HTML y los datos JSON de una propiedad"""
    try:
        # Construir nombres de archivo
        filename_base = f"{ciudad}-{fecha_str}-{id_propiedad}"
        
        # Guardar en la carpeta de datos por fecha
        carpeta_datos = os.path.join(carpeta_base, fecha_str)
        
        # Guardar HTML
        filename_html = filename_base + ".html"
        path_html = os.path.join(carpeta_datos, filename_html)
        with open(path_html, "w", encoding="utf-8") as f:
        f.write(html)
            
        # Guardar JSON
        filename_json = filename_base + ".json"
        path_json = os.path.join(carpeta_datos, filename_json)
        with open(path_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

        return True
        
    except Exception as e:
        print(f"Error guardando archivos: {str(e)}")
        return False

def descargar_imagen_por_playwright(page, ciudad, pid, carpeta_base, date_str):
    """Descarga la imagen de portada usando Playwright"""
    try:
        # Intentar obtener la imagen de portada
        src = None
        try:
            src = page.locator('img[alt^="Foto de"]').first.get_attribute('src')
        except:
            try:
                src = page.locator('img').first.get_attribute('src')
            except:
                return ""
                
        if not src or not src.startswith("http"):
            return ""
            
        # Construir estructura de carpetas
        carpeta_ciudad = os.path.join(carpeta_base, "imagenes", ciudad.lower(), date_str)
        os.makedirs(carpeta_ciudad, exist_ok=True)
            
        # Construir nombre de archivo
        filename = f"propiedad-{pid}.jpg"
        path_img = os.path.join(carpeta_ciudad, filename)
        
        # Descargar imagen
        try:
            resp = requests.get(src, timeout=10)
            if resp.status_code == 200:
                with open(path_img, "wb") as f:
                    f.write(resp.content)
                return os.path.join("imagenes", ciudad.lower(), date_str, filename)
        except:
            pass
            
        return ""
        
    except Exception as e:
        print(f"Error descargando imagen: {str(e)}")
        return ""

def main():
    """Función principal del script"""
    # 1) Maestro previo
    data_master = {}
    if os.path.exists(CARPETA_REPO_MASTER):
        with open(CARPETA_REPO_MASTER, "r", encoding="utf-8") as f:
            data_master = json.load(f)
    existing_ids = set(data_master.keys())
    print(f"Repositorio maestro cargado con {len(data_master)} propiedades")

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

    # 3) Filtra pendientes y no disponibles
    pending = []
    no_disponibles = []
    for link in links:
        pid = link["id"]
        if pid not in existing_ids:
            pending.append(link)
        elif data_master[pid].get("metadata", {}).get("status") == "no_disponible":
            no_disponibles.append(link)

    # ── PRINT RESUMEN ANTES DE EMPEZAR ──
    total = len(links)
    falta = len(pending)
    no_disp = len(no_disponibles)
    print(f"\nTotal de propiedades: {total}")
    print(f"Pendientes por procesar: {falta}")
    print(f"No disponibles: {no_disp}")
    print(f"Ya procesadas: {total - falta - no_disp}")

    # Si no hay propiedades para procesar, terminar
    if falta + no_disp == 0:
        print("\nNo hay propiedades nuevas para procesar")
        return

    # 4) Carpeta base de resultados
    date_str = datetime.now().strftime("%Y-%m-%d")
    carpeta_base = CARPETA_RESULTADOS
    os.makedirs(carpeta_base, exist_ok=True)

    # Crear carpeta para HTMLs y JSONs
    carpeta_datos = os.path.join(carpeta_base, date_str)
    os.makedirs(carpeta_datos, exist_ok=True)

    # Crear carpeta base para imágenes
    carpeta_imagenes = os.path.join(carpeta_base, "imagenes")
    os.makedirs(carpeta_imagenes, exist_ok=True)

    # 5) Lanzar navegador y barra de progreso
    pbar = ProgressBar(falta + no_disp, desc="Extrayendo propiedades", unit="propiedad")
    ok = err = no_disp_count = 0
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=ESTADO_FB if os.path.exists(ESTADO_FB) else None,
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        # Procesar propiedades pendientes
        for item in pending:
            pid    = item["id"]
            url    = item["link"]
            ciudad = item["ciudad"]
            t0     = time.time()
            try:
                # Navegar y esperar carga
                page.goto(url, timeout=60000)
                page.wait_for_timeout(3000)
                
                # Extraer datos
                datos = procesar_propiedad(page, url, pid, ciudad, date_str)
                
                # Actualizar repositorio maestro
                if datos:
                    data_master[pid] = datos
                    # Si está no disponible, incrementar contador
                    if datos.get("metadata", {}).get("status") == "no_disponible":
                        no_disp_count += 1
                    else:
                        ok += 1
                    
                    # Guardar cada 10 propiedades
                    if (ok + no_disp_count) % 10 == 0:
                        with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as f:
                            json.dump(data_master, f, ensure_ascii=False, indent=2)
                
                print(f"   ✓ {pid} procesado en {time.time()-t0:.1f}s")
                
            except Exception as e:
                err += 1
                print(f"❌ Error en {pid}: {str(e)}")
            finally:
                pbar.update(1, ok=ok, err=err, last_time=time.time()-t0)

        # Verificar propiedades previamente no disponibles
        if no_disponibles:
            print("\nVerificando propiedades previamente no disponibles...")
            
        for item in no_disponibles:
            pid    = item["id"]
            url    = item["link"]
            ciudad = item["ciudad"]
            t0     = time.time()
            try:
                # Navegar y esperar carga
                page.goto(url, timeout=60000)
                page.wait_for_timeout(3000)
                
                # Extraer datos
                datos = procesar_propiedad(page, url, pid, ciudad, date_str)
                
                # Actualizar repositorio maestro
                if datos:
                    data_master[pid] = datos
                    # Si sigue no disponible, incrementar contador
                    if datos.get("metadata", {}).get("status") == "no_disponible":
                        no_disp_count += 1
                    else:
                        ok += 1
                        print(f"   ✓ {pid} ahora disponible")
                    
                    # Guardar cada 10 propiedades
                    if (ok + no_disp_count) % 10 == 0:
                        with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as f:
                            json.dump(data_master, f, ensure_ascii=False, indent=2)
                
            except Exception as e:
                err += 1
                print(f"❌ Error en {pid}: {str(e)}")
            finally:
                pbar.update(1, ok=ok, err=err, last_time=time.time()-t0)

        pbar.close()
        page.close()
        browser.close()

    # Guardar repositorio final
    with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as f:
        json.dump(data_master, f, ensure_ascii=False, indent=2)

    # Estadísticas finales
    total_procesadas = ok + err + no_disp_count
    if total_procesadas > 0:
        print(f"\nTotal de propiedades en el repositorio maestro: {len(data_master)}")
        print(f"Procesadas exitosamente: {ok}")
        print(f"No disponibles: {no_disp_count}")
        print(f"Con errores: {err}")
        print(f"Porcentaje de éxito: {(ok/total_procesadas*100):.1f}%")
    else:
        print("\nNo se procesaron propiedades en esta ejecución")

if __name__ == "__main__":
    main() 