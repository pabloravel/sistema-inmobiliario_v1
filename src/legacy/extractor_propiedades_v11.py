#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extractor_propiedades_v11.py

Versión 11.0 - Optimizada para extracción masiva y validación de datos
- Sistema de timeout por propiedad
- Verificación eficiente de propiedades ya extraídas
- Guardado completo de datos (DOM, JSON, HTML, imágenes)
- Optimización de tiempos de espera
- Validación y normalización de datos
"""

import os
import json
import requests
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple
from dataclasses import dataclass, field, asdict
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuración de rutas
CARPETA_LINKS = "resultados/links/repositorio_unico.json"
CARPETA_RESULTADOS = "resultados"
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
CARPETA_IMAGENES = os.path.join(CARPETA_RESULTADOS, "imagenes")
ESTADO_FB = "fb_state.json"
BASE_URL = "https://www.facebook.com"

# Estados de propiedades
ESTADO_DISPONIBLE = "disponible"
ESTADO_NO_DISPONIBLE = "no_disponible"
ESTADO_PENDIENTE = "pendiente"
ESTADO_ERROR = "error"
ESTADO_VENDIDO = "vendido"
ESTADO_RENTADO = "rentado"

# Configuración de extracción
MAX_IMAGENES = 1  # Número máximo de imágenes a guardar por propiedad
GUARDAR_HTML = False  # Si se debe guardar el HTML completo
GUARDAR_DOM = False  # Si se debe guardar el DOM
GUARDAR_JSON = True  # Si se debe guardar el JSON de datos
DIAS_ACTUALIZACION = 2  # Días para actualizar una propiedad

# Timeouts y reintentos
TIMEOUT_PROPIEDAD = 60  # Segundos máximos por propiedad
MAX_REINTENTOS = 3  # Número máximo de reintentos por propiedad
ESPERA_ENTRE_REINTENTOS = 5  # Segundos entre reintentos

# Rangos de precios válidos (en MXN)
PRECIO_MIN_RENTA = 1_000  # Mínimo para renta mensual
PRECIO_MAX_RENTA = 100_000  # Máximo para renta mensual
PRECIO_MIN_VENTA = 100_000  # Mínimo para venta
PRECIO_MAX_VENTA = 50_000_000  # Máximo para venta

# Catálogos y patrones
COLONIAS_CONOCIDAS = [
    "Lomas de Cortés", "Acapantzingo", "Delicias", "Reforma", 
    "Vista Hermosa", "Palmira", "Tlaltenango", "Amatitlán",
    "Chapultepec", "Bellavista", "Las Palmas", "Rancho Cortés",
    "Jardines de Cuernavaca", "La Pradera", "Maravillas"
]

TIPOS_PROPIEDAD = {
    "casa": ["casa sola", "casa", "casa habitación", "residencia", "casa en condominio", "casa en privada"],
    "departamento": ["departamento", "depto", "departamentos", "depa"],
    "terreno": ["terreno", "lote", "terrenos", "predio"],
    "local": ["local", "locales", "local comercial"],
    "oficina": ["oficina", "oficinas"],
    "bodega": ["bodega", "bodegas", "almacén"],
    "villa": ["villa", "villas"],
    "hotel": ["hotel", "hoteles"]
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
        self.pend = 0
        self.last_time = 0.0
        self.desc = desc
        self.unit = unit
        self.length = 40
        self._print()
    
    def _print(self):
        filled = int(self.length * self.n / self.total) if self.total else self.length
        bar = '█' * filled + '-' * (self.length - filled)
        pct = (self.n / self.total * 100) if self.total else 100
        print(f"\r{self.desc}: {pct:3.0f}%|"
              f"{self.MAGENTA}{bar}{self.RESET}| "
              f"{self.n}/{self.total} "
              f"[OK:{self.ok} Err:{self.err} Pend:{self.pend} t:{self.last_time:.2f}s]",
              end='', flush=True)
    
    def update(self, n: int = 1, ok: int = None, err: int = None, pend: int = None, last_time: float = None):
        self.n += n
        if ok is not None: self.ok = ok
        if err is not None: self.err = err
        if pend is not None: self.pend = pend
        if last_time is not None: self.last_time = last_time
        self._print()
    
    def close(self):
        print()

@dataclass
class Precio:
    """Clase para manejar precios de propiedades"""
    valor: str = "0"  # Ahora es string en lugar de float
    moneda: str = "MXN"
    texto_original: str = ""
    incluye_mantenimiento: bool = False
    cuota_mantenimiento: float = 0.0
    
    def es_valido(self) -> bool:
        """Verifica si el precio está en un rango válido"""
        try:
            valor_num = float(self.valor)
            if valor_num <= 0:
                return False
            
            # Validar según el rango de precios
            if "USD" in self.moneda:
                valor_num *= 20  # Conversión aproximada a MXN
            elif "EUR" in self.moneda:
                valor_num *= 24  # Conversión aproximada a MXN
            
            # Detectar si es renta por el texto original
            es_renta = any(x in self.texto_original.lower() 
                          for x in ["renta", "mes", "mensual"])
            
            if es_renta:
                return PRECIO_MIN_RENTA <= valor_num <= PRECIO_MAX_RENTA
            return PRECIO_MIN_VENTA <= valor_num <= PRECIO_MAX_VENTA
        except ValueError:
            return False

@dataclass
class Ubicacion:
    """Clase para manejar ubicaciones"""
    colonia: str = ""
    calle: str = ""
    estado: str = "Morelos"
    ciudad: str = "Cuernavaca"
    referencias: List[str] = field(default_factory=list)
    coordenadas: Dict[str, Optional[float]] = field(
        default_factory=lambda: {"latitud": None, "longitud": None}
    )
    zona: str = ""
    fraccionamiento: str = ""
    codigo_postal: str = ""
    
    def tiene_ubicacion_valida(self) -> bool:
        """Verifica si tiene suficiente información de ubicación"""
        return bool(
            self.colonia or 
            self.fraccionamiento or 
            self.zona or 
            (self.coordenadas["latitud"] and self.coordenadas["longitud"])
        )

@dataclass
class Caracteristicas:
    """Clase para manejar características de la propiedad"""
    tipo_propiedad: str = ""
    tipo_operacion: str = ""
    recamaras: int = 0
    banos: float = 0.0
    niveles: int = 0
    un_nivel: bool = False
    superficie_m2: float = 0.0
    construccion_m2: float = 0.0
    recamara_pb: bool = False
    cisterna: Dict[str, Union[bool, int]] = field(
        default_factory=lambda: {"tiene": False, "capacidad": 0}
    )
    apto_discapacitados: bool = False
    estacionamientos: int = 0
    edad: str = ""
    estado_conservacion: str = ""
    
    def tiene_datos_basicos(self) -> bool:
        """Verifica si tiene los datos mínimos necesarios"""
        return bool(
            self.tipo_propiedad and
            self.tipo_operacion and
            (self.superficie_m2 > 0 or self.construccion_m2 > 0)
        )

@dataclass
class Amenidades:
    """Clase para manejar amenidades de la propiedad"""
    seguridad: bool = False
    alberca: bool = False
    patio: bool = False
    bodega: bool = False
    terraza: bool = False
    jardin: bool = False
    estudio: bool = False
    roof_garden: bool = False
    gimnasio: bool = False
    area_juegos: bool = False
    salon_usos_multiples: bool = False
    area_lavado: bool = False
    cocina_integral: bool = False
    cuarto_servicio: bool = False
    
    def contar_amenidades(self) -> int:
        """Cuenta el número de amenidades presentes"""
        return sum(1 for v in asdict(self).values() if v)

@dataclass
class Legal:
    """Clase para manejar aspectos legales"""
    escrituras: bool = False
    cesion_derechos: bool = False
    predial_corriente: bool = False
    servicios_pagados: bool = False
    libre_gravamen: bool = False
    formas_pago: List[str] = field(default_factory=list)
    
    def tiene_documentacion(self) -> bool:
        """Verifica si tiene documentación básica"""
        return self.escrituras or self.cesion_derechos

@dataclass
class Vendedor:
    """Clase para manejar información del vendedor"""
    nombre: str = ""
    perfil: str = ""
    tipo: str = "desconocido"  # particular, inmobiliaria, desconocido
    telefono: str = ""
    correo: str = ""
    otros_anuncios: List[str] = field(default_factory=list)
    
    def es_valido(self) -> bool:
        """Verifica si tiene información válida del vendedor"""
        return bool(self.nombre and self.perfil)

@dataclass
class EstadoPropiedad:
    """Clase para manejar el estado de una propiedad"""
    estado: str = ESTADO_DISPONIBLE
    ultima_revision: str = field(default_factory=lambda: datetime.now().isoformat())
    intentos: int = 0
    error_mensaje: str = ""
    fecha_cambio_estado: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def actualizar_estado(self, nuevo_estado: str, mensaje: str = ""):
        self.estado = nuevo_estado
        self.ultima_revision = datetime.now().isoformat()
        self.intentos += 1
        self.error_mensaje = mensaje
        self.fecha_cambio_estado = datetime.now().isoformat()
    
    def debe_reintentar(self) -> bool:
        if self.estado == ESTADO_ERROR and self.intentos < 3:
            return True
        if self.estado == ESTADO_PENDIENTE and self.intentos < 5:
            return True
        return False

def normalizar_texto(texto: str) -> str:
    """Normaliza un texto eliminando caracteres especiales y espacios extras"""
    if not texto:
        return ""
    # Eliminar caracteres especiales excepto puntuación básica
    texto = re.sub(r'[^\w\s.,;:()¿?¡!-]', '', texto)
    # Normalizar espacios
    texto = ' '.join(texto.split())
    return texto.lower()

def normalizar_precio(texto: str) -> Dict[str, Union[float, str, bool]]:
    """
    Normaliza el precio de una propiedad.
    Guarda el valor como string sin decimales.
    """
    if not texto:
        return {
            "valor": "0",
            "moneda": "MXN",
            "texto_original": "",
            "incluye_mantenimiento": False,
            "cuota_mantenimiento": 0.0
        }
    
    # Guardar el texto original
    texto_original = texto.strip()
    
    # Detectar moneda
    moneda = "MXN"
    if "usd" in texto.lower() or "dolar" in texto.lower() or "dlls" in texto.lower():
        moneda = "USD"
    elif "eur" in texto.lower() or "euro" in texto.lower():
        moneda = "EUR"
    
    # Limpiar el texto para extraer el número
    texto = texto.lower()
    texto = texto.replace("$", "").replace("mxn", "").replace("mnx", "")
    texto = texto.replace("pesos", "").replace("mx", "").strip()
    
    # Extraer el número
    patron_numero = r"[\d,.]+(?:\s*(?:millones?|mill?|k))?"
    match = re.search(patron_numero, texto)
    
    if not match:
        return {
            "valor": "0",
            "moneda": moneda,
            "texto_original": texto_original,
            "incluye_mantenimiento": False,
            "cuota_mantenimiento": 0.0
        }
    
    numero = match.group(0)
    
    # Procesar millones/miles
    multiplicador = 1
    if any(x in numero.lower() for x in ["millones", "millon", "mill", "m"]):
        multiplicador = 1_000_000
        numero = re.sub(r"\s*(?:millones|millon|mill|m)", "", numero, flags=re.IGNORECASE)
    elif "k" in numero.lower():
        multiplicador = 1_000
        numero = numero.lower().replace("k", "")
    
    # Limpiar el número
    numero = numero.replace(" ", "")
    
    # Si tiene coma y punto, la coma es separador de miles
    if "," in numero and "." in numero:
        numero = numero.replace(",", "")
    # Si solo tiene comas, es separador decimal
    elif "," in numero and "." not in numero:
        numero = numero.replace(",", ".")
    
    try:
        valor = float(numero) * multiplicador
        # Convertir a string sin decimales
        valor_str = str(int(valor))
    except (ValueError, TypeError):
        valor_str = "0"
    
    # Detectar si incluye mantenimiento
    incluye_mantenimiento = any(x in texto_original.lower() for x in [
        "incluye mantenimiento",
        "mantenimiento incluido",
        "cuota incluida",
        "incluye cuota"
    ])
    
    # Extraer cuota de mantenimiento si se menciona
    cuota = 0.0
    patron_cuota = r"mantenimiento[:\s]+\$?\s*([\d,.]+)"
    if match_cuota := re.search(patron_cuota, texto_original.lower()):
        try:
            cuota = float(match_cuota.group(1).replace(",", ""))
        except (ValueError, TypeError):
            pass
    
    return {
        "valor": valor_str,
        "moneda": moneda,
        "texto_original": texto_original,
        "incluye_mantenimiento": incluye_mantenimiento,
        "cuota_mantenimiento": cuota
    }

def extraer_tipo_operacion(texto: str) -> str:
    """Extrae el tipo de operación (venta/renta)"""
    texto = texto.lower()
    
    # Palabras clave para cada tipo
    palabras_renta = [
        "renta", "alquiler", "arrendamiento", "rentar", "alquilar",
        "mensual", "/mes", "por mes", "mensualidad"
    ]
    palabras_venta = [
        "venta", "vendo", "se vende", "en venta", "remato", "remate",
        "oportunidad de compra", "precio de venta"
    ]
    
    # Buscar palabras clave
    if any(p in texto for p in palabras_renta):
        return "Renta"
    if any(p in texto for p in palabras_venta):
        return "Venta"
    
    # Si no hay palabras clave, inferir por precio
    precio_match = re.search(r'\$\s*([\d,.]+)', texto)
    if precio_match:
        try:
            precio = float(precio_match.group(1).replace(",", "").replace(".", ""))
            return "Venta" if precio >= 500_000 else "Renta"
        except:
            pass
    
    return "Desconocido"

def extraer_tipo_propiedad(texto: str) -> str:
    """Extrae el tipo de propiedad"""
    texto = texto.lower()
    
    # Mapeo de tipos de propiedad y sus variantes
    tipos = {
        "Casa": [
            "casa", "casa sola", "casa habitación", "residencia",
            "chalet", "villa", "casa en condominio"
        ],
        "Departamento": [
            "departamento", "depto", "apartamento", "flat",
            "penthouse", "pent house", "loft"
        ],
        "Terreno": [
            "terreno", "lote", "predio", "solar", "parcela",
            "tierra", "hectárea"
        ],
        "Local": [
            "local", "local comercial", "plaza comercial",
            "negocio", "comercio"
        ],
        "Oficina": [
            "oficina", "despacho", "consultorio", "suite"
        ],
        "Bodega": [
            "bodega", "almacén", "nave industrial", "galpón"
        ],
        "Casa en condominio": [
            "casa en condominio", "casa en privada", "townhouse",
            "casa en cluster"
        ]
    }
    
    # Buscar coincidencias
    for tipo, palabras in tipos.items():
        if any(p in texto for p in palabras):
            return tipo
    
    return "Otro"

def extraer_ubicacion(texto: str, soup: BeautifulSoup) -> Dict[str, Any]:
    """Extrae y normaliza la información de ubicación"""
    ubicacion = {
        "colonia": "",
        "calle": "",
        "estado": "Morelos",
        "ciudad": "Cuernavaca",
        "referencias": [],
        "coordenadas": {"latitud": None, "longitud": None},
        "zona": "",
        "fraccionamiento": ""
    }
    
    # Patrones para colonias conocidas
    colonias_conocidas = [
        "Chipitlán", "Palmira", "Delicias", "Tlaltenango", "Acapantzingo",
        "Reforma", "Vista Hermosa", "Lomas de Cortés", "Buenavista",
        "Rancho Cortés", "Amatitlán", "Tetela del Monte", "Lomas de Atzingo",
        "Jardines de Cuernavaca", "La Pradera", "Lomas de la Selva"
    ]
    
    # Buscar colonia
    texto_lower = texto.lower()
    for colonia in colonias_conocidas:
        if colonia.lower() in texto_lower:
            ubicacion["colonia"] = colonia
            break
    
    # Buscar fraccionamiento/privada
    patrones_fracc = [
        r'(?:fraccionamiento|fracc\.|privada|priv\.|residencial|cluster)\s+([A-Za-zÁ-Úá-ú\s]+)',
        r'en\s+([A-Za-zÁ-Úá-ú\s]+?)(?:\s+(?:cerca|junto|frente))',
    ]
    
    for patron in patrones_fracc:
        if match := re.search(patron, texto, re.I):
            fracc = match.group(1).strip()
            if len(fracc) > 3:  # Evitar matches muy cortos
                ubicacion["fraccionamiento"] = fracc
                break
    
    # Extraer referencias
    referencias = []
    patrones_ref = [
        r'cerca\s+(?:de|del|dela|a)\s+([^\.]+)',
        r'junto\s+(?:a|al)\s+([^\.]+)',
        r'frente\s+(?:a|al)\s+([^\.]+)',
        r'sobre\s+([^\.]+)',
    ]
    
    for patron in patrones_ref:
        if matches := re.finditer(patron, texto, re.I):
            for match in matches:
                ref = match.group(1).strip()
                if len(ref) > 3 and ref not in referencias:
                    referencias.append(ref)
    
    ubicacion["referencias"] = referencias
    
    # Intentar extraer coordenadas del DOM
    try:
        coords = soup.find('a', href=lambda x: x and 'maps' in x.lower())
        if coords:
            href = coords['href']
            lat_match = re.search(r'[?&]q=([-\d.]+),([-\d.]+)', href)
            if lat_match:
                ubicacion["coordenadas"]["latitud"] = float(lat_match.group(1))
                ubicacion["coordenadas"]["longitud"] = float(lat_match.group(2))
    except:
        pass
    
    return ubicacion

def extraer_caracteristicas(texto: str) -> Caracteristicas:
    """Extrae características de la propiedad"""
    caract = Caracteristicas()
    
    # Tipo de propiedad
    tipos = {
        "casa": ["casa sola", "casa", "casa en condominio", "casa en privada"],
        "departamento": ["departamento", "depto", "departamentos"],
        "terreno": ["terreno", "lote", "terrenos"],
        "local": ["local", "locales", "local comercial"],
        "oficina": ["oficina", "oficinas"],
        "bodega": ["bodega", "bodegas"],
        "hotel": ["hotel", "hoteles"]
    }
    
    for tipo, palabras in tipos.items():
        if any(p in texto.lower() for p in palabras):
            caract.tipo_propiedad = tipo.capitalize()
            break
    
    # Recámaras (buscar en título y descripción)
    patrones_rec = [
        r'(\d+)\s*(?:recámaras?|recamaras?|habitaciones?|dormitorios?|rec)',
        r'(?:recámaras?|recamaras?|habitaciones?|dormitorios?|rec)\s*(?::|=)?\s*(\d+)'
    ]
    
    for patron in patrones_rec:
        if match := re.search(patron, texto, re.I):
            try:
                caract.recamaras = int(match.group(1))
                break
            except:
                continue
    
    # Baños (incluye decimales)
    patrones_ban = [
        r'(\d+(?:\.\d+)?)\s*(?:baños?|banos?)',
        r'(?:baños?|banos?)\s*(?::|=)?\s*(\d+(?:\.\d+)?)'
    ]
    
    for patron in patrones_ban:
        if match := re.search(patron, texto, re.I):
            try:
                caract.banos = float(match.group(1))
                break
            except:
                continue
    
    # Niveles
    if match := re.search(r'(\d+)\s*(?:niveles?|pisos?|plantas?)', texto, re.I):
        caract.niveles = int(match.group(1))
    
    # Un nivel
    caract.un_nivel = any(p in texto.lower() for p in [
        "un nivel", "una planta", "planta baja", "1 nivel", "1 planta"
    ])
    
    # Superficies (buscar diferentes formatos)
    patrones_sup = [
        r'(?:terreno|superficie)\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts?2?|metros?)',
        r'(\d+)\s*(?:m2|mts?2?|metros?)\s*(?:de)?\s*(?:terreno|superficie)'
    ]
    
    for patron in patrones_sup:
        if match := re.search(patron, texto, re.I):
            try:
                caract.superficie_m2 = float(match.group(1))
                break
            except:
                continue
    
    patrones_cons = [
        r'(?:construcción|construccion)\s*(?:de|:)?\s*(\d+)\s*(?:m2|mts?2?|metros?)',
        r'(\d+)\s*(?:m2|mts?2?|metros?)\s*(?:de)?\s*(?:construcción|construccion)'
    ]
    
    for patron in patrones_cons:
        if match := re.search(patron, texto, re.I):
            try:
                caract.construccion_m2 = float(match.group(1))
                break
            except:
                continue
    
    # Recámara en planta baja
    caract.recamara_pb = any(p in texto.lower() for p in [
        "recámara en planta baja", "recamara en pb",
        "habitación en planta baja", "dormitorio en planta baja"
    ])
    
    # Cisterna
    if "cisterna" in texto.lower():
        caract.cisterna["tiene"] = True
        if match := re.search(r'cisterna\s*(?:de)?\s*(\d+)\s*(?:litros?|l|m3)', texto, re.I):
            try:
                caract.cisterna["capacidad"] = int(match.group(1))
            except:
                pass
    
    # Apto para discapacitados
    caract.apto_discapacitados = any(p in texto.lower() for p in [
        "discapacitados", "accesibilidad", "rampa", "elevador"
    ])
    
    # Estacionamientos
    patrones_est = [
        r'(\d+)\s*(?:lugares?|cajones?)\s*(?:de)?\s*(?:estacionamiento|cochera)',
        r'(?:estacionamiento|cochera)\s*(?:para|de)?\s*(\d+)\s*(?:autos?|coches?)'
    ]
    
    for patron in patrones_est:
        if match := re.search(patron, texto, re.I):
            try:
                caract.estacionamientos = int(match.group(1))
                break
            except:
                continue
    
    # Edad/Estado
    if any(p in texto.lower() for p in ["nueva", "a estrenar", "recién terminada"]):
        caract.edad = "Nueva"
    elif match := re.search(r'(\d+)\s*años?\s*(?:de antigüedad|antiguo)', texto, re.I):
        caract.edad = f"{match.group(1)} años"
    elif "remodelada" in texto.lower():
        caract.edad = "Remodelada"
    elif "en construcción" in texto.lower():
        caract.edad = "En construcción"
    
    return caract

def extraer_amenidades(texto: str) -> Amenidades:
    """Extrae amenidades de la propiedad"""
    amenidades = Amenidades()
    
    # Seguridad
    amenidades.seguridad = any(p in texto.lower() for p in [
        "seguridad", "vigilancia", "caseta", "privada"
    ])
    
    # Alberca
    amenidades.alberca = any(p in texto.lower() for p in [
        "alberca", "piscina", "chapoteadero"
    ])
    
    # Patio
    amenidades.patio = any(p in texto.lower() for p in [
        "patio", "área exterior", "area exterior"
    ])
    
    # Bodega
    amenidades.bodega = any(p in texto.lower() for p in [
        "bodega", "cuarto de servicio", "almacén"
    ])
    
    # Terraza
    amenidades.terraza = any(p in texto.lower() for p in [
        "terraza", "balcón", "balcon"
    ])
    
    # Jardín
    amenidades.jardin = any(p in texto.lower() for p in [
        "jardín", "jardin", "área verde", "area verde"
    ])
    
    # Estudio
    amenidades.estudio = any(p in texto.lower() for p in [
        "estudio", "oficina", "biblioteca"
    ])
    
    # Roof Garden
    amenidades.roof_garden = any(p in texto.lower() for p in [
        "roof garden", "roofgarden", "terraza en azotea"
    ])
    
    return amenidades

def extraer_legal(texto: str) -> Legal:
    """Extrae información legal de la propiedad"""
    legal = Legal()
    
    # Escrituras
    legal.escrituras = any(p in texto.lower() for p in [
        "escrituras", "escriturada", "título de propiedad"
    ])
    
    # Cesión de derechos
    legal.cesion_derechos = any(p in texto.lower() for p in [
        "cesión", "cesion", "derechos"
    ])
    
    # Formas de pago
    formas_pago = []
    if "contado" in texto.lower():
        formas_pago.append("Contado")
    if any(p in texto.lower() for p in ["crédito", "credito", "financiamiento"]):
        formas_pago.append("Crédito")
    if "infonavit" in texto.lower():
        formas_pago.append("INFONAVIT")
    if "fovissste" in texto.lower():
        formas_pago.append("FOVISSSTE")
    
    legal.formas_pago = formas_pago
    
    return legal

def extraer_vendedor(page) -> Dict[str, str]:
    """Extrae y normaliza información del vendedor"""
    try:
        vendedor_info = page.evaluate('''() => {
            const links = Array.from(document.querySelectorAll('a'));
            const vendedores = [];
            
            for (const link of links) {
                // Filtrar links inválidos
                if (!link.href || !link.textContent.trim() ||
                    link.href.includes('/marketplace') ||
                    link.href.includes('utm_source') ||
                    link.href.includes('fbclid') ||
                    link.href.includes('business.facebook.com')) {
                    continue;
                }
                
                // Buscar links de perfil válidos
                if (link.href.includes('/profile.php?id=') ||
                    link.href.match(/facebook\\.com\\/[^\\/]+$/)) {
                    
                    let nombre = link.textContent.trim();
                    let tipo = 'particular';
                    
                    // Detectar si es inmobiliaria
                    const palabras_inmobiliaria = [
                        'inmobiliaria', 'bienes raices', 'propiedades',
                        'real estate', 'realty', 'broker', 'century',
                        'coldwell', 'properties'
                    ];
                    
                    if (palabras_inmobiliaria.some(p => 
                        nombre.toLowerCase().includes(p))) {
                        tipo = 'inmobiliaria';
                    }
                    
                    vendedores.push({
                        nombre: nombre,
                        perfil: link.href,
                        tipo: tipo
                    });
                }
            }
            
            // Retornar el vendedor más probable
            return vendedores.length > 0 ? vendedores[0] : null;
        }''')
        
        if vendedor_info:
            # Limpiar nombre
            nombre = vendedor_info["nombre"]
            # Eliminar emojis y caracteres especiales
            nombre = re.sub(r'[\U0001F300-\U0001F9FF]', '', nombre)
            # Eliminar palabras comunes
            palabras_eliminar = [
                "marketplace", "facebook", "properties", "real estate",
                "bienes raíces", "inmobiliaria", "realty", "hasta",
                "off", "recoge", "msi", "descuento", "oferta"
            ]
            for palabra in palabras_eliminar:
                nombre = re.sub(r'(?i)' + re.escape(palabra), '', nombre)
            nombre = ' '.join(nombre.split())
            vendedor_info["nombre"] = nombre
            
            # Limpiar link
            link = vendedor_info["perfil"]
            if "?" in link:
                link = link.split("?")[0]
            if "facebook.com/l.php" in link:
                try:
                    # Extraer link real de la redirección
                    response = requests.head(link, allow_redirects=True)
                    link = response.url
                except:
                    pass
            vendedor_info["perfil"] = link
            
            return vendedor_info
    except Exception as e:
        print(f"Error extrayendo vendedor: {e}")
    
    return {
        "nombre": "",
        "perfil": "",
        "tipo": "desconocido"
    }

def extraer_descripcion(page, soup) -> Dict[str, str]:
    """Extrae la descripción y título de la propiedad"""
    resultado = {
        "titulo": "",
        "texto": "",
        "precio": ""
    }
    
    # Extraer título y procesar números
    if h1 := soup.find("h1"):
        titulo = h1.get_text(strip=True)
        resultado["titulo"] = normalizar_texto(titulo)
        
        # Extraer números del título
        if match := re.search(r'(\d+)\s*(?:habitaciones?|recámaras?|rec)', titulo, re.I):
            resultado["recamaras"] = int(match.group(1))
        if match := re.search(r'(\d+(?:\.\d+)?)\s*baños?', titulo, re.I):
            resultado["banos"] = float(match.group(1))
    
    # Extraer precio del título o descripción
    for span in soup.find_all("span"):
        texto = span.get_text(strip=True)
        if texto.startswith("$") and len(texto) < 30:
            resultado["precio"] = texto
            break
    
    # Extraer descripción completa
    try:
        # Intentar expandir "Ver más" si existe
        ver_mas = page.locator("text=Ver más").first
        if ver_mas.is_visible():
            ver_mas.click()
            page.wait_for_timeout(1000)
            # Obtener el contenido actualizado
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
    except:
        pass
    
    # Buscar descripción en el DOM
    descripcion = ""
    for div in soup.find_all("div"):
        if div.get_text(strip=True) in ["Descripción", "Detalles"]:
            if siguiente := div.find_next_sibling("div"):
                descripcion = siguiente.get_text(strip=True).replace("Ver menos", "")
                break
    
    if not descripcion:
        # Buscar en todo el contenido si no se encuentra en la estructura esperada
        texto_completo = soup.get_text(" ", strip=True)
        descripcion = texto_completo
    
    resultado["texto"] = normalizar_texto(descripcion)
    return resultado

def detectar_estado_propiedad(page, soup) -> Tuple[str, str]:
    """Detecta el estado de una propiedad (disponible, no disponible, error)"""
    try:
        # Verificar si hay mensajes de error o no disponibilidad
        mensajes_error = [
            "Esta publicación ya no está disponible",
            "Este artículo ya no está disponible",
            "Este contenido no está disponible",
            "La publicación no existe",
            "No se puede acceder a esta página",
            "Error al cargar la página",
            "Contenido no encontrado",
            "This listing is no longer available",
            "This content isn't available right now",
            "Lo sentimos, este artículo ya no está disponible"
        ]
        
        # Buscar mensajes de error en el texto
        texto_pagina = soup.get_text(" ", strip=True).lower()
        for mensaje in mensajes_error:
            if mensaje.lower() in texto_pagina:
                return ESTADO_NO_DISPONIBLE, mensaje
        
        # Verificar si hay elementos clave que indican que la página cargó bien
        elementos_requeridos = [
            "h1",  # Título
            "span",  # Precio y otros detalles
            "div"  # Contenido general
        ]
        
        for elemento in elementos_requeridos:
            if not soup.find(elemento):
                return ESTADO_ERROR, f"No se encontró el elemento {elemento}"
        
        # Verificar si hay contenido mínimo
        if len(texto_pagina) < 50:
            return ESTADO_ERROR, "Contenido insuficiente en la página"
        
        # Verificar si hay botones de acción típicos
        botones = [
            "Enviar mensaje",
            "Contactar",
            "Hacer una pregunta",
            "Ver más",
            "Message",
            "Contact"
        ]
        
        tiene_botones = False
        for boton in botones:
            try:
                if page.locator(f"text={boton}").is_visible():
                    tiene_botones = True
                    break
            except:
                continue
        
        if not tiene_botones:
            return ESTADO_PENDIENTE, "No se encontraron botones de acción"
        
        # Verificar si está vendida/rentada
        palabras_no_disponible = [
            "vendido", "vendida", "ya no disponible",
            "rentado", "rentada", "alquilado", "alquilada",
            "no disponible", "reservado", "reservada",
            "apartado", "apartada"
        ]
        
        if any(palabra in texto_pagina for palabra in palabras_no_disponible):
            return ESTADO_NO_DISPONIBLE, "Propiedad marcada como no disponible"
        
        # Si llegamos aquí, la propiedad está disponible
        return ESTADO_DISPONIBLE, ""
        
    except Exception as e:
        return ESTADO_ERROR, str(e)

def procesar_propiedad(page, link: str, id_propiedad: str, ciudad: str) -> Optional[Dict]:
    """Procesa una propiedad y retorna sus datos"""
    print(f"\n   → Procesando {id_propiedad} ({ciudad})")
    print(f"   → URL: {link}")
    
    tiempo_inicio = time.time()
    propiedad = Propiedad(id=id_propiedad, link=link)
    
    try:
        # 1. Navegar a la página
        page.goto(link, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_selector("h1", timeout=15000)
        
        # 2. Obtener HTML y crear BeautifulSoup
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # 3. Verificar disponibilidad
        if any(msg in html.lower() for msg in [
            "este contenido no está disponible",
            "esta publicación ya no está disponible",
            "this content isn't available",
            "this listing is no longer available"
        ]):
            propiedad.metadata["estado_listado"] = ESTADO_NO_DISPONIBLE
            return propiedad.to_dict()
        
        # 4. Expandir descripción si es necesario
        try:
            ver_mas = page.locator("text=Ver más").first
            if ver_mas.is_visible():
                ver_mas.click()
                page.wait_for_timeout(1000)
        except:
            pass
        
        # 5. Extraer datos básicos
        propiedad.titulo = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
        texto_completo = soup.get_text(" ", strip=True)
        propiedad.descripcion = texto_completo
        
        # 6. Extraer precio
        precio_info = normalizar_precio(texto_completo)
        propiedad.precio = Precio(**precio_info)
        
        # 7. Extraer ubicación
        ubicacion_info = extraer_ubicacion(texto_completo, soup)
        ubicacion_info["ciudad"] = ciudad
        propiedad.ubicacion = Ubicacion(**ubicacion_info)
        
        # 8. Extraer características
        propiedad.caracteristicas.tipo_operacion = extraer_tipo_operacion(texto_completo)
        propiedad.caracteristicas.tipo_propiedad = extraer_tipo_propiedad(texto_completo)
        
        # Extraer números
        for match in re.finditer(r'(\d+)\s*(?:recámaras?|recamaras?|habitaciones?|dormitorios?)', texto_completo, re.I):
            propiedad.caracteristicas.recamaras = int(match.group(1))
            break
        
        for match in re.finditer(r'(\d+(?:\.\d+)?)\s*(?:baños?|banos?)', texto_completo, re.I):
            propiedad.caracteristicas.banos = float(match.group(1))
            break
        
        for match in re.finditer(r'(\d+)\s*(?:niveles?|pisos?|plantas?)', texto_completo, re.I):
            propiedad.caracteristicas.niveles = int(match.group(1))
            break
        
        for match in re.finditer(r'(\d+)\s*m2?\s*(?:terreno|superficie)', texto_completo, re.I):
            propiedad.caracteristicas.superficie_m2 = float(match.group(1))
            break
        
        for match in re.finditer(r'(\d+)\s*m2?\s*(?:construcción|construccion)', texto_completo, re.I):
            propiedad.caracteristicas.construccion_m2 = float(match.group(1))
            break
        
        # 9. Extraer amenidades
        texto_lower = texto_completo.lower()
        propiedad.amenidades.seguridad = any(x in texto_lower for x in ["vigilancia", "seguridad", "privada"])
        propiedad.amenidades.alberca = any(x in texto_lower for x in ["alberca", "piscina", "pool"])
        propiedad.amenidades.jardin = any(x in texto_lower for x in ["jardín", "jardin", "área verde"])
        propiedad.amenidades.terraza = any(x in texto_lower for x in ["terraza", "balcón", "balcon"])
        propiedad.amenidades.gimnasio = any(x in texto_lower for x in ["gimnasio", "gym"])
        propiedad.amenidades.area_juegos = any(x in texto_lower for x in ["juegos infantiles", "área de juegos"])
        propiedad.amenidades.cocina_integral = any(x in texto_lower for x in ["cocina integral", "cocina equipada"])
        propiedad.amenidades.cuarto_servicio = any(x in texto_lower for x in ["cuarto servicio", "habitación servicio"])
        
        # 10. Extraer información legal
        propiedad.legal.escrituras = any(x in texto_lower for x in ["escrituras", "título propiedad"])
        propiedad.legal.cesion_derechos = any(x in texto_lower for x in ["cesión", "cesion", "derechos"])
        propiedad.legal.predial_corriente = any(x in texto_lower for x in ["predial al corriente", "predial pagado"])
        propiedad.legal.servicios_pagados = any(x in texto_lower for x in ["servicios al corriente", "servicios pagados"])
        
        # Formas de pago
        formas_pago = []
        if "infonavit" in texto_lower:
            formas_pago.append("INFONAVIT")
        if "fovissste" in texto_lower:
            formas_pago.append("FOVISSSTE")
        if "crédito" in texto_lower or "credito" in texto_lower:
            formas_pago.append("Crédito bancario")
        if "contado" in texto_lower:
            formas_pago.append("Contado")
        propiedad.legal.formas_pago = formas_pago
        
        # 11. Extraer vendedor
        vendedor_info = extraer_vendedor(page)
        propiedad.vendedor = Vendedor(**vendedor_info)
        
        # 12. Extraer imágenes
        imagenes = extraer_imagenes(page, id_propiedad)
        propiedad.metadata["imagenes"] = imagenes
        
        # 13. Guardar archivos
        guardar_archivos(html, propiedad.to_dict(), id_propiedad)
        
        # 14. Actualizar timestamps
        ahora = datetime.now().isoformat()
        propiedad.metadata.update({
            "ultima_actualizacion": ahora,
            "fecha_extraccion": ahora,
            "fecha_ultima_revision": ahora
        })
        
        # 15. Validar propiedad
        if not propiedad.es_valida():
            propiedad.metadata["estado_listado"] = ESTADO_PENDIENTE
            propiedad.metadata["errores"].append("Datos incompletos o inválidos")
        else:
            propiedad.metadata["estado_listado"] = ESTADO_DISPONIBLE
        
        return propiedad.to_dict()
        
    except Exception as e:
        print(f"   ! Error procesando propiedad: {e}")
        propiedad.metadata["estado_listado"] = ESTADO_ERROR
        propiedad.metadata["errores"].append(str(e))
        propiedad.metadata["intentos_extraccion"] += 1
        return propiedad.to_dict()

def descargar_imagen(url: str, ruta_destino: str) -> bool:
    """Descarga una imagen y la guarda en la ruta especificada"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
            with open(ruta_destino, "wb") as f:
                f.write(response.content)
            return True
    except Exception as e:
        print(f"Error descargando imagen {url}: {e}")
    return False

def extraer_imagenes(page, id_propiedad: str) -> List[str]:
    """Extrae las URLs de las imágenes y descarga la primera"""
    try:
        # Obtener URLs de imágenes
        imagenes = page.evaluate('''() => {
            return Array.from(document.querySelectorAll('img'))
                .map(img => img.src)
                .filter(src => src && src.startsWith('http'))
                .slice(0, 5);  // Limitar a 5 imágenes
        }''')
        
        # Si no hay imágenes, retornar lista vacía
        if not imagenes:
            return []
        
        # Crear carpeta para imágenes si no existe
        fecha = datetime.now().strftime("%Y-%m-%d")
        carpeta_img = os.path.join(CARPETA_IMAGENES, fecha)
        os.makedirs(carpeta_img, exist_ok=True)
        
        # Descargar solo la primera imagen
        if MAX_IMAGENES > 0:
            for i, url in enumerate(imagenes[:MAX_IMAGENES]):
                nombre_archivo = f"{id_propiedad}_{i+1}.jpg"
                ruta_destino = os.path.join(carpeta_img, nombre_archivo)
                if descargar_imagen(url, ruta_destino):
                    print(f"   ✓ Imagen {i+1} guardada: {nombre_archivo}")
                    return [nombre_archivo]
        
        return []
        
    except Exception as e:
        print(f"Error extrayendo imágenes: {e}")
        return []

def guardar_archivos(html: str, datos: Dict, id_propiedad: str) -> None:
    """Guarda los archivos relacionados con la propiedad"""
    try:
        fecha = datetime.now().strftime("%Y-%m-%d")
        
        # Crear carpetas si no existen
        carpetas = {
            "html": os.path.join(CARPETA_RESULTADOS, fecha, "html") if GUARDAR_HTML else None,
            "dom": os.path.join(CARPETA_RESULTADOS, fecha, "dom") if GUARDAR_DOM else None,
            "json": os.path.join(CARPETA_RESULTADOS, fecha, "json") if GUARDAR_JSON else None
        }
        
        for carpeta in carpetas.values():
            if carpeta:
                os.makedirs(carpeta, exist_ok=True)
        
        # Guardar HTML
        if GUARDAR_HTML and carpetas["html"]:
            ruta_html = os.path.join(carpetas["html"], f"{id_propiedad}.html")
            with open(ruta_html, "w", encoding="utf-8") as f:
                f.write(html)
            print("   ✓ HTML guardado")
        
        # Guardar DOM
        if GUARDAR_DOM and carpetas["dom"]:
            ruta_dom = os.path.join(carpetas["dom"], f"{id_propiedad}_dom.html")
            with open(ruta_dom, "w", encoding="utf-8") as f:
                f.write(html)
            print("   ✓ DOM guardado")
        
        # Guardar JSON
        if GUARDAR_JSON and carpetas["json"]:
            ruta_json = os.path.join(carpetas["json"], f"{id_propiedad}_data.json")
            with open(ruta_json, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
            print("   ✓ JSON guardado")
            
    except Exception as e:
        print(f"Error guardando archivos: {e}")

@dataclass
class Propiedad:
    """Clase principal para manejar propiedades"""
    id: str
    link: str
    titulo: str = ""
    descripcion: str = ""
    precio: Precio = field(default_factory=Precio)
    ubicacion: Ubicacion = field(default_factory=Ubicacion)
    caracteristicas: Caracteristicas = field(default_factory=Caracteristicas)
    amenidades: Amenidades = field(default_factory=Amenidades)
    legal: Legal = field(default_factory=Legal)
    vendedor: Vendedor = field(default_factory=Vendedor)
    metadata: Dict[str, Any] = field(default_factory=lambda: {
        "estado_listado": "disponible",
        "ultima_actualizacion": datetime.now().isoformat(),
        "fecha_extraccion": datetime.now().isoformat(),
        "fecha_ultima_revision": datetime.now().isoformat(),
        "imagenes": [],
        "intentos_extraccion": 0,
        "errores": []
    })
    
    def es_valida(self) -> bool:
        """Verifica si la propiedad tiene datos válidos"""
        return all([
            self.precio.es_valido(),
            self.ubicacion.tiene_ubicacion_valida(),
            self.caracteristicas.tiene_datos_basicos(),
            bool(self.titulo and self.descripcion)
        ])
    
    def to_dict(self) -> Dict:
        """Convierte la propiedad a diccionario"""
        return {
            "id": self.id,
            "link": self.link,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "precio": asdict(self.precio),
            "ubicacion": asdict(self.ubicacion),
            "caracteristicas": asdict(self.caracteristicas),
            "amenidades": asdict(self.amenidades),
            "legal": asdict(self.legal),
            "vendedor": asdict(self.vendedor),
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Propiedad':
        """Crea una instancia de Propiedad desde un diccionario"""
        prop = cls(
            id=data["id"],
            link=data["link"]
        )
        prop.titulo = data.get("titulo", "")
        prop.descripcion = data.get("descripcion", "")
        prop.precio = Precio(**data.get("precio", {}))
        prop.ubicacion = Ubicacion(**data.get("ubicacion", {}))
        prop.caracteristicas = Caracteristicas(**data.get("caracteristicas", {}))
        prop.amenidades = Amenidades(**data.get("amenidades", {}))
        prop.legal = Legal(**data.get("legal", {}))
        prop.vendedor = Vendedor(**data.get("vendedor", {}))
        prop.metadata = data.get("metadata", {})
        return prop

def main():
    """Función principal del script"""
    # 1. Crear directorios necesarios
    fecha = datetime.now().strftime("%Y-%m-%d")
    for carpeta in [CARPETA_RESULTADOS, CARPETA_IMAGENES]:
        os.makedirs(carpeta, exist_ok=True)
    
    # 2. Cargar repositorio maestro
    print("\n1. Cargando repositorio maestro...")
    try:
        with open(CARPETA_REPO_MASTER, "r") as f:
            data = json.load(f)
            repositorio = {k: Propiedad.from_dict(v) for k, v in data.items()}
            print(f"   ✓ Repositorio cargado con {len(repositorio)} propiedades")
    except:
        print("   ! Creando nuevo repositorio")
        repositorio = {}
    
    # 3. Cargar enlaces
    print("\n2. Cargando enlaces a procesar...")
    try:
        with open(CARPETA_LINKS, "r") as f:
            links = json.load(f)
            print(f"   ✓ {len(links)} enlaces cargados")
    except Exception as e:
        print(f"   ! Error cargando enlaces: {e}")
        return
    
    # 4. Filtrar propiedades ya procesadas
    links_pendientes = []
    for item in links:
        if isinstance(item, str):
            link = BASE_URL + item if item.startswith("/") else item
            ciudad = "cuernavaca"
        else:
            link = item.get("link", "")
            link = BASE_URL + link if link.startswith("/") else link
            ciudad = item.get("ciudad", "cuernavaca").lower()
        
        id_prop = link.rstrip("/").split("/")[-1]
        
        # Verificar si necesita actualización
        if id_prop in repositorio:
            prop = repositorio[id_prop]
            ultima_actualizacion = datetime.fromisoformat(
                prop.metadata["ultima_actualizacion"]
            )
            dias_desde_actualizacion = (datetime.now() - ultima_actualizacion).days
            
            # No actualizar si:
            # 1. Se actualizó hace menos de DIAS_ACTUALIZACION días
            # 2. Está marcada como no disponible
            # 3. Ha tenido demasiados intentos fallidos
            if (dias_desde_actualizacion < DIAS_ACTUALIZACION or
                prop.metadata["estado_listado"] == ESTADO_NO_DISPONIBLE or
                prop.metadata["intentos_extraccion"] >= MAX_REINTENTOS):
                continue
        
        links_pendientes.append({"link": link, "id": id_prop, "ciudad": ciudad})
    
    # 5. Procesar propiedades pendientes
    print(f"\n3. Enlaces pendientes: {len(links_pendientes)}")
    pbar = ProgressBar(len(links_pendientes), "Procesando", "propiedades")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=ESTADO_FB,
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()
        
        ok = err = 0
        for item in links_pendientes:
            link = item["link"]
            ciudad = item["ciudad"]
            id_prop = item["id"]
            
            try:
                datos = procesar_propiedad(page, link, id_prop, ciudad)
                if datos:
                    prop = Propiedad.from_dict(datos)
                    if prop.metadata["estado_listado"] == ESTADO_DISPONIBLE:
                        ok += 1
                    else:
                        err += 1
                    repositorio[id_prop] = prop
                else:
                    err += 1
            except Exception as e:
                print(f"\n   ! Error en {id_prop}: {e}")
                err += 1
            
            # Actualizar progreso
            pbar.update(1, ok, err)
            
            # Guardar progreso cada 10 propiedades
            if (ok + err) % 10 == 0:
                with open(CARPETA_REPO_MASTER, "w") as f:
                    json.dump({k: v.to_dict() for k, v in repositorio.items()},
                            f, ensure_ascii=False, indent=2)
        
        pbar.close()
        page.close()
        browser.close()
    
    # 6. Guardar repositorio final
    with open(CARPETA_REPO_MASTER, "w") as f:
        json.dump({k: v.to_dict() for k, v in repositorio.items()},
                 f, ensure_ascii=False, indent=2)
    
    print(f"\nProcesamiento completado:")
    print(f"✓ Exitosos: {ok}")
    print(f"✗ Errores: {err}")
    print(f"Total en repositorio: {len(repositorio)}")

if __name__ == "__main__":
    main() 