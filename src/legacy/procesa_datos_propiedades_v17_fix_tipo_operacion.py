#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
procesa_datos_propiedades.py

Script para procesar los datos crudos extraídos y generar el repositorio
completo con todos los campos necesarios.
"""

import os
import json
import logging
import shutil
import re
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple, Union

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

regex_precio = r"(?:\$|MXN|mnx|MX\$)?\s?([\d.,]+)\s?(millones?|millón|mil|k|M|MM)?"

def normalizar_precio(texto):
    if not texto:
        return None
    texto = texto.lower()
    match = re.search(regex_precio, texto)
    if match:
        numero, unidad = match.groups()
        try:
            numero = float(numero.replace(',', '').replace('.', '')) if ',' in numero and '.' in numero else float(numero.replace(',', '').replace('.', '', 1))
        except:
            return None
        if unidad in ['millon', 'millones', 'mm', 'm']:
            return int(numero * 1_000_000)
        if unidad in ['mil', 'k']:
            return int(numero * 1_000)
        return int(numero)
    return None

# Constantes y rutas
CARPETA_DATOS_CRUDOS = "resultados/datos_crudos"
ARCHIVO_SALIDA = "resultados/propiedades_estructuradas.json"
ARCHIVO_BACKUP = "resultados/propiedades_estructuradas.json.bak"
ARCHIVO_REPOSITORIO = "resultados/repositorio_propiedades.json"
CARPETA_REPO_MASTER = "resultados/repositorio_propiedades.json"

# Constantes de validación
RANGO_PRECIO_VENTA = (200_000, 100_000_000)  # Rango de precios válidos para venta
RANGO_PRECIO_RENTA = (1_500, 300_000)      # Rango de precios válidos para renta mensual
RANGO_SUPERFICIE = (20, 10000)             # Rango de superficie en m2
RANGO_CONSTRUCCION = (20, 2000)            # Rango de construcción en m2
RANGO_RECAMARAS = (1, 10)                  # Rango de número de recámaras
RANGO_BANOS = (1, 6)                       # Rango de número de baños
RANGO_NIVELES = (1, 4)                     # Rango de número de niveles
RANGO_ESTACIONAMIENTOS = (0, 6)            # Rango de lugares de estacionamiento

def normalizar_texto(texto: str) -> str:
    """Normaliza un texto para procesamiento."""
    if not texto:
        return ""
    
    # Convertir a minúsculas y eliminar espacios extras
    texto = texto.lower().strip()
    texto = re.sub(r'\s+', ' ', texto)
    
    # Normalizar caracteres especiales
    reemplazos = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ü': 'u', 'ñ': 'n', 'à': 'a', 'è': 'e', 'ì': 'i',
        'ò': 'o', 'ù': 'u'
    }
    for k, v in reemplazos.items():
        texto = texto.replace(k, v)
    
    return texto

def validar_rango(valor: Union[int, float], rango: Tuple[Union[int, float], Union[int, float]]) -> bool:
    """Valida si un valor está dentro de un rango específico."""
    if valor is None:
        return False
    try:
        valor_num = float(valor)
        return rango[0] <= valor_num <= rango[1]
    except (ValueError, TypeError):
        return False

def extraer_numero(texto: str) -> Optional[float]:
    """Extrae un número de un texto, manejando diferentes formatos."""
    if not texto:
        return None
    
    # Limpiar el texto
    texto = texto.replace(' ', '').replace('$', '').replace(',', '').strip()
    
    # Patrones comunes de números
    patrones = [
        r'(\d+(?:\.\d+)?)',  # Números con decimales
        r'(\d+)',            # Números enteros
    ]
    
    for patron in patrones:
        if match := re.search(patron, texto):
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return None

def extraer_medidas(texto: str) -> Optional[float]:
    """Extrae medidas de superficie o construcción."""
    if not texto:
        return None
    
    # Patrones para medidas
    patrones = [
        r'(\d+(?:\.\d+)?)\s*(?:x|\*)\s*(\d+(?:\.\d+)?)',  # formato: 10x20
        r'(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?(?:\s+cuadrados?)?)',  # formato: 200m2
        r'(\d+(?:\.\d+)?)\s*(?:mts?2|mt2)',  # formato: 200mt2
    ]
    
    for patron in patrones:
        if match := re.search(patron, texto):
            try:
                if 'x' in patron or '*' in patron:
                    # Si es formato de multiplicación (10x20)
                    largo = float(match.group(1))
                    ancho = float(match.group(2))
                    return largo * ancho
                else:
                    # Si es formato directo (200m2)
                    return float(match.group(1))
            except ValueError:
                continue
    
    return None

def es_precio_valido(precio: float, tipo_operacion: str) -> bool:
    """Valida si un precio es válido según el tipo de operación."""
    if not precio:
        return False
    
    try:
        precio_num = float(precio)
        if tipo_operacion.lower() == "venta":
            return RANGO_PRECIO_VENTA[0] <= precio_num <= RANGO_PRECIO_VENTA[1]
        elif tipo_operacion.lower() == "renta":
            return RANGO_PRECIO_RENTA[0] <= precio_num <= RANGO_PRECIO_RENTA[1]
        return False
    except (ValueError, TypeError):
        return False

def limpiar_descripcion(texto: str) -> str:
    """Limpia y normaliza una descripción."""
    if not texto:
        return ""
    
    # Convertir a minúsculas y eliminar espacios extras
    texto = texto.lower().strip()
    texto = re.sub(r'\s+', ' ', texto)
    
    # Eliminar caracteres especiales y emojis
    texto = re.sub(r'[^\w\s\.,;:¿?¡!áéíóúüñ-]', '', texto)
    
    # Normalizar puntuación
    texto = re.sub(r'\.+', '.', texto)  # Eliminar puntos múltiples
    texto = re.sub(r'\s*[,;]\s*', ', ', texto)  # Normalizar comas y punto y coma
    
    return texto.strip()

def extraer_valor_numerico(texto: str, patrones: List[str]) -> Optional[int]:
    """Extrae un valor numérico usando una lista de patrones."""
    if not texto:
        return None
    
    texto = normalizar_texto(texto)
    
    for patron in patrones:
        if match := re.search(patron, texto):
            try:
                return int(match.group(1))
            except ValueError:
                continue
    
    return None

def extraer_colonia(texto, ubicacion):
    """Extrae la colonia de la descripción o ubicación."""
    colonias_conocidas = [
        # Cuernavaca
        "Lomas de Cortés", "Acapantzingo", "Delicias", "Burgos",
        "Tres de Mayo", "Palmira", "Tlaltenango", "Vista Hermosa",
        "Rancho Cortés", "Reforma", "Chapultepec", "Buenavista",
        "Maravillas", "Amatitlán", "Antonio Barona", "Lomas de la Selva",
        "Lomas de Tzompantle", "Lomas de Atzingo", "Lomas de Tetela",
        "Alta Vista", "Jardines de Cuernavaca", "Real de Tetela",
        "Provincias de Morelos", "Teopanzolco", "Lomas de Ahuatlán",
        "Las Palmas", "Cantarranas", "Centro",
        # Temixco
        "Burgos Bugambilias", "Lomas de Cuernavaca", "Campo Verde",
        "Los Presidentes", "Alta Palmira", "Azteca", "Las Rosas",
        # Jiutepec
        "Jardines de la Hacienda", "Tejalpa", "Civac", "La Calera",
        "Independencia", "Morelos", "Tlahuapan", "Las Fincas",
        # Emiliano Zapata
        "Tezoyuca", "1 de Mayo", "El Capiri", "Las Garzas",
        # Yautepec
        "Oaxtepec", "Cocoyoc", "Oacalco", "La Joya"
    ]
    
    # Primero buscar en la ubicación si existe
    if ubicacion and isinstance(ubicacion, dict):
        dir_completa = ubicacion.get("direccion_completa", "").lower()
        for colonia in colonias_conocidas:
            if colonia.lower() in dir_completa:
                return colonia
    
    # Buscar en el texto
    texto = texto.lower()
    for colonia in colonias_conocidas:
        if colonia.lower() in texto:
            return colonia
            
    # Buscar patrones comunes
    patrones = [
        r"col(?:onia)?\.?\s+([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+?)(?:\.|,|en|cerca|junto|$)",
        r"fracc(?:ionamiento)?\.?\s+([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+?)(?:\.|,|en|cerca|junto|$)",
        r"en\s+([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+?)(?:\s+(?:cerca|junto|a un lado|sobre|por|en)|$)",
        r"ubicad[oa]\s+en\s+([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+?)(?:\.|,|cerca|junto|$)",
        r"zona\s+(?:de\s+)?([A-Za-zÁáÉéÍíÓóÚúÑñ\s]+?)(?:\.|,|cerca|junto|$)"
    ]
    
    for patron in patrones:
        if match := re.search(patron, texto):
            colonia_encontrada = match.group(1).strip()
            # Limpiar la colonia encontrada
            colonia_encontrada = re.sub(r'\s+', ' ', colonia_encontrada)
            colonia_encontrada = colonia_encontrada.strip('., ')
            
            # Verificar si la colonia encontrada está en nuestro catálogo
            for colonia in colonias_conocidas:
                if colonia.lower() in colonia_encontrada.lower():
                    return colonia
            
            # Si no está en el catálogo pero parece válida, retornarla
            if len(colonia_encontrada) > 3 and not any(c.isdigit() for c in colonia_encontrada):
                return colonia_encontrada.title()
    
    return None

def extraer_tipo_propiedad(texto):
    """Extrae el tipo de propiedad con mejor categorización."""
    if not texto:
        return None
        
    texto = normalizar_texto(texto)
    
    # Primero buscar menciones explícitas
    menciones_explicitas = {
        'Casa': [
            r'(?:hermosa|bonita|preciosa|bella|linda|nueva|amplia|moderna|vendo|rento|casa)(?:\s+en\s+venta|\s+sola|\s+nueva|\s+individual|\s+habitacional|\s+residencial|\s+unifamiliar)',
            r'casa(?:\s+(?:sola|nueva|individual|habitacional|residencial|unifamiliar))?(?:\s+en\s+(?:venta|renta))?',
            r'residencia(?:\s+(?:nueva|moderna|amplia))?',
            r'chalet',
            r'vivienda(?:\s+unifamiliar)?'
        ],
        'Departamento': [
            r'(?:hermoso|bonito|precioso|bello|lindo|nuevo|amplio|moderno|vendo|rento|departamento)(?:\s+en\s+(?:venta|renta)|\s+nuevo|\s+tipo|\s+estudio)',
            r'departamento(?:\s+(?:nuevo|tipo|estudio))?(?:\s+en\s+(?:venta|renta))?',
            r'depto(?:\.|\s+)',
            r'dpto(?:\.|\s+)',
            r'apartamento',
            r'apto(?:\.|\s+)',
            r'pent\s*house',
            r'penthouse',
            r'loft'
        ],
        'Terreno': [
            r'(?:hermoso|bonito|precioso|bello|lindo|nuevo|amplio|vendo|rento|terreno)(?:\s+en\s+(?:venta|renta)|\s+plano|\s+urbano|\s+residencial)',
            r'terreno(?:\s+(?:plano|urbano|residencial))?(?:\s+en\s+(?:venta|renta))?',
            r'lote(?:\s+(?:residencial|urbano|comercial))?',
            r'predio(?:\s+(?:urbano|residencial))?',
            r'parcela',
            r'solar(?:\s+urbano)?',
            r'hectareas?(?:\s+de\s+terreno)?',
            r'has?(?:\.|\s+)(?:de\s+terreno)?',
            r'm2\s+(?:de\s+)?terreno',
            r'metros?\s+(?:cuadrados?\s+)?(?:de\s+)?terreno'
        ],
        'Local': [
            r'(?:hermoso|bonito|precioso|bello|lindo|nuevo|amplio|moderno|vendo|rento|local)(?:\s+en\s+(?:venta|renta)|\s+comercial|\s+nuevo)',
            r'local(?:\s+(?:comercial|nuevo))?(?:\s+en\s+(?:venta|renta))?',
            r'bodega(?:\s+comercial)?',
            r'nave(?:\s+industrial)?',
            r'oficina(?:\s+comercial)?',
            r'consultorio',
            r'despacho',
            r'plaza(?:\s+comercial)?'
        ]
    }
    
    # Buscar menciones explícitas primero
    for tipo, patrones in menciones_explicitas.items():
        if any(re.search(patron, texto, re.IGNORECASE) for patron in patrones):
            return tipo
            
    # Si no hay mención explícita, buscar características físicas
    caracteristicas_vivienda = [
        r'\d+\s*(?:recamaras?|rec(?:s|\.|amaras?)?|habitaciones?|cuartos?|dormitorios?)',
        r'(?:ba[ñn]os?|wc|sanitarios?)',
        r'cocina\s+(?:integral|equipada)',
        r'sala\s*(?:y|,)?\s*comedor',
        r'cochera|garage|estacionamiento',
        r'planta\s+(?:alta|baja)',
        r'jardin|patio',
        r'terraza|balcon'
    ]
    
    caracteristicas_depto = [
        r'edificio',
        r'torre',
        r'nivel\s+\d+',
        r'piso\s+\d+',
        r'\d+(?:er|do|ro|to|vo|°)?\s+piso',
        r'elevador',
        r'ascensor',
        r'condominio\s+vertical',
        r'desarrollo\s+vertical'
    ]
    
    caracteristicas_terreno = [
        r'(?:terreno|lote)\s+(?:\d+\s*)?(?:x|por)\s*\d+',
        r'(?:uso\s+de\s+)?suelo\s+(?:habitacional|comercial|mixto)',
        r'escrituras?\s+(?:en\s+)?regla',
        r'ejidal(?:es)?',
        r'colindancias',
        r'medidas\s+y\s+colindancias',
        r'poligonal',
        r'topografia'
    ]
    
    caracteristicas_local = [
        r'cortina\s+metalica',
        r'zona\s+comercial',
        r'uso\s+comercial',
        r'local(?:es)?\s+(?:adjuntos?|contiguos?)',
        r'area\s+de\s+exhibicion',
        r'vitrina|aparador',
        r'almacen|bodega'
    ]
    
    # Contar características de cada tipo
    puntos = {
        'Casa': sum(1 for patron in caracteristicas_vivienda if re.search(patron, texto, re.IGNORECASE)),
        'Departamento': sum(1 for patron in caracteristicas_depto if re.search(patron, texto, re.IGNORECASE)),
        'Terreno': sum(1 for patron in caracteristicas_terreno if re.search(patron, texto, re.IGNORECASE)),
        'Local': sum(1 for patron in caracteristicas_local if re.search(patron, texto, re.IGNORECASE))
    }
    
    # Si hay características claras de un tipo, usarlas
    max_puntos = max(puntos.values())
    if max_puntos > 0:
        for tipo, score in puntos.items():
            if score == max_puntos:
                return tipo
    
    # Si no hay características claras, intentar inferir por el contexto
    if re.search(r'(?:casa|vivienda|hogar|residencia)(?:\s+en\s+(?:venta|renta))?', texto, re.IGNORECASE):
        return 'Casa'
    elif re.search(r'(?:departamento|depto|dpto|apartamento|apto)(?:\s+en\s+(?:venta|renta))?', texto, re.IGNORECASE):
        return 'Departamento'
    elif re.search(r'(?:terreno|lote|predio|solar)(?:\s+en\s+(?:venta|renta))?', texto, re.IGNORECASE):
        return 'Terreno'
    elif re.search(r'(?:local|bodega|nave|oficina|consultorio)(?:\s+en\s+(?:venta|renta))?', texto, re.IGNORECASE):
        return 'Local'
    
    return None

def extraer_amenidades(texto):
    """Extrae amenidades con mejor detección."""
    texto = texto.lower()
    
    amenidades = {
        "alberca": {
            "presente": any(palabra in texto for palabra in ["alberca", "piscina", "pool"]),
            "tipo": None,
            "detalles": []
        },
        "jardin": {
            "presente": any(palabra in texto for palabra in ["jardin", "jardín", "área verde", "area verde"]),
            "tipo": None,
            "detalles": []
        },
        "estacionamiento": {
            "presente": False,
            "tipo": None,
            "techado": False,
            "detalles": []
        },
        "areas_comunes": {
            "presentes": False,
            "tipos": [],
            "detalles": []
        },
        "deportivas": {
            "presentes": False,
            "tipos": [],
            "detalles": []
        },
        "adicionales": []
    }
    
    # Detectar estacionamiento
    estacionamientos = extraer_estacionamientos(texto)
    if estacionamientos:
        amenidades["estacionamiento"]["presente"] = True
        amenidades["estacionamiento"]["detalles"].append(f"{estacionamientos} lugares")
    
    # Detectar áreas comunes
    areas_comunes = [
        "terraza", "roof garden", "roof top", "salón", "salon",
        "área social", "area social", "palapa"
    ]
    tipos_encontrados = []
    for area in areas_comunes:
        if area in texto:
            tipos_encontrados.append(area)
    
    if tipos_encontrados:
        amenidades["areas_comunes"]["presentes"] = True
        amenidades["areas_comunes"]["tipos"] = tipos_encontrados
    
    # Detectar amenidades adicionales
    adicionales = {
        "calentador solar": ["calentador solar", "paneles solares"],
        "cuarto de servicio": ["cuarto de servicio", "habitación de servicio"],
        "vigilancia": ["vigilancia", "seguridad 24", "camaras", "cámaras"],
        "cisterna": ["cisterna", "aljibe"],
        "bodega": ["bodega", "storage"],
        "aire acondicionado": ["aire acondicionado", "a/c", "minisplit"]
    }
    
    for amenidad, palabras_clave in adicionales.items():
        if any(palabra in texto for palabra in palabras_clave):
            amenidades["adicionales"].append(amenidad)
    
    return amenidades

def extraer_legal(texto):
    """Extrae información legal de la propiedad."""
    return {
        "escrituras": any(word in texto.lower() for word in ["escrituras", "escriturada", "título de propiedad"]),
        "cesion_derechos": any(word in texto.lower() for word in ["cesión", "cesion de derechos", "traspaso"]),
        "formas_de_pago": {
            "credito": any(word in texto.lower() for word in ["crédito", "credito", "infonavit", "fovissste"]),
            "contado": any(word in texto.lower() for word in ["contado", "efectivo"]),
            "financiamiento": any(word in texto.lower() for word in ["financiamiento", "financiado", "mensualidades"])
        }
    }

def extraer_ubicacion_detallada(texto, ubicacion_original):
    """Extrae información detallada de ubicación."""
    ubicacion = {}  # Empezar con un diccionario vacío
    
    # Mapeo de colonias a ciudades
    colonias_ciudades = {
        # Cuernavaca
        "Lomas de Cortés": "Cuernavaca", "Acapantzingo": "Cuernavaca",
        "Delicias": "Cuernavaca", "Palmira": "Cuernavaca",
        "Tlaltenango": "Cuernavaca", "Vista Hermosa": "Cuernavaca",
        "Rancho Cortés": "Cuernavaca", "Reforma": "Cuernavaca",
        "Chapultepec": "Cuernavaca", "Buenavista": "Cuernavaca",
        "Maravillas": "Cuernavaca", "Amatitlán": "Cuernavaca",
        "Antonio Barona": "Cuernavaca", "Lomas de la Selva": "Cuernavaca",
        "Lomas de Tzompantle": "Cuernavaca", "Lomas de Atzingo": "Cuernavaca",
        "Lomas de Tetela": "Cuernavaca", "Alta Vista": "Cuernavaca",
        "Jardines de Cuernavaca": "Cuernavaca", "Real de Tetela": "Cuernavaca",
        "Provincias de Morelos": "Cuernavaca", "Teopanzolco": "Cuernavaca",
        "Lomas de Ahuatlán": "Cuernavaca", "Las Palmas": "Cuernavaca",
        "Cantarranas": "Cuernavaca", "Centro": "Cuernavaca",
        "Chipitlán": "Cuernavaca", "Lomas de Cortes": "Cuernavaca",
        "Ahuatepec": "Cuernavaca",
        # Temixco
        "Burgos": "Temixco", "Tres de Mayo": "Temixco",
        "Burgos Bugambilias": "Temixco", "Lomas de Cuernavaca": "Temixco",
        "Campo Verde": "Temixco", "Los Presidentes": "Temixco",
        "Alta Palmira": "Temixco", "Azteca": "Temixco",
        "Las Rosas": "Temixco",
        # Jiutepec
        "Jardines de la Hacienda": "Jiutepec", "Tejalpa": "Jiutepec",
        "Civac": "Jiutepec", "La Calera": "Jiutepec",
        "Independencia": "Jiutepec", "Morelos": "Jiutepec",
        "Tlahuapan": "Jiutepec", "Las Fincas": "Jiutepec",
        "Kloster Sumiya": "Jiutepec", "Sumiya": "Jiutepec",
        # Emiliano Zapata
        "Tezoyuca": "Emiliano Zapata", "1 de Mayo": "Emiliano Zapata",
        "El Capiri": "Emiliano Zapata", "Las Garzas": "Emiliano Zapata",
        # Yautepec
        "Oaxtepec": "Yautepec", "Cocoyoc": "Yautepec",
        "Oacalco": "Yautepec", "La Joya": "Yautepec",
        # Monte Casino
        "Monte Casino": "Cuernavaca"
    }
    
    # Mantener la dirección completa y texto original si existen
    if ubicacion_original and isinstance(ubicacion_original, dict):
        ubicacion["direccion_completa"] = ubicacion_original.get("direccion_completa", "")
        ubicacion["texto_original"] = ubicacion_original.get("texto_original", "")
    
    # Extraer referencias
    referencias = []
    patrones_ref = [
        r"cerca de ([^\.]+)",
        r"a (?:\d+|unos) (?:min|minutos) de ([^\.]+)",
        r"junto a ([^\.]+)",
        r"frente a ([^\.]+)",
        r"sobre (?:la )?(?:calle|avenida|av\.|blvd\.) ([^\.]+)",
        r"(?:a )?(?:un )?costado de ([^\.]+)",
        r"(?:en )?esquina con ([^\.]+)",
        r"a (?:la )?altura de ([^\.]+)"
    ]
    
    texto_busqueda = texto.lower()
    if ubicacion_original and isinstance(ubicacion_original, dict):
        texto_busqueda += " " + ubicacion_original.get("direccion_completa", "").lower()
        texto_busqueda += " " + ubicacion_original.get("texto_original", "").lower()
    
    # Buscar colonia primero en el texto original
    colonia = None
    for col, ciudad in colonias_ciudades.items():
        if col.lower() in texto_busqueda:
            colonia = col
            ubicacion["ciudad"] = ciudad
            break
    
    # Si no se encontró colonia, buscar en la ubicación original
    if not colonia and ubicacion_original and isinstance(ubicacion_original, dict):
        colonia_orig = ubicacion_original.get("colonia")
        if colonia_orig and colonia_orig in colonias_ciudades:
            colonia = colonia_orig
            ubicacion["ciudad"] = colonias_ciudades[colonia_orig]
    
    # Buscar referencias
    for patron in patrones_ref:
        if matches := re.finditer(patron, texto_busqueda):
            for match in matches:
                ref = match.group(1).strip()
                if ref and len(ref) > 3 and not any(r.lower() in ref.lower() for r in referencias):
                    referencias.append(ref.strip('., ').title())
    
    # Determinar ciudad si aún no se ha encontrado
    if "ciudad" not in ubicacion:
        ciudades_conocidas = {
            "cuernavaca": "Cuernavaca",
            "temixco": "Temixco",
            "jiutepec": "Jiutepec",
            "zapata": "Emiliano Zapata",
            "yautepec": "Yautepec",
            "xochitepec": "Xochitepec",
            "tepoztlan": "Tepoztlán",
            "emiliano zapata": "Emiliano Zapata"
        }
        for ciudad_key, ciudad_nombre in ciudades_conocidas.items():
            if ciudad_key in texto_busqueda:
                ubicacion["ciudad"] = ciudad_nombre
                break
    
    # Actualizar ubicación
    ubicacion.update({
        "colonia": colonia,
        "estado": "Morelos",  # Por defecto todas las propiedades están en Morelos
        "referencias": referencias if referencias else None
    })
    
    return ubicacion

def procesar_numero_mexicano(texto: str) -> Optional[float]:
    """
    Procesa un número en formato mexicano (con comas y puntos) y lo convierte a float.
    
    Args:
        texto: Texto que contiene el número
        
    Returns:
        Número convertido a float o None si no se pudo procesar
    """
    if not texto:
        return None
    
    # Si ya es un número, retornarlo directamente
    if isinstance(texto, (int, float)):
        return float(texto)
            
    # Limpiar el texto
    texto = str(texto).strip()
    texto = texto.replace("$", "").replace(" ", "")
    
    # Remover texto adicional después del número
    texto = re.split(r'[^0-9,.KkMm]', texto)[0]
    
    # Detectar el formato del número
    tiene_punto = "." in texto
    tiene_coma = "," in texto
    
    # Contar ocurrencias de puntos y comas
    num_puntos = texto.count(".")
    num_comas = texto.count(",")
    
    # Determinar el formato basado en los separadores
    if num_puntos > 1:  # Formato con puntos como separador de miles: 1.234.567
        texto = texto.replace(".", "")
    elif num_comas > 1:  # Formato con comas como separador de miles: 1,234,567
        texto = texto.replace(",", "")
    elif tiene_punto and tiene_coma:
        if texto.rindex(".") > texto.rindex(","):  # 1,234.56
            texto = texto.replace(",", "")
        else:  # 1.234,56
            texto = texto.replace(".", "").replace(",", ".")
    elif tiene_punto:  # Asumimos que es separador decimal
        pass  # Mantener el formato
    elif tiene_coma:  # Asumimos que es separador decimal
        texto = texto.replace(",", ".")
    
    # Manejar K (miles) y M (millones)
    multiplicador = 1
    if texto.strip().lower().endswith('k'):
        multiplicador = 1000
        texto = texto[:-1]
    elif texto.strip().lower().endswith('m'):
        multiplicador = 1000000
        texto = texto[:-1]
    
    try:
        valor = float(texto) * multiplicador
        # Validar rangos razonables
        if 1 <= valor <= 1_000_000_000:  # Entre $1 y $1B
            return valor
    except ValueError:
        pass
    
    return None

def extraer_precio(texto: str) -> Dict:
    """
    Extrae el precio original del texto sin procesarlo.
    
    Args:
        texto: Texto que contiene el precio o diccionario con información del precio
        
    Returns:
        Dict con:
            - texto: str con el texto original del precio
            - valor: float con el valor numérico normalizado
            - es_valido: bool indicando si se pudo procesar el precio
            - confianza: float entre 0 y 1
            - mensaje: str con detalles o error
            - formato: str con el precio formateado para mostrar
    """
    if not texto:
        return {
            "texto": "",
            "valor": None,
            "es_valido": False,
            "confianza": 0.0,
            "mensaje": "Texto vacío",
            "formato": "Precio no disponible"
        }
    
    # Si el texto es un diccionario, buscar el precio en el campo precio
    if isinstance(texto, dict):
        try:
            # Si tiene texto, usarlo como valor principal
            if "texto" in texto:
                valor_normalizado = procesar_numero_mexicano(texto["texto"])
                formato = f"${valor_normalizado:,.0f}" if valor_normalizado is not None else "Precio no disponible"
                return {
                    "texto": texto["texto"],
                    "valor": valor_normalizado,
                    "es_valido": valor_normalizado is not None,
                    "confianza": 1.0 if valor_normalizado is not None else 0.0,
                    "mensaje": "",
                    "formato": formato
                }
            # Si tiene valor, usarlo directamente
            elif "valor" in texto:
                valor = texto["valor"]
                if isinstance(valor, (int, float)):
                    return {
                        "texto": str(valor),
                        "valor": float(valor),
                        "es_valido": True,
                        "confianza": 1.0,
                        "mensaje": "",
                        "formato": f"${float(valor):,.0f}"
                    }
                else:
                    valor_normalizado = procesar_numero_mexicano(str(valor))
                    formato = f"${valor_normalizado:,.0f}" if valor_normalizado is not None else "Precio no disponible"
                    return {
                        "texto": str(valor),
                        "valor": valor_normalizado,
                        "es_valido": valor_normalizado is not None,
                        "confianza": 1.0 if valor_normalizado is not None else 0.0,
                        "mensaje": "",
                        "formato": formato
                    }
        except Exception as e:
            return {
                "texto": str(texto),
                "valor": None,
                "es_valido": False,
                "confianza": 0.0,
                "mensaje": f"Error procesando precio: {str(e)}",
                "formato": "Precio no disponible"
            }
    
    # Si el texto es un string, intentar extraer y normalizar el precio
    if isinstance(texto, str):
        valor_normalizado = procesar_numero_mexicano(texto)
        formato = f"${valor_normalizado:,.0f}" if valor_normalizado is not None else "Precio no disponible"
        return {
            "texto": texto,
            "valor": valor_normalizado,
            "es_valido": valor_normalizado is not None,
            "confianza": 1.0 if valor_normalizado is not None else 0.0,
            "mensaje": "",
            "formato": formato
        }
    
    return {
        "texto": str(texto),
        "valor": None,
        "es_valido": False,
        "confianza": 0.0,
        "mensaje": "Formato no reconocido",
        "formato": "Precio no disponible"
    }

def extraer_recamaras_y_banos(texto):
    """Extrae el número de recámaras y baños con validación mejorada."""
    texto = texto.lower()
    resultado = {
        "recamaras": None,
        "banos": None,
        "medio_bano": None
    }
    
    # Patrones para recámaras
    patrones_recamaras = [
        r"(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?|cuartos?|alcobas?)",
        r"(?:rec[aá]maras?|habitaciones?|dormitorios?)\\s*:\\s*(\\d+)",
        r"(?:con|tiene)\s*(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?)",
        r"(\d+)\s*(?:rec|hab|dorm)\.?",
        r"casa\s*(?:de|con)\s*(\d+)\s*(?:rec[aá]maras?|habitaciones?)",
        r"departamento\s*(?:de|con)\s*(\d+)\s*(?:rec[aá]maras?|habitaciones?)",
        r"(?:^|\n)\s*▪️?\s*(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?)"
    ]
    
    # Patrones para baños completos y medios baños combinados
    patrones_banos_combinados = [
        r"(\d+)(?:\s*baños?)?\s*(?:y|,)?\s*(?:medio|1\/2)",
        r"(\d+)\s*\.5\s*(?:baños?|sanitarios?)",
        r"(\d+)\s*baños?\s*1\/2",
        r"(\d+)\s*baños?\s*y\s*medio",
        r"(\d+)\s*baños?\s*y\s*1\/2"
    ]
    
    # Patrones para baños completos
    patrones_banos = [
        r"(\d+)\s*(?:baños?|sanitarios?|wc)(?!\s*(?:y|,)?\s*(?:medio|1\/2))",
        r"(?:baños?|sanitarios?)\\s*:\\s*(\d+)(?!\s*(?:y|,)?\s*(?:medio|1\/2))",
        r"(?:con|tiene)\s*(\d+)\s*(?:baños?|sanitarios?)(?!\s*(?:y|,)?\s*(?:medio|1\/2))",
        r"(\d+)\s*(?:baño completo|b\.?c\.?)",
        r"(\d+)\s*(?:baños?\s*completos?)",
        r"casa\s*(?:de|con)\s*(\d+)\s*(?:baños?)(?!\s*(?:y|,)?\s*(?:medio|1\/2))",
        r"departamento\s*(?:de|con)\s*(\d+)\s*(?:baños?)(?!\s*(?:y|,)?\s*(?:medio|1\/2))",
        r"(?:^|\n)\s*▪️?\s*(\d+)\s*(?:baños?|sanitarios?)(?!\s*(?:y|,)?\s*(?:medio|1\/2))"
    ]
    
    # Patrones para medios baños independientes
    patrones_medio_bano = [
        r"(\d+)\s*(?:medio\s*baño|baño\s*medio)",
        r"(\d+)\s*(?:m\.?\s*b\.?|b\.?\s*m\.?)",
        r"(?:con|tiene)\s*(\d+)\s*(?:medio\s*baño|baño\s*medio)",
        r"(?:y|más)\s*(\d+)\s*(?:medio\s*baño|baño\s*medio)",
        r"(\d+)\s*(?:sanitario\s*medio|wc\s*medio)",
        r"(?:^|\n)\s*▪️?\s*(\d+)\s*(?:medio\s*baño|baño\s*medio)"
    ]
    
    # Buscar recámaras
    for patron in patrones_recamaras:
        if match := re.search(patron, texto):
            try:
                valor = int(match.group(1))
                if 1 <= valor <= 10:  # Validación de rango lógico
                    resultado["recamaras"] = valor
                    break
            except ValueError:
                continue
    
    # Primero buscar patrones combinados de baños completos y medios
    for patron in patrones_banos_combinados:
        if match := re.search(patron, texto):
            try:
                valor = int(match.group(1))
                if 1 <= valor <= 6:  # Validación de rango lógico
                    resultado["banos"] = valor
                    resultado["medio_bano"] = 1
                    break
            except ValueError:
                continue
    
    # Si no se encontró patrón combinado, buscar baños completos
    if resultado["banos"] is None:
        for patron in patrones_banos:
            if match := re.search(patron, texto):
                try:
                    valor = int(match.group(1))
                    if 1 <= valor <= 6:  # Validación de rango lógico
                        resultado["banos"] = valor
                        break
                except ValueError:
                    continue
    
    # Buscar medios baños específicamente si no se encontró en patrón combinado
    if resultado["medio_bano"] is None:
        for patron in patrones_medio_bano:
            if match := re.search(patron, texto):
                try:
                    valor = int(match.group(1))
                    if 1 <= valor <= 2:  # Validación de rango lógico
                        resultado["medio_bano"] = valor
                        break
                except ValueError:
                    continue
    
    # Detectar baños sin número específico
    if resultado["banos"] is None and any(frase in texto for frase in [
        "con baño", "baño completo", "baño principal",
        "tiene baño", "incluye baño"
    ]):
        resultado["banos"] = 1
    
    return resultado

def extraer_niveles(texto):
    """Extrae el número de niveles con validación mejorada."""
    texto = texto.lower()
    
    # Detectar si es de un nivel explícitamente
    es_un_nivel = any(frase in texto for frase in [
        "un nivel", "una planta", "planta baja",
        "sin escaleras", "todo en un nivel",
        "todo en planta baja", "casa en un nivel",
        "casa de un nivel", "1 nivel", "un piso",
        "casa en planta baja", "todo en pb"
    ])
    
    # Detectar si tiene opción a crecer
    opcion_crecer = any(frase in texto for frase in [
        "opción de crecimiento", "opcion de crecimiento",
        "posibilidad de crecer", "puede crecer",
        "con opción a segundo piso", "con opcion a segundo piso",
        "se puede construir arriba", "preparada para segundo piso",
        "preparado para segundo piso", "con preparación para segundo piso",
        "con preparacion para segundo piso"
    ])
    
    # Detectar si tiene planta alta o segundo piso
    tiene_planta_alta = any(frase in texto for frase in [
        "planta alta", "segundo piso", "2do piso",
        "segunda planta", "piso superior", "planta superior",
        "nivel superior", "dos niveles", "2 niveles"
    ]) and not opcion_crecer  # Si solo es opción, no cuenta como planta alta actual
    
    # Patrones para números específicos de niveles
    patrones_niveles = [
        r"(\d+)\s*(?:niveles?|pisos?|plantas?)",
        r"(?:de|con)\s*(\d+)\s*(?:niveles?|pisos?|plantas?)",
        r"(?:niveles?|pisos?|plantas?)\s*:\s*(\d+)",
        r"(?:casa|propiedad)\s*(?:de|con)\s*(\d+)\s*(?:niveles?|pisos?|plantas?)",
        r"(\d+)\s*(?:niv\.?|p\.?b\.?\s*\+\s*p\.?a\.?)"
    ]
    
    niveles = None
    
    # Buscar número específico de niveles
    for patron in patrones_niveles:
        if match := re.search(patron, texto):
            try:
                valor = int(match.group(1))
                if 1 <= valor <= 4:  # Validación de rango lógico
                    niveles = valor
                    break
            except ValueError:
                continue
    
    # Si no se encontró un número específico, inferir por otras menciones
    if niveles is None:
        if es_un_nivel and not tiene_planta_alta:
            niveles = 1
        elif tiene_planta_alta:
            niveles = 2
    
    return {
        "niveles": niveles,
        "un_nivel": (niveles == 1 or es_un_nivel) and not tiene_planta_alta,
        "tiene_planta_alta": tiene_planta_alta,
        "opcion_crecer": opcion_crecer
    }

def extraer_estacionamientos(texto):
    """Extrae el número de estacionamientos con validación mejorada."""
    texto = texto.lower()
    
    patrones_estacionamiento = [
        r"(\d+)\s*(?:estacionamientos?|cajone?s?|lugares?\s*de\s*estacionamiento)",
        r"(?:estacionamiento|cajon|lugar)\s*(?:para|de)\s*(\d+)\s*(?:auto|carro|coche)s?",
        r"(?:con|tiene)\s*(\d+)\s*(?:estacionamientos?|cajone?s?|lugares?\s*de\s*estacionamiento)",
        r"garage\s*(?:para|de)\s*(\d+)\s*(?:auto|carro|coche)s?",
        r"(\d+)\s*(?:auto|carro|coche)s?\s*en\s*(?:estacionamiento|garage)",
        r"cochera\s*(?:para|de)\s*(\d+)\s*(?:auto|carro|coche)s?",
        r"(\d+)\s*(?:lugar|espacio)s?\s*(?:de|para)\s*(?:auto|carro|coche)s?",
        r"capacidad\s*(?:para|de)\s*(\d+)\s*(?:auto|carro|coche)s?",
        r"estacionamiento\s*(?:para|de)\s*(\d+)\s*(?:auto|carro|coche)s?",
        r"cochera\s*(?:para|de)\s*(\d+)\s*(?:auto|carro|coche)s?",
        r"garaje\s*(?:para|de)\s*(\d+)\s*(?:auto|carro|coche)s?",
        r"(\d+)\s*autos?\s*en\s*(?:cochera|garage|estacionamiento)",
        r"(\d+)\s*lugares?\s*de\s*estacionamiento",
        r"estacionamiento\s*(\d+)\s*autos?",
        r"garaje\s*(\d+)\s*autos?",
        r"cochera\s*(\d+)\s*autos?",
        r"(\d+)\s*autos?\s*(?:cubiertos?|techados?)",
        r"garaje\s*(?:para|con)\s*(\d+)\s*autos?\s*(?:cubiertos?|techados?)",
        r"cochera\s*(?:para|con)\s*(\d+)\s*autos?\s*(?:cubiertos?|techados?)",
        r"(\d+)\s*(?:cajone?s?|lugares?)\s*(?:cubiertos?|techados?)",
        r"(\d+)\s*(?:estacionamientos?)\s*(?:cubiertos?|techados?)",
        r"(\d+)\s*(?:autos?|carros?|coches?)\s*(?:en\s*)?(?:estacionamiento|garage|cochera)\s*(?:cubiertos?|techados?)",
        r"garaje\s*(?:para|con)?\s*(\d+)\s*(?:autos?|carros?|coches?)\s*(?:cubiertos?|techados?)",
        r"cochera\s*(?:para|con)?\s*(\d+)\s*(?:autos?|carros?|coches?)\s*(?:cubiertos?|techados?)",
        r"estacionamiento\s*(?:para|con)?\s*(\d+)\s*(?:autos?|carros?|coches?)\s*(?:cubiertos?|techados?)",
        r"(?:^|\n)\s*▪️?\s*(\d+)\s*(?:autos?|lugares?|cajone?s?)",
        r"(?:^|\n)\s*▪️?\s*estacionamiento\s*(?:para|de)?\s*(\d+)\s*(?:autos?|carros?|coches?)"
    ]
    
    # Buscar coincidencias en los patrones
    for patron in patrones_estacionamiento:
        if match := re.search(patron, texto):
            try:
                valor = int(match.group(1))
                if 1 <= valor <= 10:  # Validación de rango lógico
                    # Verificar si el estacionamiento es techado
                    es_techado = any(palabra in texto for palabra in [
                        "techado", "techada", "cubierto", "cubierta",
                        "bajo techo", "techo", "tejado", "cubiertos",
                        "techados", "cubiertas", "techadas"
                    ])
                    
                    # Si el patrón menciona que es cubierto/techado, forzar es_techado a True
                    if any(palabra in match.group(0) for palabra in [
                        "cubierto", "cubierta", "techado", "techada",
                        "cubiertos", "cubiertas", "techados", "techadas"
                    ]):
                        es_techado = True
                    
                    return {
                        "cantidad": valor,
                        "techado": es_techado,
                        "tipo": "privado" if any(palabra in texto for palabra in [
                            "privado", "privada", "propio", "propia",
                            "exclusivo", "exclusiva", "individual"
                        ]) else None
                    }
            except ValueError:
                continue
    
    # Detectar estacionamiento sin número específico
    if any(frase in texto for frase in [
        "con estacionamiento", "tiene estacionamiento",
        "incluye estacionamiento", "con cochera",
        "con garage", "con lugar de estacionamiento",
        "estacionamiento propio", "cochera propia",
        "garage propio", "lugar de estacionamiento",
        "espacio para auto", "espacio para carro",
        "lugar para auto", "lugar para carro",
        "con estacionamiento techado", "con cochera techada",
        "con garage techado", "con estacionamiento cubierto",
        "con estacionamiento bajo techo", "con cochera bajo techo",
        "con garage bajo techo", "con estacionamiento con techo",
        "garaje eléctrico", "cochera eléctrica",
        "portón eléctrico"
    ]):
        return {
            "cantidad": 1,
            "techado": any(palabra in texto for palabra in [
                "techado", "techada", "cubierto", "cubierta",
                "bajo techo", "techo", "tejado", "cubiertos",
                "techados", "cubiertas", "techadas",
                "eléctrico", "electrico"
            ]),
            "tipo": "privado" if any(palabra in texto for palabra in [
                "privado", "privada", "propio", "propia",
                "exclusivo", "exclusiva", "individual"
            ]) else None
        }
    
    return {
        "cantidad": 0,
        "techado": False,
        "tipo": None
    }

def extraer_superficies(texto):
    """Extrae superficies de terreno y construcción con validación mejorada."""
    if not texto:
        return {
            "superficie_m2": None,
            "construccion_m2": None
        }
        
    texto = normalizar_texto(texto)
    
    resultado = {
        "superficie_m2": None,
        "construccion_m2": None
    }
    
    # Patrones para superficie de terreno
    patrones_terreno = [
        r'(?:superficie|terreno)(?:\s+de)?:?\s*([\d,.]+)\s*(?:m2|metros?|mt2|mts2)',
        r'([\d,.]+)\s*(?:m2|metros?|mt2|mts2)(?:\s+de)?(?:\s+terreno|superficie)',
        r'(?:lote|terreno)\s+(?:de|con)?\s*([\d,.]+)\s*(?:m2|metros?|mt2|mts2)',
        r'([\d,.]+)\s*(?:x|por)\s*([\d,.]+)(?:\s*(?:m2|metros?|mt2|mts2))?',
        r'(?:frente|fondo)\s*(?:de)?\s*([\d,.]+)(?:\s*(?:m2|metros?|mt2|mts2))?'
    ]
    
    # Patrones para superficie de construcción
    patrones_construccion = [
        r'(?:construccion|construidos?)(?:\s+de)?:?\s*([\d,.]+)\s*(?:m2|metros?|mt2|mts2)',
        r'([\d,.]+)\s*(?:m2|metros?|mt2|mts2)(?:\s+de)?(?:\s+construccion|construidos?)',
        r'(?:area|superficie)\s+construida:?\s*([\d,.]+)\s*(?:m2|metros?|mt2|mts2)'
    ]
    
    # Buscar superficie de terreno
    for patron in patrones_terreno:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            try:
                # Si el patrón captura dos números (frente x fondo)
                if len(match.groups()) == 2:
                    frente = float(match.group(1).replace(',', ''))
                    fondo = float(match.group(2).replace(',', ''))
                    resultado["superficie_m2"] = frente * fondo
                else:
                    valor = match.group(1).replace(',', '')
                    resultado["superficie_m2"] = float(valor)
                break
            except (ValueError, AttributeError):
                continue
    
    # Buscar superficie de construcción
    for patron in patrones_construccion:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            try:
                valor = match.group(1).replace(',', '')
                resultado["construccion_m2"] = float(valor)
                break
            except (ValueError, AttributeError):
                continue
    
    return resultado

def extraer_caracteristicas(texto, tipo_propiedad=None):
    """Extrae características con validación mejorada."""
    texto = texto.lower()
    
    # Extraer superficies
    superficies = extraer_superficies(texto)
    
    # Extraer recámaras y baños
    rec_banos = extraer_recamaras_y_banos(texto)
    
    # Extraer estacionamientos
    estacionamientos = extraer_estacionamientos(texto)
    
    # Detectar si tiene recámara en planta baja
    rec_pb = any(patron in texto for patron in [
        r'rec[aá]mara(?:\s+en)?\s+planta\s+baja',
        r'habitaci[oó]n(?:\s+en)?\s+planta\s+baja'
    ])
    
    # Detectar si es de un nivel
    un_nivel = any(patron in texto for patron in [
        'un nivel',
        'una planta',
        'planta baja',
        '1 nivel',
        'nivel 1'
    ])
    
    return {
        "recamaras": rec_banos["recamaras"],
        "banos": rec_banos["banos"],
        "medio_bano": rec_banos["medio_bano"],
        "niveles": None,  # Se maneja en otra función
        "estacionamientos": estacionamientos,
        "superficie_m2": superficies["superficie_m2"],
        "construccion_m2": superficies["construccion_m2"],
        "edad": None,  # Se maneja en otra función
        "recamara_planta_baja": rec_pb,
        "cisterna": False,  # Se maneja en otra función
        "capacidad_cisterna": None,
        "un_nivel": un_nivel,
        "opcion_crecer": False
    }

def extraer_caracteristicas_detalladas(texto, caracteristicas_orig=None):
    """
    Extrae características detalladas de la propiedad.
    Mantiene los valores originales si existen y solo agrega/actualiza los que faltan.
    """
    # Mantener características originales
    caract = caracteristicas_orig.copy() if caracteristicas_orig else {}
    
    # Asegurarse que todos los campos existan
    campos_default = {
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
        "capacidad_cisterna": None,
        "un_nivel": False,
        "opcion_crecer": False
    }
    
    for campo, valor in campos_default.items():
        if campo not in caract:
            caract[campo] = valor
    
    # Extraer estacionamientos si no existen
    if caract["estacionamientos"] is None:
        info_estacionamiento = extraer_estacionamientos(texto)
        caract["estacionamientos"] = info_estacionamiento["cantidad"]
    
    # Extraer superficies si no existen
    if caract["superficie_m2"] is None or caract["construccion_m2"] is None:
        superficies = extraer_superficies(texto)
        if caract["superficie_m2"] is None:
            caract["superficie_m2"] = superficies["superficie_m2"]
        if caract["construccion_m2"] is None:
            caract["construccion_m2"] = superficies["construccion_m2"]
    
    # Extraer recámaras y baños si no existen
    if caract["recamaras"] is None or caract["banos"] is None or caract["medio_bano"] is None:
        rec_banos = extraer_recamaras_y_banos(texto)
        if caract["recamaras"] is None:
            caract["recamaras"] = rec_banos["recamaras"]
        if caract["banos"] is None:
            caract["banos"] = rec_banos["banos"]
        if caract["medio_bano"] is None:
            caract["medio_bano"] = rec_banos["medio_bano"]
    
    # Extraer niveles si no existen
    if caract["niveles"] is None or not caract["un_nivel"]:
        info_niveles = extraer_niveles(texto)
        if caract["niveles"] is None:
            caract["niveles"] = info_niveles["niveles"]
        caract["un_nivel"] = info_niveles["un_nivel"]
        caract["opcion_crecer"] = info_niveles["opcion_crecer"]
        
        # Si se menciona planta alta, no puede ser de un nivel
        if info_niveles["tiene_planta_alta"]:
            caract["un_nivel"] = False
            if caract["niveles"] is None or caract["niveles"] < 2:
                caract["niveles"] = 2
    
    # Detectar recámara en planta baja
    if not caract["recamara_planta_baja"]:
        caract["recamara_planta_baja"] = any(frase in texto.lower() for frase in [
            "recámara en planta baja", "recamara en planta baja",
            "habitación en planta baja", "habitacion en planta baja",
            "dormitorio en planta baja", "recámara principal en planta baja",
            "recamara principal en pb", "habitación en pb"
        ])
    
    # Detectar cisterna y su capacidad
    if not caract["cisterna"]:
        texto_lower = texto.lower()
        caract["cisterna"] = "cisterna" in texto_lower
        if caract["cisterna"]:
            # Buscar capacidad de la cisterna
            patrones_cisterna = [
                r"cisterna\s*(?:de|con)?\s*(\d+(?:,\d+)?)\s*(?:mil)?\s*(?:litros?|lts?|m3)",
                r"cisterna\s*(?:de|con)?\s*(\d+(?:,\d+)?)\s*(?:mil)",
                r"cisterna\s*(?:con\s*)?capacidad\s*(?:de|para)?\s*(\d+(?:,\d+)?)\s*(?:mil)?\s*(?:litros?|lts?|m3)",
                r"cisterna\s*(?:con\s*)?capacidad\s*(?:de|para)?\s*(\d+(?:,\d+)?)\s*(?:mil)",
                r"cisterna\s*(?:de|con)?\s*(\d+(?:[.,]\d+)?)\s*(?:mil)?\s*(?:litros?|lts?|m3)",
                r"cisterna\s*(?:de|con)?\s*(\d+(?:[.,]\d+)?)\s*(?:mil)",
                r"cisterna\s*(?:con\s*)?capacidad\s*(?:de|para)?\s*(\d+(?:[.,]\d+)?)\s*(?:mil)?\s*(?:litros?|lts?|m3)",
                r"cisterna\s*(?:con\s*)?capacidad\s*(?:de|para)?\s*(\d+(?:[.,]\d+)?)\s*(?:mil)"
            ]
            
            for patron in patrones_cisterna:
                if match := re.search(patron, texto_lower):
                    try:
                        # Reemplazar comas y puntos por punto decimal
                        valor = match.group(1).replace(",", ".")
                        capacidad = float(valor)
                        
                        # Si menciona "mil", multiplicar por 1000
                        if "mil" in match.group(0):
                            capacidad *= 1000
                        
                        caract["capacidad_cisterna"] = int(capacidad)
                        break
                    except ValueError:
                        continue
    
    # Extraer edad de la propiedad si no existe
    if caract["edad"] is None:
        match = re.search(r"(\d+)\s*(?:años?|year)", texto.lower())
        if match:
            try:
                edad = int(match.group(1))
                if 0 <= edad <= 100:  # Validación de rango lógico
                    caract["edad"] = edad
            except ValueError:
                pass
        elif any(frase in texto.lower() for frase in ["nueva", "a estrenar", "recién construida"]):
            caract["edad"] = 0
    
    return caract

def extraer_caracteristicas_especificas(texto: str) -> Dict:
    """
    Extrae características específicas de la propiedad.
    """
    texto = normalizar_texto(texto)
    
    caracteristicas = {
        "cocina": {
            "tipo": None,
            "equipada": False,
            "integral": False
        },
        "sala_comedor": {
            "tipo": None,
            "amplia": False,
            "separada": False
        },
        "acabados": {
            "tipo": None,
            "calidad": None,
            "detalles": []
        },
        "seguridad": {
            "tipo": None,
            "detalles": []
        },
        "servicios": {
            "agua": False,
            "luz": False,
            "gas": False,
            "internet": False,
            "detalles": []
        },
        "estado": {
            "condicion": None,
            "antiguedad": None,
            "remodelado": False
        }
    }
    
    # Detectar tipo y características de cocina
    if "cocina integral" in texto:
        caracteristicas["cocina"]["tipo"] = "integral"
        caracteristicas["cocina"]["integral"] = True
    elif "cocina equipada" in texto:
        caracteristicas["cocina"]["tipo"] = "equipada"
        caracteristicas["cocina"]["equipada"] = True
    
    # Detectar características de sala/comedor
    if any(x in texto for x in ["sala amplia", "amplia sala", "gran sala"]):
        caracteristicas["sala_comedor"]["amplia"] = True
    if "sala comedor separados" in texto or "sala y comedor independientes" in texto:
        caracteristicas["sala_comedor"]["separada"] = True
    
    # Detectar acabados
    acabados_tipos = {
        "lujo": ["lujo", "premium", "alto nivel"],
        "modernos": ["modernos", "contemporáneos", "actuales"],
        "básicos": ["básicos", "sencillos", "estándar"]
    }
    for tipo, palabras in acabados_tipos.items():
        if any(palabra in texto for palabra in palabras):
            caracteristicas["acabados"]["tipo"] = tipo
            break
    
    # Detectar seguridad
    if "vigilancia" in texto or "seguridad 24" in texto:
        caracteristicas["seguridad"]["tipo"] = "vigilancia_24h"
        caracteristicas["seguridad"]["detalles"].append("vigilancia 24 horas")
    if "caseta" in texto:
        caracteristicas["seguridad"]["detalles"].append("caseta de vigilancia")
    if "cerca electrica" in texto:
        caracteristicas["seguridad"]["detalles"].append("cerca eléctrica")
    
    # Detectar servicios
    caracteristicas["servicios"]["agua"] = "agua" in texto
    caracteristicas["servicios"]["luz"] = any(x in texto for x in ["luz", "electricidad"])
    caracteristicas["servicios"]["gas"] = "gas" in texto
    caracteristicas["servicios"]["internet"] = any(x in texto for x in ["internet", "wifi"])
    
    # Detectar estado de la propiedad
    estados = {
        "nuevo": ["nueva", "a estrenar", "recién construida"],
        "excelente": ["excelente estado", "impecable", "como nueva"],
        "bueno": ["buen estado", "conservada"],
        "regular": ["regular estado", "necesita mantenimiento"],
        "remodelar": ["para remodelar", "necesita renovación"]
    }
    for estado, palabras in estados.items():
        if any(palabra in texto for palabra in palabras):
            caracteristicas["estado"]["condicion"] = estado
            break
    
    # Detectar antigüedad
    patrones_antiguedad = [
        r"(\d+)\s*(?:años?|year) de antigüedad",
        r"antigüedad(?:\s+de)?\s+(\d+)\s*(?:años?|year)",
        r"construida hace\s+(\d+)\s*(?:años?|year)"
    ]
    for patron in patrones_antiguedad:
        if match := re.search(patron, texto):
            try:
                caracteristicas["estado"]["antiguedad"] = int(match.group(1))
                break
            except ValueError:
                continue
    
    # Detectar si está remodelada
    caracteristicas["estado"]["remodelado"] = any(x in texto for x in [
        "remodelada", "renovada", "actualizada", "modernizada"
    ])
    
    return caracteristicas

def extraer_amenidades_detalladas(texto: str) -> Dict:
    """Extrae información detallada sobre las amenidades de la propiedad."""
    amenidades = {
        "alberca": {
            "presente": False,
            "tipo": None,
            "detalles": []
        },
        "jardin": {
            "presente": False,
            "tipo": None,
            "detalles": []
        },
        "estacionamiento": {
            "presente": False,
            "tipo": None,
            "techado": False,
            "detalles": []
        },
        "areas_comunes": {
            "presentes": False,
            "tipos": [],
            "detalles": []
        },
        "deportivas": {
            "presentes": False,
            "tipos": [],
            "detalles": []
        },
        "adicionales": []
    }
    
    # Detectar alberca
    if any(x in texto for x in ["alberca", "piscina", "pool"]):
        amenidades["alberca"]["presente"] = True
        if "alberca techada" in texto:
            amenidades["alberca"]["tipo"] = "techada"
        elif "alberca climatizada" in texto:
            amenidades["alberca"]["tipo"] = "climatizada"
    
    # Detectar jardín
    if any(x in texto for x in ["jardin", "jardín", "área verde"]):
        amenidades["jardin"]["presente"] = True
        if "jardin privado" in texto:
            amenidades["jardin"]["tipo"] = "privado"
        elif "jardin común" in texto or "jardines comunes" in texto:
            amenidades["jardin"]["tipo"] = "común"
    
    # Detectar estacionamiento
    if any(x in texto for x in ["estacionamiento", "cochera", "garage", "parking"]):
        amenidades["estacionamiento"]["presente"] = True
        if "estacionamiento techado" in texto or "cochera techada" in texto:
            amenidades["estacionamiento"]["techado"] = True
        if "estacionamiento subterráneo" in texto:
            amenidades["estacionamiento"]["tipo"] = "subterráneo"
        elif "estacionamiento privado" in texto:
            amenidades["estacionamiento"]["tipo"] = "privado"
    
    # Detectar áreas comunes
    areas_comunes = [
        "salón", "salon", "terraza", "roof garden", "área de lavado",
        "area de lavado", "lobby", "elevador", "ascensor"
    ]
    for area in areas_comunes:
        if area in texto:
            amenidades["areas_comunes"]["presentes"] = True
            amenidades["areas_comunes"]["tipos"].append(area)
    
    # Detectar instalaciones deportivas
    instalaciones = [
        "gym", "gimnasio", "cancha", "court", "área deportiva",
        "area deportiva", "zona deportiva"
    ]
    for instalacion in instalaciones:
        if instalacion in texto:
            amenidades["deportivas"]["presentes"] = True
            amenidades["deportivas"]["tipos"].append(instalacion)
    
    # Detectar amenidades adicionales
    adicionales = [
        "aire acondicionado", "calefacción", "calefaccion",
        "sistema de seguridad", "cámaras", "camaras",
        "bodega", "almacén", "almacen", "cuarto de servicio"
    ]
    for adicional in adicionales:
        if adicional in texto:
            amenidades["adicionales"].append(adicional)
    
    return amenidades

def extraer_tipo_operacion(texto, precio=None):
    """Extrae el tipo de operación con mejor detección."""
    if not texto:
        return None
        
    texto = normalizar_texto(texto)
    
    # Detectar venta
    patrones_venta = [
        r'\b(?:venta|vendo|vendemos|se\s+vende)\b',
        r'\ben\s+venta\b',
        r'\bprecio\s+de\s+venta\b',
        r'\bpropiedad\s+(?:en|de)\s+venta\b'
    ]
    
    for patron in patrones_venta:
        if re.search(patron, texto):
            return "venta"
    
    # Detectar renta
    patrones_renta = [
        r'\b(?:renta|rento|rentamos|se\s+renta)\b',
        r'\ben\s+renta\b',
        r'\bprecio\s+de\s+renta\b',
        r'\bpropiedad\s+(?:en|de)\s+renta\b',
        r'\barrendamiento\b',
        r'\balquiler\b'
    ]
    
    for patron in patrones_renta:
        if re.search(patron, texto):
            return "renta"
            
    # Si no hay mención explícita en el texto, usar el precio como criterio
    if precio:
        try:
            # Si es un diccionario, intentar obtener el valor
            if isinstance(precio, dict):
                if "valor" in precio:
                    valor_precio = float(str(precio["valor"]).replace("$", "").replace(",", "").strip())
                else:
                    return None
            else:
                valor_precio = float(str(precio).replace("$", "").replace(",", "").strip())
                
            # Si el precio es mayor a 300,000, es venta
            if valor_precio > 300000:
                return "venta"
        except (ValueError, TypeError, KeyError):
            pass
    
    # Si no hay mención explícita ni precio válido, retornar None
    return None

def es_publicacion_no_inmobiliaria(texto: str) -> bool:
    """
    Detecta si una publicación NO es sobre propiedades inmobiliarias.
    Retorna True si la publicación NO es inmobiliaria.
    """
    if not texto:
        return True
        
    texto_lower = texto.lower()
    
    # Palabras clave que indican que ES una propiedad inmobiliaria
    palabras_inmobiliarias = [
        "casa", "depto", "departamento", "terreno", "propiedad",
        "inmueble", "edificio", "local", "oficina", "bodega",
        "renta", "venta", "alquiler", "inmobiliaria", "bienes raices",
        "m2", "metros", "recamara", "habitacion", "baño",
        "cocina", "sala", "comedor", "jardin", "alberca",
        "estacionamiento", "garage", "cochera", "residencial",
        "condominio", "fraccionamiento", "privada", "hogar",
        "cabaña", "cabana", "lote", "construccion", "obra negra",
        "cisterna", "fosa", "septica", "escrituras", "ejidal",
        "cesion", "derechos", "constancia"
    ]
    
    # Palabras clave que indican ubicación
    palabras_ubicacion = [
        "cuernavaca", "morelos", "jiutepec", "temixco", "zapata",
        "yautepec", "tepoztlan", "huitzilac", "tres marias",
        "teopanzolco", "ahuatepec", "lomas", "zona norte",
        "colonia", "fraccionamiento"
    ]
    
    # Contar palabras clave
    contador_inmobiliarias = sum(1 for palabra in palabras_inmobiliarias if palabra in texto_lower)
    contador_ubicacion = sum(1 for palabra in palabras_ubicacion if palabra in texto_lower)
    
    # Si tiene al menos una palabra inmobiliaria y una de ubicación, es válida
    if contador_inmobiliarias >= 1 and contador_ubicacion >= 1:
        return False
        
    # Si tiene al menos 2 palabras inmobiliarias, es válida
    if contador_inmobiliarias >= 2:
        return False
        
    # Si menciona metros cuadrados o dimensiones, es válida
    if re.search(r'\d+\s*(?:m2|mts?2|metros?(?:\s+cuadrados?)?)', texto_lower):
        return False
        
    # Si tiene un precio alto (>$100,000) y al menos una palabra inmobiliaria o de ubicación
    precio_match = re.search(r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', texto)
    if precio_match and (contador_inmobiliarias >= 1 or contador_ubicacion >= 1):
        try:
            precio = float(precio_match.group(1).replace(',', ''))
            if precio >= 100000:  # Si el precio es mayor a $100,000
                return False
        except ValueError:
            pass
            
    # Si menciona millones y tiene al menos una palabra inmobiliaria o de ubicación
    if (contador_inmobiliarias >= 1 or contador_ubicacion >= 1) and any(palabra in texto_lower for palabra in [
        "millon", "millones", "mdp", "mill", "m.n.", "mnx"
    ]):
        return False
    
    # Patrones que indican claramente que NO es una propiedad inmobiliaria
    patrones_no_inmobiliarios = [
        r"(?:vendo|venta de|se vende|vendemos)\s+(?:celular|moto|ropa|zapatos|juguetes)",
        r"(?:rento|renta de|se renta|rentamos)\s+(?:celular|moto|ropa|zapatos|juguetes)",
        r"(?:vendo|venta de|se vende|vendemos)\s+(?:computadora|laptop|tablet|electrodomestico)",
        r"(?:rento|renta de|se renta|rentamos)\s+(?:computadora|laptop|tablet|electrodomestico)",
        r"(?:vendo|venta de|se vende|vendemos)\s+(?:mueble|sillon|cama|colchon)",
        r"(?:rento|renta de|se renta|rentamos)\s+(?:mueble|sillon|cama|colchon)",
        r"(?:vendo|venta de|se vende|vendemos)\s+(?:refrigerador|lavadora|secadora|estufa)",
        r"(?:rento|renta de|se renta|rentamos)\s+(?:refrigerador|lavadora|secadora|estufa)",
        r"(?:vendo|venta de|se vende|vendemos)\s+(?:herramienta|maquinaria|camion|trailer)",
        r"(?:rento|renta de|se renta|rentamos)\s+(?:herramienta|maquinaria|camion|trailer)",
        r"(?:servicio|servicios)\s+de\s+(?:instalacion|reparacion|mantenimiento)",
        r"(?:se hacen|hacemos|realizo|realizamos)\s+(?:instalaciones|reparaciones|mantenimiento)"
    ]
    
    # Si tiene patrones claros de otros productos/servicios, es no inmobiliaria
    if any(re.search(patron, texto_lower) for patron in patrones_no_inmobiliarios):
        return True
    
    # Si el precio es muy bajo (menos de $1000), probablemente no es inmobiliaria
    if precio_match:
        try:
            precio = float(precio_match.group(1).replace(',', ''))
            if precio < 1000:
                return True
        except ValueError:
            pass
    
    # Si tiene al menos una palabra inmobiliaria y no tiene indicadores claros de no ser inmobiliaria
    if contador_inmobiliarias > 0:
        return False
        
    # Si no podemos determinar claramente, pero tiene un precio alto (>$500,000), asumimos que es inmobiliaria
    if precio_match:
        try:
            precio = float(precio_match.group(1).replace(',', ''))
            if precio >= 500000:
                return False
        except ValueError:
            pass
    
    # Si no podemos determinar claramente, asumimos que no es inmobiliaria
    return True

def procesar_datos_crudos(archivo_entrada: str, archivo_salida: str) -> None:
    """
    Procesa los datos crudos del archivo de entrada y genera un archivo estructurado.
    
    Args:
        archivo_entrada: Ruta al archivo JSON con los datos crudos
        archivo_salida: Ruta donde se guardará el archivo JSON procesado
    """
    try:
        logger.info(f"Iniciando procesamiento de datos desde {archivo_entrada}")
        
        # Crear backup si existe el archivo de salida
        if os.path.exists(archivo_salida):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{archivo_salida}.backup_{timestamp}"
            shutil.copy2(archivo_salida, backup_path)
            logger.info(f"Backup creado en {backup_path}")
        
        # Cargar datos crudos
        with open(archivo_entrada, 'r', encoding='utf-8') as f:
            datos_crudos = json.load(f)
            
        # Inicializar estructura de salida
        propiedades_estructuradas = {
            "fecha_procesamiento": datetime.now().isoformat(),
            "total_propiedades": len(datos_crudos),
            "propiedades": [],
            "estadisticas": {
                "total_procesadas": 0,
                "total_validas": 0,
                "total_invalidas": 0,
                "tipos_propiedad": defaultdict(int),
                "tipos_operacion": defaultdict(int),
                "motivos_invalidez": defaultdict(int)
            }
        }
        
        # Procesar cada propiedad
        for id_propiedad, datos in datos_crudos.items():
            try:
                # Asegurar que el ID sea string
                id_propiedad = str(id_propiedad)
                
                # Extraer descripción según el formato
                descripcion = ""
                titulo = ""
                if isinstance(datos, dict):
                    if isinstance(datos.get("descripcion"), dict):
                        descripcion = datos["descripcion"].get("texto_original", "") or datos["descripcion"].get("texto_limpio", "")
                    elif isinstance(datos.get("descripcion"), str):
                        descripcion = datos["descripcion"]
                    
                    # Extraer título
                    if datos.get("titulo"):
                        titulo = datos["titulo"]
                        descripcion = titulo + ". " + descripcion
                
                # Validar si es una publicación inmobiliaria
                es_valida = True
                motivos_invalidez = []
                
                if es_publicacion_no_inmobiliaria(descripcion):
                    es_valida = False
                    motivo = "Publicación no relacionada con propiedades inmobiliarias"
                    motivos_invalidez.append(motivo)
                    propiedades_estructuradas["estadisticas"]["motivos_invalidez"]["no_inmobiliaria"] += 1
                    continue
                
                # Extraer precio
                precio_info = None
                if isinstance(datos, dict):
                    if "precio" in datos:
                        precio_info = datos["precio"]
                    elif "precios" in datos:
                        precio_info = datos["precios"]
                    elif "caracteristicas" in datos and isinstance(datos["caracteristicas"], dict):
                        precio_info = datos["caracteristicas"].get("precio")
                
                # Si el precio es un string o número, convertirlo a diccionario
                if isinstance(precio_info, (str, int, float)):
                    precio_info = {"valor": str(precio_info), "moneda": "MXN"}
                
                # Si no hay precio, intentar extraerlo de la descripción
                if not precio_info:
                    patrones_precio = [
                        r'\$\s*[\d,.]+\s*(?:mil|millones?)?',
                        r'(?:precio|costo|valor):\s*\$?\s*[\d,.]+\s*(?:mil|millones?)?',
                        r'[\d,.]+\s*(?:mil|millones?)\s*(?:de)?\s*pesos'
                    ]
                    for patron in patrones_precio:
                        if match := re.search(patron, descripcion, re.IGNORECASE):
                            precio_info = {"valor": match.group(0), "moneda": "MXN"}
                            break
                
                # Extraer tipo de propiedad
                tipo_prop = None
                if isinstance(datos, dict):
                    if "caracteristicas" in datos and isinstance(datos["caracteristicas"], dict):
                        tipo_prop = datos["caracteristicas"].get("tipo_propiedad")
                    if not tipo_prop and "tipo_propiedad" in datos:
                        tipo_prop = datos["tipo_propiedad"]
                
                # Si no se encontró el tipo de propiedad, intentar extraerlo del texto
                if not tipo_prop:
                    tipo_prop = extraer_tipo_propiedad(descripcion)
                
                # Si aún no hay tipo de propiedad, buscar en el título
                if not tipo_prop and titulo:
                    tipo_prop = extraer_tipo_propiedad(titulo)
                
                # Si aún no hay tipo, usar "casa" como valor por defecto si hay indicadores
                if not tipo_prop:
                    texto_completo = (titulo + " " + descripcion).lower()
                    if any(palabra in texto_completo for palabra in ["recámara", "recamara", "habitación", "habitacion", "baño", "bano", "cocina"]):
                        tipo_prop = "casa"
                    else:
                        tipo_prop = "propiedad"  # Valor por defecto si no se puede determinar
                
                # Extraer tipo de operación
                tipo_op = None
                if isinstance(datos, dict):
                    if "caracteristicas" in datos and isinstance(datos["caracteristicas"], dict):
                        tipo_op = datos["caracteristicas"].get("tipo_operacion")
                    if not tipo_op and "tipo_operacion" in datos:
                        tipo_op = datos["tipo_operacion"]
                
                # Normalizar tipo_op si es un diccionario
                if isinstance(tipo_op, dict):
                    tipo_op = tipo_op.get("tipo", None)
                
                # Si no hay tipo de operación, intentar extraerlo del texto y precio
                if not tipo_op:
                    tipo_op = extraer_tipo_operacion(descripcion, precio_info)
                
                # Si aún no hay tipo de operación, intentar inferirlo solo del precio
                if not tipo_op and precio_info:
                    try:
                        if isinstance(precio_info, dict) and "valor" in precio_info:
                            valor = float(str(precio_info["valor"]).replace("$", "").replace(",", "").strip())
                        else:
                            valor = float(str(precio_info).replace("$", "").replace(",", "").strip())
                            
                        if valor > 300000:
                            tipo_op = "venta"
                    except (ValueError, TypeError, KeyError):
                        pass
                
                # Si aún no hay tipo de operación, dejar como None
                # No asignar un valor por defecto
                
                # Crear propiedad procesada
                propiedad_procesada = {
                    "id": id_propiedad,
                    "link": str(datos.get("link", "") or datos.get("url", "")) if isinstance(datos, dict) else "",
                    "titulo": titulo,
                    "descripcion_original": descripcion,
                    "ubicacion": extraer_ubicacion_detallada(descripcion, datos.get("ubicacion", {}) if isinstance(datos, dict) else {}),
                    "propiedad": {
                        "tipo_propiedad": tipo_prop,
                        "precio": extraer_precio(precio_info),
                        "tipo_operacion": tipo_op
                    },
                    "caracteristicas": extraer_caracteristicas_detalladas(descripcion),
                    "amenidades": extraer_amenidades_detalladas(descripcion),
                    "legal": extraer_legal(descripcion),
                    "fecha_procesamiento": datetime.now().isoformat(),
                    "es_valida": es_valida,
                    "motivos_invalidez": motivos_invalidez,
                    "imagen_portada": datos.get("imagen_portada", {}),  # Mantener la información de la imagen de portada
                    "imagenes": datos.get("imagenes", []),  # Mantener el array de imágenes adicionales
                    "datos_originales": datos  # Mantener todos los datos originales sin modificar
                }
                
                # Actualizar estadísticas
                propiedades_estructuradas["estadisticas"]["total_procesadas"] += 1
                
                if es_valida:
                    propiedades_estructuradas["estadisticas"]["total_validas"] += 1
                    propiedades_estructuradas["estadisticas"]["tipos_propiedad"][tipo_prop] += 1
                    propiedades_estructuradas["estadisticas"]["tipos_operacion"][tipo_op] += 1
                else:
                    propiedades_estructuradas["estadisticas"]["total_invalidas"] += 1
                
                # Agregar propiedad a la lista
                propiedades_estructuradas["propiedades"].append(propiedad_procesada)
                
            except Exception as e:
                logger.error(f"Error procesando propiedad {id_propiedad}: {str(e)}")
                propiedades_estructuradas["estadisticas"]["total_invalidas"] += 1
                propiedades_estructuradas["estadisticas"]["motivos_invalidez"]["error_procesamiento"] += 1
                continue
        
        # Guardar resultados
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(propiedades_estructuradas, f, ensure_ascii=False, indent=2)
            
        logger.info("Procesamiento completado")
        logger.info(f"Total propiedades procesadas: {propiedades_estructuradas['estadisticas']['total_procesadas']}")
        logger.info(f"Propiedades válidas: {propiedades_estructuradas['estadisticas']['total_validas']}")
        logger.info(f"Propiedades inválidas: {propiedades_estructuradas['estadisticas']['total_invalidas']}")
        
    except Exception as e:
        logger.error(f"Error general en el procesamiento: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        # Definir rutas de archivos
        archivo_entrada = os.path.join("resultados", "repositorio_propiedades.json")
        archivo_salida = os.path.join("resultados", "propiedades_estructuradas.json")
        
        # Verificar que el archivo de entrada existe
        if not os.path.exists(archivo_entrada):
            logger.error(f"El archivo {archivo_entrada} no existe")
            sys.exit(1)
            
        # Procesar datos
        procesar_datos_crudos(archivo_entrada, archivo_salida)
    except Exception as e:
        logger.error(f"Error en main: {str(e)}")
        sys.exit(1)