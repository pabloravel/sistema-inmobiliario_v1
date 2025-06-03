#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
procesa_datos_propiedades_v4_tipo_operacion.py

Script para procesar los datos crudos extraídos y generar el repositorio
completo con todos los campos necesarios.
Esta versión mejora específicamente la detección del tipo de operación.
"""

import os
import json
import logging
import shutil
import re
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple, Union
import sys

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extraer_tipo_operacion(descripcion, precio=None, titulo=None, datos_originales=None):
    """
    Extrae el tipo de operación (venta/renta) basado en el texto y el precio.
    
    Args:
        descripcion (str): Texto de la descripción
        precio (int): Precio normalizado
        titulo (str): Título del anuncio
        datos_originales (dict): Datos originales de la propiedad
        
    Returns:
        str: 'venta' o 'renta' según corresponda
    """
    # Palabras clave para cada tipo
    palabras_venta = ['venta', 'vendo', 'vendemos', 'vende', 'venden', 'compra', 'comprar']
    palabras_renta = ['renta', 'rento', 'rentamos', 'rentan', 'alquiler', 'alquilo', 'arriendo']
    
    # Inicializar contadores
    puntos_venta = 0
    puntos_renta = 0
    
    # Normalizar textos
    descripcion = descripcion.lower() if descripcion else ''
    titulo = titulo.lower() if titulo else ''
    
    # Buscar palabras clave en descripción
    for palabra in palabras_venta:
        if palabra in descripcion:
            puntos_venta += 2
        if palabra in titulo:
            puntos_venta += 3
            
    for palabra in palabras_renta:
        if palabra in descripcion:
            puntos_renta += 2
        if palabra in titulo:
            puntos_renta += 3
    
    # Analizar precio si está disponible
    if precio:
        if 500_000 <= precio <= 50_000_000:
            puntos_venta += 2
        elif 3_000 <= precio <= 100_000:
            puntos_renta += 2
    
    # Determinar tipo basado en puntos
    if puntos_venta > puntos_renta:
        return 'venta'
    elif puntos_renta > puntos_venta:
        return 'renta'
    
    # Si no hay suficiente evidencia, usar precio como último recurso
    if precio:
        if precio >= 500_000:
            return 'venta'
        elif precio <= 100_000:
            return 'renta'
    
    # Si no se puede determinar, retornar None
    return None

def extraer_precio(texto):
    """
    Extrae el precio de un texto usando expresiones regulares.
    
    Args:
        texto (str): Texto que contiene el precio
        
    Returns:
        float: Precio extraído o None si no se encuentra
    """
    if not texto:
        return None
        
    texto = texto.lower().strip()
    
    # Patrones de precio comunes
    patrones = [
        r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $1,234.56 o $1,234
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:pesos|mxn|mnx)',  # 1,234.56 pesos
        r'(\d+(?:\.\d{2})?)\s*(?:k|mil)',  # 1.5k o 1.5 mil
        r'(\d+(?:\.\d{2})?)\s*(?:m|millones?|millón)',  # 1.5m o 1.5 millones
    ]
    
    for patron in patrones:
        match = re.search(patron, texto)
        if match:
            numero = match.group(1).replace(',', '')
            try:
                valor = float(numero)
                # Ajustar según la unidad
                if 'k' in texto or 'mil' in texto:
                    valor *= 1_000
                elif 'm' in texto or 'millon' in texto:
                    valor *= 1_000_000
                return int(valor)
            except (ValueError, TypeError):
                continue
    
    return None

# Constantes y rutas
CARPETA_DATOS_CRUDOS = "resultados/datos_crudos"
ARCHIVO_ENTRADA = "resultados/repositorio_propiedades.json"
ARCHIVO_SALIDA = "resultados/propiedades_estructuradas.json"
ARCHIVO_BACKUP = "resultados/propiedades_estructuradas.json.bak"
ARCHIVO_REPOSITORIO = "resultados/repositorio_propiedades.json"
CARPETA_REPO_MASTER = "resultados/repositorio_propiedades.json"

# Constantes de validación
RANGO_PRECIO_VENTA = (500_000, 50_000_000)  # Entre 500 mil y 50 millones
RANGO_PRECIO_RENTA = (3_000, 100_000)       # Entre 3 mil y 100 mil
RANGO_SUPERFICIE = (20, 10000)             # Rango de superficie en m2
RANGO_CONSTRUCCION = (20, 2000)            # Rango de construcción en m2
RANGO_RECAMARAS = (1, 10)                  # Rango de número de recámaras
RANGO_BANOS = (1, 6)                       # Rango de número de baños
RANGO_NIVELES = (1, 4)                     # Rango de número de niveles
RANGO_ESTACIONAMIENTOS = (0, 6)            # Rango de lugares de estacionamiento

# Palabras clave para tipo de operación
PALABRAS_VENTA = [
    "venta", "vendemos", "se vende", "en venta",
    "vendo", "remato", "oportunidad", "precio de venta",
    "precio venta", "venta de casa", "venta de departamento",
    "venta de terreno", "venta casa", "venta depto",
    "venta departamento", "venta terreno", "casa en venta",
    "depto en venta", "departamento en venta", "terreno en venta",
    "propiedad en venta", "inmueble en venta", "residencia en venta",
    "venta de propiedad", "venta de inmueble", "venta de residencia",
    "precio de contado", "acepto crédito", "acepto credito",
    "acepto infonavit", "acepto fovissste", "escrituración inmediata",
    "escrituracion inmediata"
]

PALABRAS_RENTA = [
    "renta", "rentamos", "se renta", "en renta",
    "rento", "alquiler", "alquilo", "precio de renta",
    "precio renta", "renta de casa", "renta de departamento",
    "renta de terreno", "renta casa", "renta depto",
    "renta departamento", "renta terreno", "casa en renta",
    "depto en renta", "departamento en renta", "terreno en renta",
    "propiedad en renta", "inmueble en renta", "residencia en renta",
    "renta de propiedad", "renta de inmueble", "renta de residencia",
    "precio mensual", "depósito", "deposito", "mes de depósito",
    "mes de deposito", "renta mensual", "mensualidad"
]

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

def extraer_valor_numerico(texto: str, patrones: List[str]) -> Optional[int]:
    """Extrae un valor numérico de un texto usando patrones de regex."""
    if not texto:
        return None
    
    texto = texto.lower().strip()
    
    for patron in patrones:
        if match := re.search(patron, texto):
            try:
                # Usar el primer grupo que coincida
                for i in range(1, len(match.groups()) + 1):
                    if match.group(i):
                        valor = match.group(i).replace(',', '').replace(' ', '')
                        return int(float(valor))
            except (ValueError, TypeError, IndexError):
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

def extraer_tipo_propiedad(texto):
    """Extrae el tipo de propiedad con mejor categorización."""
    if not texto:
        return None
        
    texto = normalizar_texto(texto)
    
    # Detectar departamentos primero
    caracteristicas_depto = [
        r'(?:departamento|depto|dpto|apartamento|apto)(?:\s+en\s+(?:la\s+)?(?:planta|piso|nivel))?',
        r'\d+(?:er|do|ro|to|vo|°)?(?:\s+piso|planta|nivel)',
        r'(?:piso|planta|nivel)\s+\d+',
        r'edificio',
        r'torre',
        r'elevador',
        r'penthouse',
        r'pent\s*house',
        r'loft',
        r'lobby'
    ]
    
    for patron in caracteristicas_depto:
        if re.search(patron, texto, re.IGNORECASE):
            return "departamento"

    # Detectar terrenos
    caracteristicas_terreno = [
        r'(?:terreno|lote)(?:\s+(?:plano|en\s+venta))?',
        r'metros?\s+(?:cuadrados?\s+)?(?:de\s+)?terreno',
        r'm2\s+(?:de\s+)?terreno',
        r'(?:terreno|lote)\s+(?:de|con)\s+\d+\s*m2'
    ]
    
    for patron in caracteristicas_terreno:
        if re.search(patron, texto, re.IGNORECASE):
            return "terreno"

    # Detectar casas en condominio
    caracteristicas_condominio = [
        r'casa\s+(?:en|dentro\s+de)\s+(?:condominio|privada|fraccionamiento|cluster)',
        r'fraccionamiento\s+(?:privado|residencial)',
        r'acceso\s+controlado',
        r'vigilancia\s+24(?:\/7|hrs|horas)',
        r'areas?\s+comunes',
        r'casa\s+club',
        r'amenidades'
    ]
    
    for patron in caracteristicas_condominio:
        if re.search(patron, texto, re.IGNORECASE):
            return "casa_condominio"

    # Por defecto casa sola si menciona casa
    if re.search(r'\bcasa\b', texto, re.IGNORECASE):
        return "casa_sola"

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

def extraer_estacionamientos(texto):
    """Extrae información sobre estacionamientos."""
    info = {
        "cantidad": None,
        "techado": False,
        "tipo": None  # "individual", "común", "subterráneo", etc.
    }
    
    texto = texto.lower()
    
    # Patrones para cantidad de estacionamientos
    patrones_cantidad = [
        r"(\d+)\s*(?:lugares?|cajones?|estacionamientos?)",
        r"estacionamiento\s*(?:para|de)\s*(\d+)\s*(?:autos?|coches?|carros?)",
        r"(\d+)\s*(?:autos?|coches?|carros?)\s*(?:en\s*)?(?:estacionamiento|cochera)",
        r"cochera\s*(?:para|de)\s*(\d+)\s*(?:autos?|coches?|carros?)",
        r"garage\s*(?:para|de)\s*(\d+)\s*(?:autos?|coches?|carros?)",
        r"garaje\s*(?:para|de)\s*(\d+)\s*(?:autos?|coches?|carros?)"
    ]
    
    for patron in patrones_cantidad:
        if match := re.search(patron, texto):
            try:
                cantidad = int(match.group(1))
                if 0 < cantidad <= 10:  # Validación de rango lógico
                    info["cantidad"] = cantidad
                    break
            except ValueError:
                continue
    
    # Si no se encontró cantidad pero se menciona estacionamiento
    if info["cantidad"] is None and any(palabra in texto for palabra in ["estacionamiento", "cochera", "garage", "garaje"]):
        info["cantidad"] = 1
    
    # Detectar si es techado
    info["techado"] = any(frase in texto for frase in [
        "estacionamiento techado", "cochera techada",
        "garage techado", "garaje techado",
        "estacionamiento cubierto", "cochera cubierta",
        "garage cubierto", "garaje cubierto"
    ])
    
    # Detectar tipo de estacionamiento
    if "estacionamiento común" in texto or "estacionamiento comun" in texto:
        info["tipo"] = "común"
    elif "estacionamiento subterráneo" in texto or "estacionamiento subterraneo" in texto:
        info["tipo"] = "subterráneo"
    elif "estacionamiento individual" in texto or "cochera individual" in texto:
        info["tipo"] = "individual"
    
    return info

def extraer_superficies(texto):
    """Extrae información sobre superficies de terreno y construcción."""
    info = {
        "superficie_m2": None,
        "construccion_m2": None,
        "frente_m": None,
        "fondo_m": None
    }
    
    texto = texto.lower()
    
    # Patrones para superficie total
    patrones_superficie = [
        r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?\s*cuadrados?)\s*(?:de\s*)?(?:terreno|superficie|total)",
        r"terreno\s*(?:de|con)?\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?\s*cuadrados?)",
        r"superficie\s*(?:de|con)?\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?\s*cuadrados?)",
        r"(\d+(?:[.,]\d+)?)\s*(?:x|\*)\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?\s*cuadrados?)?",
        r"lote\s*(?:de|con)?\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?\s*cuadrados?)"
    ]
    
    # Patrones para superficie construida
    patrones_construccion = [
        r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?\s*cuadrados?)\s*(?:de\s*)?construcci[oó]n",
        r"construcci[oó]n\s*(?:de|con)?\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?\s*cuadrados?)",
        r"[aá]rea\s*construida\s*(?:de|con)?\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?\s*cuadrados?)"
    ]
    
    # Buscar superficie total
    for patron in patrones_superficie:
        if match := re.search(patron, texto):
            try:
                if 'x' in patron or '*' in patron:
                    # Si es formato de multiplicación (10x20)
                    frente = float(match.group(1).replace(',', '.'))
                    fondo = float(match.group(2).replace(',', '.'))
                    info["superficie_m2"] = int(frente * fondo)
                    info["frente_m"] = frente
                    info["fondo_m"] = fondo
                else:
                    superficie = float(match.group(1).replace(',', '.'))
                    if 10 <= superficie <= 10000:  # Validación de rango lógico
                        info["superficie_m2"] = int(superficie)
                break
            except ValueError:
                continue
    
    # Buscar superficie construida
    for patron in patrones_construccion:
        if match := re.search(patron, texto):
            try:
                construccion = float(match.group(1).replace(',', '.'))
                if 20 <= construccion <= 1000:  # Validación de rango lógico
                    info["construccion_m2"] = int(construccion)
                break
            except ValueError:
                continue
    
    return info

def extraer_recamaras_y_banos(texto):
    """Extrae información sobre recámaras y baños."""
    info = {
        "recamaras": None,
        "banos": None,
        "medio_bano": None
    }
    
    texto = texto.lower()
    
    # Patrones para recámaras
    patrones_recamaras = [
        r"(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?|cuartos?)",
        r"(?:rec[aá]maras?|habitaciones?|dormitorios?|cuartos?)\s*:\s*(\d+)",
        r"(?:con|de)\s*(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?|cuartos?)"
    ]
    
    # Patrones para baños
    patrones_banos = [
        r"(\d+)\s*(?:baños?|wc|sanitarios?)",
        r"(?:baños?|wc|sanitarios?)\s*:\s*(\d+)",
        r"(?:con|de)\s*(\d+)\s*(?:baños?|wc|sanitarios?)"
    ]
    
    # Patrones para medio baño
    patrones_medio_bano = [
        r"(\d+)\s*(?:medio\s*baño|baño\s*medio)",
        r"(?:medio\s*baño|baño\s*medio)\s*:\s*(\d+)",
        r"(?:con|de)\s*(\d+)\s*(?:medio\s*baño|baño\s*medio)"
    ]
    
    # Extraer recámaras
    for patron in patrones_recamaras:
        if match := re.search(patron, texto):
            try:
                recamaras = int(match.group(1))
                if 1 <= recamaras <= 10:  # Validación de rango lógico
                    info["recamaras"] = recamaras
                    break
            except ValueError:
                continue
    
    # Extraer baños
    for patron in patrones_banos:
        if match := re.search(patron, texto):
            try:
                banos = int(match.group(1))
                if 1 <= banos <= 6:  # Validación de rango lógico
                    info["banos"] = banos
                    break
            except ValueError:
                continue
    
    # Extraer medio baño
    for patron in patrones_medio_bano:
        if match := re.search(patron, texto):
            try:
                medio_bano = int(match.group(1))
                if 0 < medio_bano <= 2:  # Validación de rango lógico
                    info["medio_bano"] = medio_bano
                    break
            except ValueError:
                continue
    
    return info

def extraer_niveles(texto):
    """Extrae información sobre niveles de la propiedad."""
    info = {
        "niveles": None,
        "un_nivel": False,
        "tiene_planta_alta": False,
        "opcion_crecer": False
    }
    
    texto = texto.lower()
    
    # Patrones para niveles
    patrones_niveles = [
        r"(\d+)\s*(?:niveles?|pisos?|plantas?)",
        r"(?:de|con)\s*(\d+)\s*(?:niveles?|pisos?|plantas?)",
        r"(?:niveles?|pisos?|plantas?)\s*:\s*(\d+)"
    ]
    
    # Buscar niveles
    for patron in patrones_niveles:
        if match := re.search(patron, texto):
            try:
                niveles = int(match.group(1))
                if 1 <= niveles <= 10:  # Validación de rango lógico
                    info["niveles"] = niveles
                    if niveles == 1:
                        info["un_nivel"] = True
                    break
            except ValueError:
                continue
    
    # Detectar si es de un nivel por otras menciones
    if info["niveles"] is None:
        un_nivel_frases = [
            "un nivel", "una planta", "planta baja",
            "todo en planta baja", "todo en un nivel"
        ]
        info["un_nivel"] = any(frase in texto for frase in un_nivel_frases)
        if info["un_nivel"]:
            info["niveles"] = 1
    
    # Detectar si tiene planta alta
    planta_alta_frases = [
        "planta alta", "segundo piso", "segunda planta",
        "piso superior", "nivel superior"
    ]
    info["tiene_planta_alta"] = any(frase in texto for frase in planta_alta_frases)
    
    # Si tiene planta alta, no puede ser de un nivel
    if info["tiene_planta_alta"]:
        info["un_nivel"] = False
        if info["niveles"] is None or info["niveles"] < 2:
            info["niveles"] = 2
    
    # Detectar opción para crecer
    crecer_frases = [
        "opción a crecer", "opcion a crecer",
        "posibilidad de crecer", "se puede crecer",
        "preparada para crecer", "preparado para crecer",
        "oportunidad de crecer", "espacio para crecer",
        "puede crecer", "posibilidad de ampliar",
        "se puede ampliar", "opción de ampliar",
        "opcion de ampliar"
    ]
    info["opcion_crecer"] = any(frase in texto for frase in crecer_frases)
    
    return info

def procesar_propiedad(datos):
    """
    Procesa una propiedad individual y extrae toda la información relevante.
    
    Args:
        datos (dict): Diccionario con los datos crudos de la propiedad
        
    Returns:
        dict: Diccionario con los datos procesados y estructurados
    """
    if not isinstance(datos, dict):
        return None
        
    # Extraer campos básicos
    descripcion = datos.get('descripcion', '')
    titulo = datos.get('titulo', '')
    precio_texto = datos.get('precio', '')
    
    # Asegurarse de que los campos de texto sean strings
    descripcion = str(descripcion) if descripcion else ''
    titulo = str(titulo) if titulo else ''
    precio_texto = str(precio_texto) if precio_texto else ''
    
    # Normalizar textos
    descripcion_norm = normalizar_texto(descripcion)
    titulo_norm = normalizar_texto(titulo)
    
    # Procesar precio
    precio = extraer_precio(precio_texto)
    
    # Extraer tipo de operación
    tipo_operacion = extraer_tipo_operacion(
        descripcion_norm,
        precio=precio,
        titulo=titulo_norm,
        datos_originales=datos
    )
    
    # Validar precio según tipo de operación
    if not es_precio_valido(precio, tipo_operacion):
        precio = None
    
    # Extraer características detalladas
    caracteristicas = extraer_caracteristicas_detalladas(
        descripcion_norm,
        datos.get('caracteristicas', {})
    )
    
    # Extraer ubicación
    ubicacion = extraer_ubicacion_detallada(
        descripcion_norm,
        datos.get('ubicacion', {})
    )
    
    # Extraer tipo de propiedad
    tipo_propiedad = extraer_tipo_propiedad(descripcion_norm)
    
    # Extraer amenidades
    amenidades = extraer_amenidades(descripcion_norm)
    
    # Extraer información legal
    legal = extraer_legal(descripcion_norm)
    
    # Construir resultado
    resultado = {
        'id': datos.get('id'),
        'titulo': titulo,
        'descripcion': descripcion,
        'precio': precio,
        'tipo_operacion': tipo_operacion,
        'tipo_propiedad': tipo_propiedad,
        'caracteristicas': caracteristicas,
        'ubicacion': ubicacion,
        'amenidades': amenidades,
        'legal': legal,
        'link': datos.get('link'),
        'imagen_portada': datos.get('imagen_portada'),
        'fecha_procesamiento': datetime.now().isoformat()
    }
    
    return resultado

if __name__ == "__main__":
    # Configuración de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('resultados/procesa_propiedades.log'),
            logging.StreamHandler()
        ]
    )
    
    try:
        # Cargar datos de propiedades
        with open(ARCHIVO_ENTRADA, 'r', encoding='utf-8') as f:
            datos_propiedades = json.load(f)
        
        # Procesar cada propiedad
        resultados = []
        for id_propiedad, propiedad in datos_propiedades.items():
            try:
                resultado = procesar_propiedad(propiedad)
                if resultado:
                    # Agregar el ID de la propiedad al resultado
                    resultado["id"] = id_propiedad
                    resultados.append(resultado)
            except Exception as e:
                logging.error(f"Error procesando propiedad {id_propiedad}: {str(e)}")
                continue
        
        # Crear backup si existe el archivo de salida
        if os.path.exists(ARCHIVO_SALIDA):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{ARCHIVO_BACKUP}.{timestamp}"
            shutil.copy2(ARCHIVO_SALIDA, backup_path)
            logging.info(f"Backup creado en {backup_path}")
        
        # Guardar resultados
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            json.dump({
                "fecha_procesamiento": datetime.now().isoformat(),
                "total_propiedades": len(resultados),
                "propiedades": resultados
            }, f, ensure_ascii=False, indent=2)
        
        logging.info(f"Procesamiento completado. {len(resultados)} propiedades procesadas.")
        
    except Exception as e:
        logging.error(f"Error en el proceso principal: {str(e)}")
        raise 