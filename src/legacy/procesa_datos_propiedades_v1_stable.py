#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
procesa_datos_propiedades.py

Script para procesar los datos crudos extraídos y generar el repositorio
completo con todos los campos necesarios.
"""

import os
import json
from datetime import datetime
import re
from typing import Dict, List, Optional, Tuple, Union
import logging
import shutil
import time
from collections import defaultdict

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    
    # Primero detectar si es departamento por menciones específicas
    caracteristicas_depto = [
        "departamento", "depto", "apartamento", "apto",
        "elevador", "piso", "nivel", "edificio", "torre",
        "penthouse", "pent house", "loft"
    ]
    
    # Patrones específicos que indican que es departamento
    patrones_depto = [
        r"\d+(?:er|do|ro|to|vo|°)?\s*piso",  # 1er piso, 2do piso, 3er piso, etc
        r"piso\s+\d+",  # piso 1, piso 2, etc
        r"nivel\s+\d+",  # nivel 1, nivel 2, etc
        r"\d+\s*°\s*piso"  # 1° piso, 2° piso, etc
    ]
    
    # Si tiene características de departamento o coincide con los patrones
    if any(x in texto for x in caracteristicas_depto) or any(re.search(patron, texto) for patron in patrones_depto):
        return "departamento"
    
    # Detectar si es una casa por sus características
    caracteristicas_casa = [
        # Distribución y espacios
        "planta baja", "planta alta", "recamara", "habitacion",
        "sala comedor", "cocina integral", "cocina equipada",
        "sotano", "sótano", "niveles", "pisos", "plantas",
        "vestidor", "closet", "baño completo", "medio baño",
        "cuarto de tv", "family room", "cuarto de lavado",
        # Amenidades
        "terraza", "jardín", "jardin", "alberca", "piscina",
        "cochera", "garage", "estacionamiento",
        # Descripciones directas
        "casa en venta", "casa en preventa", "casa nueva",
        "casa moderna", "casa equipada", "casa lista",
        "preciosa casa", "hermosa casa", "bonita casa",
        # Construcción
        "construcción de", "construccion de", "m2 de construcción",
        "metros de construcción", "m2 construidos"
    ]
    
    caracteristicas_condominio = [
        "fraccionamiento", "fracc", "privada", "condominio",
        "vigilancia 24", "seguridad 24", "acceso controlado",
        "areas comunes", "áreas comunes", "casa club",
        "burgos", "sumiya", "kloster", "vista hermosa"
    ]
    
    # Si tiene características de casa
    if any(x in texto for x in caracteristicas_casa):
        # Verificar si es casa en condominio
        if any(x in texto for x in caracteristicas_condominio):
            return "casa_condominio"
        return "casa_sola"
    
    # Solo si no tiene características de casa o departamento, verificar si es terreno
    caracteristicas_terreno = [
        "terreno baldio", "lote baldio", "sin construccion",
        "terreno para construir", "lote para construir",
        "terreno uso habitacional", "terreno comercial",
        "terreno industrial", "lote sin construccion",
        "terreno plano", "terreno bardeado"
    ]
    
    # Verificar que NO tenga características de construcción
    caracteristicas_construccion = [
        "construccion", "construcción", "casa", "departamento",
        "cocina", "baño", "recamara", "sala", "comedor",
        "habitacion", "habitación", "closet", "vestidor"
    ]
    
    if (any(x in texto for x in caracteristicas_terreno) and 
        not any(x in texto for x in caracteristicas_construccion)):
        # Verificar si menciona metros de terreno pero también de construcción
        if "m2 de terreno" in texto or "metros de terreno" in texto:
            if "m2 de construccion" in texto or "metros de construccion" in texto:
                # Si menciona ambos, no es un terreno
                return "casa_sola"
        return "terreno"
    
    # Si no se puede determinar con certeza, buscar más pistas
    if "casa" in texto.lower():
        # Si menciona casa y está en un fraccionamiento/condominio
        if any(x in texto for x in caracteristicas_condominio):
            return "casa_condominio"
        return "casa_sola"
    
    return None

def extraer_amenidades(texto):
    """Extrae las amenidades de la propiedad."""
    return {
        "seguridad": any(word in texto.lower() for word in ["seguridad", "vigilancia", "24/7", "caseta"]),
        "alberca": any(word in texto.lower() for word in ["alberca", "piscina", "chapuzón", "pool"]),
        "patio": "patio" in texto.lower(),
        "bodega": any(word in texto.lower() for word in ["bodega", "almacén", "storage"]),
        "terraza": any(word in texto.lower() for word in ["terraza", "balcón"]),
        "jardin": any(word in texto.lower() for word in ["jardín", "jardin", "área verde"]),
        "estudio": any(word in texto.lower() for word in ["estudio", "oficina", "despacho"]),
        "roof_garden": any(word in texto.lower() for word in ["roof", "rooftop", "terraza en azotea"])
    }

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
    
    # Patrones comunes en México
    patrones = [
        # 1,234,567.89 o 1234567.89
        r"^\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|\d+(?:\.\d{1,2})?)$",
        # 1.234.567,89 o 1234567,89 (formato europeo)
        r"^\$?\s*(\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?|\d+(?:,\d{1,2})?)$",
        # Números sin separadores
        r"^\$?\s*(\d+)$",
        # Números con K o M
        r"^\$?\s*(\d+(?:\.\d+)?)\s*[kK]$",
        r"^\$?\s*(\d+(?:\.\d+)?)\s*[mM]$"
    ]
    
    for patron in patrones:
        match = re.match(patron, texto)
        if match:
            numero = match.group(1)
            
            # Manejar K (miles) y M (millones)
            if texto.strip().lower().endswith('k'):
                numero = float(numero.replace(",", "")) * 1000
            elif texto.strip().lower().endswith('m'):
                numero = float(numero.replace(",", "")) * 1000000
            else:
                # Formato mexicano (1,234,567.89)
                if "," in numero and "." in numero:
                    numero = numero.replace(",", "")
                # Formato europeo (1.234.567,89)
                elif "," in numero and "." not in numero:
                    numero = numero.replace(".", "").replace(",", ".")
                # Sin separadores o solo punto decimal
                else:
                    numero = numero.replace(",", "")
                    
            try:
                valor = float(numero)
                # Validar rangos razonables
                if 100 <= valor <= 100_000_000:  # Entre $100 y $100M
                    return valor
            except ValueError:
                continue
    
    return None

def extraer_precio(texto: str) -> Dict:
    """Extrae el precio original del texto sin procesarlo."""
    if not texto:
        return {
            "valor": None,
            "valor_normalizado": None,
            "moneda": None,
            "es_valido": False,
            "confianza": 0.0,
            "periodo": None,
            "mensaje": "Texto vacío"
        }
    
    # Si el texto es un string directo (como viene en el archivo original)
    if isinstance(texto, str):
        return {
            "valor": texto,  # Mantener el texto exactamente como está
            "valor_normalizado": None,
            "moneda": "MXN" if "$" in texto else None,
            "es_valido": True,
            "confianza": 1.0,
            "periodo": None,
            "mensaje": ""
        }
    
    # Si el texto es un diccionario, buscar el precio en el campo precio.texto_original
    if isinstance(texto, dict):
        try:
            if "precio" in texto:
                precio_dict = texto["precio"]
                if isinstance(precio_dict, dict):
                    # Mantener el texto original exactamente como está
                    texto_original = precio_dict.get("texto_original")
                    if texto_original:
                        return {
                            "valor": texto_original,  # Usar el texto original sin procesar
                            "valor_normalizado": precio_dict.get("valor"),  # Mantener el valor normalizado si existe
                            "moneda": precio_dict.get("moneda", "MXN"),
                            "es_valido": True,
                            "confianza": 1.0,
                            "periodo": None,
                            "mensaje": ""
                        }
        except:
            pass
    
    return {
        "valor": str(texto),  # Convertir a string y mantener como está
        "valor_normalizado": None,
        "moneda": None,
        "es_valido": True,
        "confianza": 1.0,
        "periodo": None,
        "mensaje": ""
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
        r"departamento\s*(?:de|con)\s*(\d+)\s*(?:rec[aá]maras?|habitaciones?)"
    ]
    
    # Patrones para baños completos
    patrones_banos = [
        r"(\d+(?:\.5)?)\s*(?:baños?|sanitarios?|wc)",
        r"(?:baños?|sanitarios?)\\s*:\\s*(\\d+(?:\\.5)?)",
        r"(?:con|tiene)\s*(\d+(?:\.5)?)\s*(?:baños?|sanitarios?)",
        r"(\d+)\s*(?:baño completo|b\.?c\.?)",
        r"(\d+)\s*(?:baños?\s*completos?)",
        r"casa\s*(?:de|con)\s*(\d+(?:\.5)?)\s*(?:baños?)",
        r"departamento\s*(?:de|con)\s*(\d+(?:\.5)?)\s*(?:baños?)"
    ]
    
    # Patrones para medios baños
    patrones_medio_bano = [
        r"(\d+)\s*(?:medio\s*baño|baño\s*medio)",
        r"(\d+)\s*(?:m\.?\s*b\.?|b\.?\s*m\.?)",
        r"(?:con|tiene)\s*(\d+)\s*(?:medio\s*baño|baño\s*medio)",
        r"(?:y|más)\s*(\d+)\s*(?:medio\s*baño|baño\s*medio)",
        r"(\d+)\s*(?:sanitario\s*medio|wc\s*medio)"
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
    
    # Buscar baños completos
    for patron in patrones_banos:
        if match := re.search(patron, texto):
            try:
                valor = float(match.group(1))
                parte_entera = int(valor)
                parte_decimal = valor - parte_entera
                
                if 1 <= parte_entera <= 6:  # Validación de rango lógico
                    resultado["banos"] = parte_entera
                    if parte_decimal == 0.5:
                        resultado["medio_bano"] = 1
                    break
            except ValueError:
                continue
    
    # Buscar medios baños específicamente
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
        r"estacionamiento\s*(?:para|con)?\s*(\d+)\s*(?:autos?|carros?|coches?)\s*(?:cubiertos?|techados?)"
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
        "con garage bajo techo", "con estacionamiento con techo"
    ]):
        return {
            "cantidad": 1,
            "techado": any(palabra in texto for palabra in [
                "techado", "techada", "cubierto", "cubierta",
                "bajo techo", "techo", "tejado", "cubiertos",
                "techados", "cubiertas", "techadas"
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
    texto = texto.lower()
    resultado = {
        "superficie_m2": None,
        "construccion_m2": None
    }
    
    # Patrones para superficie de terreno
    patrones_superficie = [
        r"(?:superficie|terreno)(?:\s+de)?:?\s*(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)",
        r"(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)\s*(?:de\s*terreno|superficie)",
        r"lote\s*(?:de)?\s*(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)",
        r"(\d+(?:\.\d+)?)\s*mt2\s*(?:de\s*terreno)?",
        r"terreno\s*(?:de|con)\s*(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)",
        r"(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)\s*totales?"
    ]
    
    # Patrones para superficie de construcción
    patrones_construccion = [
        r"(?:construcción|construccion)(?:\s+de)?:?\s*(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)",
        r"(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)\s*(?:de\s*construcción|de\s*construccion)",
        r"(?:área|area)\s*(?:construida|habitable)(?:\s+de)?:?\s*(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)",
        r"(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)\s*construidos?",
        r"construcci[oó]n\s*(?:de|con)\s*(\d+(?:\.\d+)?)\s*(?:m2|metros?|mt2)"
    ]
    
    # Buscar superficie de terreno
    for patron in patrones_superficie:
        if match := re.search(patron, texto):
            try:
                valor = float(match.group(1))
                if 20 <= valor <= 10000:  # Validación de rango lógico
                    resultado["superficie_m2"] = valor
                    break
            except ValueError:
                continue
    
    # Buscar superficie de construcción
    for patron in patrones_construccion:
        if match := re.search(patron, texto):
            try:
                valor = float(match.group(1))
                if 20 <= valor <= 2000:  # Validación de rango lógico para construcción
                    resultado["construccion_m2"] = valor
                    break
            except ValueError:
                continue
    
    # Si no se encontró superficie de construcción pero hay superficie total,
    # y es una casa o departamento, asumir que es la superficie construida
    if (resultado["construccion_m2"] is None and 
        resultado["superficie_m2"] is not None and 
        any(tipo in texto for tipo in ["casa", "depto", "departamento"]) and
        resultado["superficie_m2"] <= 500):  # Límite razonable para vivienda
        resultado["construccion_m2"] = resultado["superficie_m2"]
        resultado["superficie_m2"] = None
    
    return resultado

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
    """
    Extrae amenidades detalladas de la propiedad.
    """
    texto = normalizar_texto(texto)
    
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

def extraer_tipo_operacion(texto: str) -> str:
    """Extrae el tipo de operación (venta/renta) del texto."""
    texto = texto.lower()
    
    # Palabras clave para venta
    if any(palabra in texto for palabra in [
        "venta", "vendo", "vendemos", "se vende",
        "precio de venta", "costo de venta", "valor de venta",
        "oportunidad de compra", "precio de contado"
    ]):
        return "venta"
    
    # Palabras clave para renta
    if any(palabra in texto for palabra in [
        "renta", "alquiler", "arriendo", "se renta",
        "se alquila", "en renta", "rento", "rentamos",
        "precio mensual", "renta mensual", "costo mensual"
    ]):
        return "renta"
    
    # Si no se encuentra un tipo claro, intentar inferir por el precio
    precio_info = extraer_precio(texto)
    if precio_info and precio_info["valor"]:
        # Intentar extraer el valor numérico del precio
        valor_str = precio_info["valor"]
        if isinstance(valor_str, str):
            # Limpiar el string de precio
            valor_str = valor_str.replace("$", "").replace(",", "").replace(".", "").strip()
            try:
                valor = float(valor_str)
                if valor >= 300000:  # Si el precio es mayor a $300,000
                    return "venta"
                elif valor <= 100000:  # Precios más bajos son renta
                    return "renta"
            except ValueError:
                pass
    
    return None

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
                "errores": {},
                "tipos_propiedad": {},
                "tipos_operacion": {}
            }
        }
        
        logger.info(f"Procesando {len(datos_crudos)} propiedades...")
        
        # Procesar cada propiedad
        for id_propiedad, datos in datos_crudos.items():
            try:
                logger.debug(f"Procesando propiedad {id_propiedad}")
                
                # Extraer precio según el formato
                precio_info = None
                if "precio" in datos:
                    # Si el precio viene como string directo
                    if isinstance(datos["precio"], str):
                        precio_info = extraer_precio(datos["precio"])
                    # Si viene como diccionario
                    elif isinstance(datos["precio"], dict):
                        precio_info = extraer_precio(datos["precio"])
                    else:
                        precio_info = extraer_precio(str(datos["precio"]))
                elif "precios" in datos:
                    precio_info = extraer_precio(datos["precios"])
                
                if not precio_info:
                    precio_info = {
                        "valor": None,
                        "valor_normalizado": None,
                        "moneda": None,
                        "es_valido": False,
                        "confianza": 0,
                        "periodo": None,
                        "mensaje": "Formato de precio no reconocido"
                    }
                
                # Extraer descripción según el formato
                descripcion = ""
                if isinstance(datos.get("descripcion"), dict):
                    descripcion = datos["descripcion"].get("texto_original", "") or datos["descripcion"].get("texto_limpio", "")
                elif isinstance(datos.get("descripcion"), str):
                    descripcion = datos["descripcion"]
                
                # Agregar título si existe
                if datos.get("titulo"):
                    descripcion = datos["titulo"] + ". " + descripcion
                
                # Extraer tipo de propiedad
                tipo_prop = None
                if "caracteristicas" in datos and datos["caracteristicas"].get("tipo_propiedad"):
                    tipo_prop = datos["caracteristicas"]["tipo_propiedad"].lower()
                else:
                    tipo_prop = extraer_tipo_propiedad(descripcion)
                
                # Extraer tipo de operación
                tipo_op = None
                if "caracteristicas" in datos and datos["caracteristicas"].get("tipo_operacion"):
                    tipo_op = datos["caracteristicas"]["tipo_operacion"].lower()
                elif "precios" in datos and datos["precios"].get("tipo"):
                    tipo_op = datos["precios"]["tipo"].lower()
                else:
                    tipo_op = extraer_tipo_operacion(descripcion)
                
                # Procesar la ubicación
                ubicacion_procesada = extraer_ubicacion_detallada(descripcion, datos.get("ubicacion", {}))
                
                # Crear propiedad procesada
                propiedad_procesada = {
                    "id": id_propiedad,
                    "link": str(datos.get("link", "") or datos.get("url", "")),
                    "descripcion_original": descripcion,
                    "ubicacion": ubicacion_procesada,
                    "propiedad": {
                        "tipo_propiedad": tipo_prop,
                        "precio": precio_info,
                        "tipo_operacion": tipo_op
                    },
                    "caracteristicas": extraer_caracteristicas_detalladas(descripcion),
                    "amenidades": extraer_amenidades_detalladas(descripcion),
                    "legal": extraer_legal(descripcion),
                    "fecha_procesamiento": datetime.now().isoformat()
                }
                
                # Validar propiedad
                es_valida = True
                motivos_invalidez = []
                
                if not tipo_prop:
                    es_valida = False
                    motivos_invalidez.append("Tipo de propiedad no identificado")
                
                if not precio_info["valor"]:
                    es_valida = False
                    motivos_invalidez.append("Precio no identificado")
                elif not precio_info["es_valido"]:
                    es_valida = False
                    motivos_invalidez.append("Precio inválido")
                
                if not tipo_op:
                    es_valida = False
                    motivos_invalidez.append("Tipo de operación no identificado")
                
                # Actualizar estadísticas
                propiedades_estructuradas["estadisticas"]["total_procesadas"] += 1
                
                if es_valida:
                    propiedades_estructuradas["estadisticas"]["total_validas"] += 1
                    if tipo_prop:
                        propiedades_estructuradas["estadisticas"]["tipos_propiedad"][tipo_prop] = \
                            propiedades_estructuradas["estadisticas"]["tipos_propiedad"].get(tipo_prop, 0) + 1
                    if tipo_op:
                        propiedades_estructuradas["estadisticas"]["tipos_operacion"][tipo_op] = \
                            propiedades_estructuradas["estadisticas"]["tipos_operacion"].get(tipo_op, 0) + 1
                else:
                    propiedades_estructuradas["estadisticas"]["total_invalidas"] += 1
                    for motivo in motivos_invalidez:
                        propiedades_estructuradas["estadisticas"]["errores"][motivo] = \
                            propiedades_estructuradas["estadisticas"]["errores"].get(motivo, 0) + 1
                
                propiedades_estructuradas["propiedades"].append(propiedad_procesada)
                logger.debug(f"Propiedad {id_propiedad} procesada exitosamente")
                
            except Exception as e:
                logger.error(f"Error procesando propiedad {id_propiedad}: {str(e)}")
                propiedades_estructuradas["estadisticas"]["errores"][str(type(e).__name__)] = \
                    propiedades_estructuradas["estadisticas"]["errores"].get(str(type(e).__name__), 0) + 1
        
        # Guardar resultados
        os.makedirs(os.path.dirname(archivo_salida), exist_ok=True)
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(propiedades_estructuradas, f, ensure_ascii=False, indent=2)
        
        logger.info("Procesamiento completado")
        logger.info(f"Total propiedades procesadas: {propiedades_estructuradas['estadisticas']['total_procesadas']}")
        logger.info(f"Propiedades válidas: {propiedades_estructuradas['estadisticas']['total_validas']}")
        logger.info(f"Propiedades inválidas: {propiedades_estructuradas['estadisticas']['total_invalidas']}")
        
    except Exception as e:
        logger.error(f"Error general en procesar_datos_crudos: {str(e)}")
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