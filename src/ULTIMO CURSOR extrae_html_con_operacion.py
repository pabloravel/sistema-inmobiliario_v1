#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extrae_html_con_operacion.py

Versión estable que combina la simplicidad del script original
con mejoras en el manejo de errores y timeouts.
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

# Barra de progreso (idéntica a la original)
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
CARPETA_LINKS       = "resultados/links/repositorio_unico.json"
CARPETA_RESULTADOS  = "resultados"
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
ESTADO_FB           = "fb_state.json"
BASE_URL            = "https://www.facebook.com"

# ── Repositorio de colonias y ubicaciones ────────────────────────────────────────────────
COLONIAS_CONOCIDAS = {
    # Cuernavaca
    'lomas de cortes': ('Lomas De Cortes', 'Cuernavaca'),
    'lomas de cortés': ('Lomas De Cortes', 'Cuernavaca'),
    'lomas tetela': ('Lomas De Tetela', 'Cuernavaca'),
    'rancho tetela': ('Rancho Tetela', 'Cuernavaca'),
    'lomas de tzompantle': ('Lomas De Tzompantle', 'Cuernavaca'),
    'tzompantle': ('Tzompantle', 'Cuernavaca'),
    'reforma': ('Reforma', 'Cuernavaca'),
    'vista hermosa': ('Vista Hermosa', 'Cuernavaca'),
    'vistahermosa': ('Vista Hermosa', 'Cuernavaca'),
    'delicias': ('Delicias', 'Cuernavaca'),
    'jardines delicias': ('Jardines Delicias', 'Cuernavaca'),
    'rancho cortes': ('Rancho Cortes', 'Cuernavaca'),
    'flores magón': ('Flores Magón', 'Cuernavaca'),
    'plan de ayala': ('Plan De Ayala', 'Cuernavaca'),
    'paraiso': ('Paraiso', 'Cuernavaca'),
    'paraíso': ('Paraiso', 'Cuernavaca'),
    'unidad deportiva': ('Unidad Deportiva', 'Cuernavaca'),
    'ocotepec': ('Ocotepec', 'Cuernavaca'),
    'tlaltenango': ('Tlaltenango', 'Cuernavaca'),
    'tabachines': ('Tabachines', 'Cuernavaca'),
    'polvorín': ('Polvorin', 'Cuernavaca'),
    'buenavista': ('Buenavista', 'Cuernavaca'),
    'el capiri': ('El Capiri', 'Cuernavaca'),
    'capiri': ('El Capiri', 'Cuernavaca'),
    'los pinos': ('Los Pinos', 'Cuernavaca'),
    'los volcanes': ('Los Volcanes', 'Cuernavaca'),
    'las palmas': ('Las Palmas', 'Cuernavaca'),
    'ahuatepec': ('Ahuatepec', 'Cuernavaca'),
    'santa maria': ('Santa Maria', 'Cuernavaca'),
    'santa maría': ('Santa Maria', 'Cuernavaca'),
    'chamilpa': ('Chamilpa', 'Cuernavaca'),
    'chipitlan': ('Chipitlan', 'Cuernavaca'),
    'palmira': ('Palmira', 'Cuernavaca'),
    'bellavista': ('Bellavista', 'Cuernavaca'),
    'acapantzingo': ('Acapantzingo', 'Cuernavaca'),
    'antonio barona': ('Antonio Barona', 'Cuernavaca'),
    'centro': ('Centro', 'Cuernavaca'),
    'jardín juárez': ('Jardin Juarez', 'Cuernavaca'),
    'jardin juarez': ('Jardin Juarez', 'Cuernavaca'),
    'guerrero': ('Guerrero', 'Cuernavaca'),
    'chapultepec': ('Chapultepec', 'Cuernavaca'),
    'provincias': ('Provincias', 'Cuernavaca'),
    'lomas de la selva': ('Lomas De La Selva', 'Cuernavaca'),
    'la selva': ('La Selva', 'Cuernavaca'),
    'san anton': ('San Anton', 'Cuernavaca'),
    'san jerónimo': ('San Jeronimo', 'Cuernavaca'),
    'san jeronimo': ('San Jeronimo', 'Cuernavaca'),
    'las aguilas': ('Las Aguilas', 'Cuernavaca'),
    'las águilas': ('Las Aguilas', 'Cuernavaca'),
    'campo verde': ('Campo Verde', 'Cuernavaca'),
    'tulipanes': ('Tulipanes', 'Cuernavaca'),
    'satelite': ('Satelite', 'Cuernavaca'),
    'satélite': ('Satelite', 'Cuernavaca'),
    'lomas de ahuatlan': ('Lomas de Ahuatlan', 'Cuernavaca'),
    'jardines de reforma': ('Jardines de Reforma', 'Cuernavaca'),
    'san miguel acapantzingo': ('San Miguel Acapantzingo', 'Cuernavaca'),
    'san cristobal': ('San Cristobal', 'Cuernavaca'),
    'maravillas': ('Maravillas', 'Cuernavaca'),
    'lomas de cortés norte': ('Lomas de Cortes Norte', 'Cuernavaca'),
    'lomas de cortés sur': ('Lomas de Cortes Sur', 'Cuernavaca'),
    'jardines de cuernavaca': ('Jardines de Cuernavaca', 'Cuernavaca'),
    'la pradera': ('La Pradera', 'Cuernavaca'),
    'la herradura': ('La Herradura', 'Cuernavaca'),
    'lomas de la herradura': ('Lomas de la Herradura', 'Cuernavaca'),
    'ahuatepec': ('Ahuatepec', 'Cuernavaca'),
    'lomas de ahuatepec': ('Lomas de Ahuatepec', 'Cuernavaca'),
    'alta vista': ('Alta Vista', 'Cuernavaca'),
    'altavista': ('Alta Vista', 'Cuernavaca'),
    'del empleado': ('Del Empleado', 'Cuernavaca'),
    'del bosque': ('Del Bosque', 'Cuernavaca'),
    'las quintas': ('Las Quintas', 'Cuernavaca'),
    'las rosas': ('Las Rosas', 'Cuernavaca'),
    'los limoneros': ('Los Limoneros', 'Cuernavaca'),
    'los ciruelos': ('Los Ciruelos', 'Cuernavaca'),
    'los mangos': ('Los Mangos', 'Cuernavaca'),
    'las granjas': ('Las Granjas', 'Cuernavaca'),
    'los laureles': ('Los Laureles', 'Cuernavaca'),
    'los sabinos': ('Los Sabinos', 'Cuernavaca'),
    'los robles': ('Los Robles', 'Cuernavaca'),
    'los cedros': ('Los Cedros', 'Cuernavaca'),
    'los faroles': ('Los Faroles', 'Cuernavaca'),
    'los arcos': ('Los Arcos', 'Cuernavaca'),
    'las flores': ('Las Flores', 'Cuernavaca'),
}

LUGARES_CONOCIDOS = {
    # Cuernavaca
    'galerias cuernavaca': ('Vista Hermosa', 'Cuernavaca'),
    'galerías cuernavaca': ('Vista Hermosa', 'Cuernavaca'),
    'averanda': ('Vista Hermosa', 'Cuernavaca'),
    'forum': ('Vista Hermosa', 'Cuernavaca'),
    'plaza cuernavaca': ('Vista Hermosa', 'Cuernavaca'),
    'walmart vista hermosa': ('Vista Hermosa', 'Cuernavaca'),
    'sams vista hermosa': ('Vista Hermosa', 'Cuernavaca'),
    'costco': ('Vista Hermosa', 'Cuernavaca'),
    'hospital henri dunant': ('Vista Hermosa', 'Cuernavaca'),
    'hospital morelos': ('Vista Hermosa', 'Cuernavaca'),
    'hospital san diego': ('Vista Hermosa', 'Cuernavaca'),
    'imss plan de ayala': ('Plan De Ayala', 'Cuernavaca'),
    'issste': ('Chapultepec', 'Cuernavaca'),
    'cruz roja': ('Centro', 'Cuernavaca'),
    'hospital inovamed': ('Reforma', 'Cuernavaca'),
    'hospital medsur': ('Reforma', 'Cuernavaca'),
    'plaza cuernavaca': ('Vista Hermosa', 'Cuernavaca'),
    'superama vista hermosa': ('Vista Hermosa', 'Cuernavaca'),
    'soriana vista hermosa': ('Vista Hermosa', 'Cuernavaca'),
    'walmart reforma': ('Reforma', 'Cuernavaca'),
    'bodega aurrera reforma': ('Reforma', 'Cuernavaca'),
    'oxxo reforma': ('Reforma', 'Cuernavaca'),
    'farmacia guadalajara reforma': ('Reforma', 'Cuernavaca'),
    'plaza reforma': ('Reforma', 'Cuernavaca'),
    'plaza degollado': ('Centro', 'Cuernavaca'),
    'jardín borda': ('Centro', 'Cuernavaca'),
    'jardin borda': ('Centro', 'Cuernavaca'),
    'palacio de cortés': ('Centro', 'Cuernavaca'),
    'catedral': ('Centro', 'Cuernavaca'),
    'zócalo': ('Centro', 'Cuernavaca'),
    'plaza de armas': ('Centro', 'Cuernavaca'),
    'mercado adolfo lópez mateos': ('Centro', 'Cuernavaca'),
    'mercado lopez mateos': ('Centro', 'Cuernavaca'),
    'hospital del niño': ('Chapultepec', 'Cuernavaca'),
    'hospital del niño morelense': ('Chapultepec', 'Cuernavaca'),
    'imss plan de ayala': ('Plan de Ayala', 'Cuernavaca'),
    'plaza sendero': ('Plan de Ayala', 'Cuernavaca'),
    'mega comercial': ('Plan de Ayala', 'Cuernavaca'),
    'mega plan de ayala': ('Plan de Ayala', 'Cuernavaca'),
    'aurrera plan de ayala': ('Plan de Ayala', 'Cuernavaca'),
    'central camionera': ('Plan de Ayala', 'Cuernavaca'),
    'terminal de autobuses': ('Plan de Ayala', 'Cuernavaca'),
    'uaem': ('Centro', 'Cuernavaca'),
    'universidad autonoma': ('Centro', 'Cuernavaca'),
    'universidad autónoma': ('Centro', 'Cuernavaca'),
    'tecnológico de monterrey': ('Reforma', 'Cuernavaca'),
    'tec de monterrey': ('Reforma', 'Cuernavaca'),
    'itesm': ('Reforma', 'Cuernavaca'),
    'universidad la salle': ('Reforma', 'Cuernavaca'),
    'la salle': ('Reforma', 'Cuernavaca'),
    'uninter': ('Reforma', 'Cuernavaca'),
    'universidad internacional': ('Reforma', 'Cuernavaca')
}

# ── Funciones de extracción (manteniendo la simplicidad original) ────────────────
def extraer_descripcion_estable(soup, page):
    """Extrae la descripción usando múltiples métodos"""
    descripcion = ""
    
    # 1. Intentar expandir la descripción
    try:
        # Buscar y hacer clic en todos los "Ver más" visibles
        ver_mas = page.locator("text=Ver más").all()
        for boton in ver_mas:
            if boton.is_visible():
                boton.click()
                page.wait_for_timeout(1000)
    except:
        pass
    
    # 2. Buscar en el HTML actualizado
    html = page.content()
    soup_actualizado = BeautifulSoup(html, "html.parser")
    
    # 3. Intentar diferentes métodos
    # Método 1: Buscar después de "Descripción" o "Detalles"
    for div in soup_actualizado.find_all("div"):
        if div.get_text(strip=True) in ["Descripción", "Detalles"]:
            siguiente = div.find_next_sibling("div")
            if siguiente:
                texto = siguiente.get_text(separator="\n", strip=True)
                if texto and len(texto) > len(descripcion):
                    descripcion = texto
    
    # Método 2: Buscar en elementos con atributos específicos
    for div in soup_actualizado.find_all("div", {"aria-label": True}):
        if "descripción" in div.get("aria-label", "").lower():
            texto = div.get_text(separator="\n", strip=True)
            if texto and len(texto) > len(descripcion):
                descripcion = texto
    
    # Método 3: Buscar en elementos con roles específicos
    for div in soup_actualizado.find_all("div", {"role": "article"}):
        texto = div.get_text(separator="\n", strip=True)
        if texto and len(texto) > len(descripcion):
            descripcion = texto
    
    # Método 4: Buscar en elementos con clases específicas
    clases_descripcion = ["description", "details", "content"]
    for clase in clases_descripcion:
        for div in soup_actualizado.find_all("div", class_=lambda x: x and clase in x.lower()):
            texto = div.get_text(separator="\n", strip=True)
            if texto and len(texto) > len(descripcion):
                descripcion = texto
    
    # 4. Limpiar la descripción
    if descripcion:
        # Eliminar texto común que no es parte de la descripción
        textos_a_eliminar = [
            "Ver más",
            "Ver menos",
            "Enviar mensaje",
            "Guardar",
            "Compartir",
            "Reportar",
            "Publicidad",
            "Sugerencias",
            "Categorías",
            "Detalles del vendedor",
            "Se unió a Facebook",
            "Envía un mensaje",
            "Hola,",
            "¿Sigue disponible?"
        ]
        
        for texto in textos_a_eliminar:
            descripcion = descripcion.replace(texto, "")
        
        # Eliminar líneas vacías y espacios extra
        lineas = [l.strip() for l in descripcion.split("\n") if l.strip()]
        descripcion = "\n".join(lineas)
    
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
    
    # Buscar precio en el texto
    for span in soup.find_all("span"):
        texto = span.get_text(strip=True)
        if texto.startswith("$") and len(texto) < 30:
            try:
                # Limpiar y convertir
                valor = texto.replace("$", "").replace(",", "").replace(".", "").replace(" ", "")
                # Convertir a float y dividir por 100 para manejar centavos
                precio_float = float(valor) / 100
                precio["valor"] = precio_float
                precio["valor_normalizado"] = precio_float
                precio["es_valido"] = True
                return precio
            except ValueError as e:
                precio["error"] = f"Error al convertir precio: {str(e)}"
                
    # Si no se encontró en spans, buscar en el texto completo
    texto_completo = soup.get_text(" ", strip=True).lower()
    patrones_precio = [
        r'\$\s*[\d,.]+\s*(?:millones?)?',
        r'precio:?\s*\$?\s*[\d,.]+',
        r'[\d,.]+\s*(?:millones?)?(?:\s*de\s*pesos)?'
    ]
    
    for patron in patrones_precio:
        if match := re.search(patron, texto_completo):
            try:
                valor = match.group(0).replace("$", "").replace(",", "").replace(".", "").strip()
                if "millones" in valor:
                    valor = float(re.search(r'\d+', valor).group(0)) * 1000000
                else:
                    valor = float(valor)
                precio["valor"] = valor
                precio["valor_normalizado"] = valor
                precio["es_valido"] = True
                return precio
            except:
                continue
                
    return precio

def extraer_ubicacion_mejorada(soup, page):
    """Extrae información detallada de ubicación"""
    ubicacion = {
        "ciudad": "cuernavaca",
        "estado": "Morelos",
        "colonia": "",
        "calle": "",
        "referencias": [],
        "coordenadas": {
            "latitud": None,
            "longitud": None
        },
        "zona": "",
        "cerca_de": []
    }
    
    # Obtener texto completo
    texto_completo = soup.get_text(" ", strip=True).lower()
    
    # 1. Buscar colonia en el texto
    for colonia_key, (colonia_nombre, ciudad) in COLONIAS_CONOCIDAS.items():
        if f" {colonia_key} " in f" {texto_completo} ":
            ubicacion["colonia"] = colonia_nombre
            ubicacion["ciudad"] = ciudad
            break
    
    # 2. Si no se encontró colonia, buscar por lugares conocidos
    if not ubicacion["colonia"]:
        for lugar_key, (colonia_nombre, ciudad) in LUGARES_CONOCIDOS.items():
            if lugar_key in texto_completo:
                ubicacion["colonia"] = colonia_nombre
                ubicacion["ciudad"] = ciudad
                ubicacion["cerca_de"].append(lugar_key)
                break
    
    # 3. Extraer calle
    patrones_calle = [
        r'calle\s+([^,\.]+)',
        r'av(?:enida)?\.\s+([^,\.]+)',
        r'boulevard\s+([^,\.]+)',
        r'blvd\.\s+([^,\.]+)',
        r'privada\s+([^,\.]+)',
        r'cerrada\s+([^,\.]+)',
        r'retorno\s+([^,\.]+)',
        r'callejón\s+([^,\.]+)',
        r'callejon\s+([^,\.]+)',
        r'andador\s+([^,\.]+)',
        r'circuito\s+([^,\.]+)',
        r'prolongación\s+([^,\.]+)',
        r'prolongacion\s+([^,\.]+)',
        # Buscar después de "en" o "ubicada en"
        r'(?:ubicad[oa] en|en)\s+(?:la\s+)?(?:calle\s+)?([^,\.]+?)(?=\s*(?:,|\.|n[úu]mero|#|colonia|esquina|entre|cerca|junto|frente))',
        # Buscar después de número de calle
        r'#\s*\d+\s+([^,\.]+)',
        r'número\s*\d+\s+([^,\.]+)',
        r'num\.\s*\d+\s+([^,\.]+)'
    ]
    
    for patron in patrones_calle:
        if match := re.search(patron, texto_completo, re.I):
            ubicacion["calle"] = match.group(1).strip().title()
            break
    
    # 4. Extraer referencias de ubicación
    referencias = []
    for div in soup.find_all("div"):
        texto = div.get_text(strip=True)
        if "ubicación" in texto.lower() or "dirección" in texto.lower():
            if siguiente := div.find_next_sibling():
                ref = siguiente.get_text(strip=True)
                if ref and len(ref) < 200 and not ref.startswith("$"):
                    referencias.append(ref)
    
    # 5. Extraer referencias tipo "cerca de"
    patrones_cerca = [
        r'cerca\s+(?:de|del|dela|a)\s+([^,\.]+)',
        r'a\s+(?:\d+)?\s*(?:minutos?|cuadras?)\s+(?:de|del|dela)\s+([^,\.]+)',
        r'junto\s+(?:a|al)\s+([^,\.]+)',
        r'frente\s+(?:a|al)\s+([^,\.]+)'
    ]
    
    for patron in patrones_cerca:
        if matches := re.finditer(patron, texto_completo):
            for match in matches:
                ref = match.group(1).strip()
                if ref and ref not in ubicacion["cerca_de"]:
                    ubicacion["cerca_de"].append(ref)
    
    # 6. Intentar extraer coordenadas del HTML
    try:
        script_tags = soup.find_all("script")
        for script in script_tags:
            if script.string and "latitude" in script.string:
                coords_match = re.search(r'"latitude":\s*([\d.-]+).*"longitude":\s*([\d.-]+)', script.string)
                if coords_match:
                    ubicacion["coordenadas"]["latitud"] = float(coords_match.group(1))
                    ubicacion["coordenadas"]["longitud"] = float(coords_match.group(2))
                    break
    except:
        pass
    
    # 7. Limpiar y normalizar referencias
    referencias_limpias = []
    for ref in referencias:
        ref = re.sub(r'\s+', ' ', ref).strip()
        if ref and ref not in referencias_limpias and len(ref) > 5:
            referencias_limpias.append(ref)
    
    ubicacion["referencias"] = referencias_limpias
    
    return ubicacion

def extraer_caracteristicas(soup):
    """Extrae características detalladas de la propiedad"""
    texto_completo = soup.get_text(" ", strip=True).lower()
    
    caracteristicas = {
        "tipo_propiedad": "otro",
        "tipo_operacion": "",
        "recamaras": 0,
        "banos": 0,
        "estacionamiento": 0,
        "metros_terreno": 0,
        "metros_construccion": 0,
        "niveles": 0,
        "un_nivel": False,
        "recamara_pb": False,
        "antiguedad": None,
        "estado_conservacion": "No especificado",
        "amueblado": False,
        "cisterna": {
            "tiene": False,
            "capacidad": None
        },
        "apto_discapacitados": False,
        "edad": None
    }
    
    # Detectar tipo de propiedad
    tipos_propiedad = {
        "casa_sola": ["casa sola", "casa independiente", "casa individual"],
        "casa_condominio": ["casa en condominio", "casa en privada", "casa en cluster"],
        "departamento": ["departamento", "depto", "apartamento", "flat"],
        "terreno": ["terreno", "lote", "predio"],
        "local": ["local", "comercial", "bodega"],
        "oficina": ["oficina", "despacho"],
        "edificio": ["edificio", "inmueble comercial"],
        "villa": ["villa", "bungalow"],
        "hotel": ["hotel", "motel", "posada"]
    }
    
    for tipo, palabras in tipos_propiedad.items():
        if any(palabra in texto_completo for palabra in palabras):
            caracteristicas["tipo_propiedad"] = tipo
            break
    
    # Detectar tipo de operación
    if any(x in texto_completo for x in ["renta", "alquiler", "arrendamiento", "/mes", "mensual"]):
        caracteristicas["tipo_operacion"] = "Renta"
    elif any(x in texto_completo for x in ["venta", "compra", "oportunidad de inversión"]):
        caracteristicas["tipo_operacion"] = "Venta"
    
    # Mapeo de números escritos a dígitos
    numeros_texto = {
        'una': 1, 'un': 1, 'dos': 2, 'tres': 3, 'cuatro': 4,
        'cinco': 5, 'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
        'media': 0.5, 'medio': 0.5
    }
    
    # Extraer números usando patrones mejorados
    patrones = {
        "recamaras": [
            r'(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?|cuartos?|alcobas?)',
            r'(?:rec[aá]maras?|habitaciones?|dormitorios?)\s*:\s*(\d+)',
            r'(?:una|dos|tres|cuatro|cinco|seis)\s+(?:rec[aá]maras?|habitaciones?|dormitorios?)',
            r'(\d+)\s*(?:rec\.?|hab\.?|dorm\.?)',
            r'[•\-\*]\s*(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?)',
            r'cuenta\s+con\s+(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?)',
            r'tiene\s+(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?)'
        ],
        "banos": [
            r'(\d+(?:\.\d+)?)\s*(?:ba[ñn]os?|wc|sanitarios?)',
            r'(?:ba[ñn]os?|sanitarios?)\s*:\s*(\d+(?:\.\d+)?)',
            r'(?:un|dos|tres|medio)\s+ba[ñn]os?'
        ],
        "estacionamiento": [
            r'(\d+)\s*(?:cajones?|lugares?)\s*(?:de)?\s*estacionamiento',
            r'estacionamiento\s*(?:para|:)?\s*(\d+)',
            r'(\d+)\s*(?:autos?|coches?|vehiculos?)',
            r'(?:un|dos|tres)\s+(?:lugares?|cajones?)\s*(?:de)?\s*estacionamiento'
        ],
        "metros_terreno": [
            r'(\d+)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)\s*(?:de)?\s*terreno',
            r'terreno\s*(?:de|:)?\s*(\d+)\s*(?:m2|m²|metros?)',
            r'superficie\s*(?:de|:)?\s*(\d+)\s*(?:m2|m²|metros?)',
            r'lote\s*(?:de)?\s*(\d+)\s*(?:m2|m²|metros?)',
            r'área\s*(?:total|del terreno)?\s*(?:de)?\s*(\d+)\s*(?:m2|m²|metros?)',
            r'(\d+)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)\s*(?:en)?\s*total'
        ],
        "metros_construccion": [
            r'(\d+)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)\s*(?:de)?\s*construcci[oó]n',
            r'construcci[oó]n\s*(?:de|:)?\s*(\d+)\s*(?:m2|m²|metros?)',
            r'[aá]rea\s*constru[ií]da\s*(?:de|:)?\s*(\d+)\s*(?:m2|m²|metros?)',
            r'superficie\s*constru[ií]da\s*(?:de|:)?\s*(\d+)\s*(?:m2|m²|metros?)',
            r'(\d+)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)\s*construidos',
            r'casa\s*(?:de)?\s*(\d+)\s*(?:m2|m²|metros?)'
        ],
        "niveles": [
            r'(\d+)\s*(?:pisos?|niveles?|plantas?)',
            r'(?:pisos?|niveles?|plantas?)\s*:\s*(\d+)'
        ]
    }
    
    for campo, expresiones in patrones.items():
        for patron in expresiones:
            if match := re.search(patron, texto_completo):
                try:
                    # Si es un número escrito en texto
                    valor_texto = match.group(1).lower() if match.groups() else match.group(0).lower()
                    for palabra in valor_texto.split():
                        if palabra in numeros_texto:
                            caracteristicas[campo] = numeros_texto[palabra]
                            break
                    else:
                        # Si no es texto, intentar convertir a número
                        caracteristicas[campo] = float(match.group(1))
                    break
                except:
                    continue
    
    # Detectar si es de un nivel
    caracteristicas["un_nivel"] = (
        "un nivel" in texto_completo or 
        "una planta" in texto_completo or 
        "planta baja" in texto_completo or
        caracteristicas["niveles"] == 1
    )
    
    # Detectar recámara en planta baja
    caracteristicas["recamara_pb"] = any(x in texto_completo for x in [
        "recámara en planta baja",
        "recamara en pb",
        "habitación en planta baja",
        "dormitorio en pb"
    ])
    
    # Detectar cisterna
    if "cisterna" in texto_completo:
        caracteristicas["cisterna"]["tiene"] = True
        # Buscar capacidad
        if match := re.search(r'cisterna\s*(?:de|con)?\s*(\d+)\s*(?:litros?|lts?|m3)', texto_completo):
            caracteristicas["cisterna"]["capacidad"] = int(match.group(1))
    
    # Detectar si es apto para discapacitados
    caracteristicas["apto_discapacitados"] = any(x in texto_completo for x in [
        "apto discapacitados",
        "acceso discapacitados",
        "accesibilidad",
        "rampa",
        "adaptado para discapacitados"
    ])
    
    # Detectar antigüedad/edad
    patrones_edad = [
        r'(\d+)\s*a[ñn]os?\s*(?:de)?\s*antig[uü]edad',
        r'construi[dt][ao]\s*(?:en|:)?\s*(\d{4})',
        r'a[ñn]o\s*(?:de)?\s*construcci[oó]n\s*:\s*(\d{4})',
        r'(?:casa|propiedad|inmueble)\s*(?:del|de)\s*(\d{4})'
    ]
    
    for patron in patrones_edad:
        if match := re.search(patron, texto_completo):
            try:
                valor = int(match.group(1))
                if valor > 1900:  # Es un año
                    caracteristicas["edad"] = datetime.now().year - valor
                else:  # Son años directamente
                    caracteristicas["edad"] = valor
                break
            except:
                continue
    
    # Detectar estado de conservación
    estados = {
        "Excelente": ["excelente", "impecable", "como nuevo", "recién", "recien"],
        "Bueno": ["buen", "bueno", "bien conservado", "en buen estado"],
        "Regular": ["regular", "para remodelar", "necesita mantenimiento"],
        "Malo": ["malo", "necesita reparaciones", "para renovar", "deteriorado"]
    }
    
    for estado, palabras in estados.items():
        if any(palabra in texto_completo for palabra in palabras):
            caracteristicas["estado_conservacion"] = estado
            break
    
    # Detectar si está amueblado
    caracteristicas["amueblado"] = any(x in texto_completo for x in [
        "amueblado", "equipado", "con muebles",
        "línea blanca", "electrodomésticos incluidos"
    ])
    
    return caracteristicas

def extraer_amenidades(soup):
    """Extrae amenidades de la propiedad"""
    texto_completo = soup.get_text(" ", strip=True).lower()
    
    amenidades = {
        "seguridad": {
            "tiene": False,
            "detalles": []
        },
        "alberca": False,
        "patio": False,
        "bodega": False,
        "terraza": False,
        "jardin": False,
        "estudio": False,
        "roof_garden": False,
        "otras": []
    }
    
    # Detectar seguridad
    elementos_seguridad = [
        "vigilancia", "seguridad 24/7", "cámaras", "circuito cerrado",
        "portón eléctrico", "caseta", "guardia", "cerca eléctrica",
        "interfón", "acceso controlado", "seguridad privada"
    ]
    
    for elemento in elementos_seguridad:
        if elemento in texto_completo:
            amenidades["seguridad"]["tiene"] = True
            amenidades["seguridad"]["detalles"].append(elemento)
    
    # Detectar alberca/piscina
    amenidades["alberca"] = any(x in texto_completo for x in [
        "alberca", "piscina", "chapoteadero", "pool"
    ])
    
    # Detectar patio
    amenidades["patio"] = any(x in texto_completo for x in [
        "patio", "área exterior", "espacio exterior"
    ])
    
    # Detectar bodega
    amenidades["bodega"] = any(x in texto_completo for x in [
        "bodega", "cuarto de servicio", "storage", "almacén"
    ])
    
    # Detectar terraza
    amenidades["terraza"] = any(x in texto_completo for x in [
        "terraza", "balcón", "balcon"
    ])
    
    # Detectar jardín
    amenidades["jardin"] = any(x in texto_completo for x in [
        "jardín", "jardin", "área verde", "area verde"
    ])
    
    # Detectar estudio
    amenidades["estudio"] = any(x in texto_completo for x in [
        "estudio", "oficina", "despacho", "biblioteca"
    ])
    
    # Detectar roof garden
    amenidades["roof_garden"] = any(x in texto_completo for x in [
        "roof garden", "rooftop", "terraza en azotea", "sky garden"
    ])
    
    # Otras amenidades comunes
    otras_amenidades = [
        "gimnasio", "gym", "área de juegos", "juegos infantiles",
        "salón de usos múltiples", "sala de juntas", "área común",
        "área de lavado", "cuarto de lavado", "área de tendido"
    ]
    
    for amenidad in otras_amenidades:
        if amenidad in texto_completo and amenidad not in amenidades["otras"]:
            amenidades["otras"].append(amenidad)
    
    return amenidades

def extraer_legal(soup):
    """Extrae información legal de la propiedad"""
    texto_completo = soup.get_text(" ", strip=True).lower()
    
    legal = {
        "escrituras": False,
        "cesion_derechos": False,
        "formas_de_pago": [],
        "documentacion": []
    }
    
    # Detectar escrituras
    legal["escrituras"] = any(x in texto_completo for x in [
        "escrituras", "escriturada", "título de propiedad"
    ])
    
    # Detectar cesión de derechos
    legal["cesion_derechos"] = any(x in texto_completo for x in [
        "cesión", "cesion de derechos", "traspaso"
    ])
    
    # Detectar formas de pago
    formas_pago = {
        "efectivo": ["efectivo", "cash", "contado"],
        "credito_bancario": ["crédito bancario", "credito bancario"],
        "infonavit": ["infonavit", "info"],
        "fovissste": ["fovissste", "fovi"],
        "credito_directo": ["crédito directo", "credito directo", "financiamiento directo"],
        "apartado": ["apartado", "enganche", "anticipo"]
    }
    
    for forma, palabras in formas_pago.items():
        if any(palabra in texto_completo for palabra in palabras):
            legal["formas_de_pago"].append(forma)
    
    # Detectar documentación
    documentos = [
        "predial al corriente",
        "agua al corriente",
        "sin adeudos",
        "documentos en regla",
        "todo pagado",
        "servicios al corriente"
    ]
    
    for doc in documentos:
        if doc in texto_completo:
            legal["documentacion"].append(doc)
    
    return legal

def extraer_estado_legal(soup):
    """Extrae información legal de la propiedad"""
    texto = soup.get_text(" ", strip=True).lower()
    
    return {
        "escrituras": "escrituras" in texto or "escriturada" in texto,
        "cesion_derechos": "cesión" in texto or "cesion de derechos" in texto,
        "creditos": any(x in texto for x in ["crédito", "credito", "infonavit", "fovissste"]),
        "constancia_posesion": "constancia de posesion" in texto
    }

def extraer_datos_vendedor(soup, page):
    """Extrae información del vendedor"""
    vendedor = {
        "nombre": "",
        "tipo": "particular",
        "telefono": "",
        "correo": "",
        "perfil_fb": "",
        "fecha_registro": None,
        "verificado": False,
        "rating": None,
        "num_propiedades": 0
    }
    
    # Buscar nombre y perfil
    try:
        # Intentar extraer usando JavaScript
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
            vendedor["nombre"] = vendedor_info["nombre"]
            vendedor["perfil_fb"] = vendedor_info["perfil"]
            vendedor["tipo"] = vendedor_info["tipo"]
    except:
        # Fallback a BeautifulSoup si falla JavaScript
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "facebook.com/profile.php?id=" in href or re.match(r"facebook\.com/[^/]+$", href):
                vendedor["perfil_fb"] = href
                if strong := a.find("strong"):
                    vendedor["nombre"] = strong.get_text(strip=True)
                break
    
    # Detectar si es inmobiliaria
    texto_completo = soup.get_text(" ", strip=True).lower()
    palabras_inmobiliaria = [
        "inmobiliaria", "bienes raíces", "real estate",
        "propiedades", "realty", "broker", "agencia"
    ]
    
    if any(palabra in texto_completo for palabra in palabras_inmobiliaria):
        vendedor["tipo"] = "inmobiliaria"
    
    # Buscar teléfono - Versión mejorada
    # 1. Primero intentar con JavaScript
    try:
        telefono_js = page.evaluate("""() => {
            // Buscar en botones de WhatsApp
            const whatsappBtns = Array.from(document.querySelectorAll('a[href*="whatsapp"], a[href*="wa.me"]'));
            for (const btn of whatsappBtns) {
                const match = btn.href.match(/(?:whatsapp|wa\.me)\/(?:\+52|52)?(\d{10})/);
                if (match) return match[1];
            }
            
            // Buscar en el texto de los elementos
            const elements = document.querySelectorAll('*');
            for (const el of elements) {
                if (el.textContent) {
                    const match = el.textContent.match(/(?:Tel[eé]fono|Cel(?:ular)?|WhatsApp|WA)?\s*[:\s]*(?:\+52|52)?\s*(\d{10})/i);
                    if (match) return match[1];
                }
            }
            return null;
        }""")
        if telefono_js:
            vendedor["telefono"] = telefono_js
    except:
        pass
    
    # 2. Si no se encontró con JS, buscar en el HTML
    if not vendedor["telefono"]:
        patrones_telefono = [
            # Patrones comunes de teléfono
            r'(?:Tel[eé]fono|Cel(?:ular)?|WhatsApp|WA)?\s*[:\s]*(?:\+52|52)?\s*(\d{10})',
            r'(\d{3}[\s-]?\d{3}[\s-]?\d{4})',
            r'(\d{2}[\s-]?\d{4}[\s-]?\d{4})',
            # Patrones específicos de WhatsApp
            r'(?:whatsapp|wa\.me)\/(?:\+52|52)?(\d{10})',
            # Patrones con palabras clave
            r'(?:informes|contacto|mayores informes)[^\d]*(\d{10})',
            # Patrones con formatos alternativos
            r'(\d{3})[\s\.-]+(\d{3})[\s\.-]+(\d{4})',
            r'(\d{2})[\s\.-]+(\d{4})[\s\.-]+(\d{4})'
        ]
        
        # Buscar en enlaces primero
        for a in soup.find_all("a", href=True):
            href = a["href"].lower()
            if "whatsapp" in href or "wa.me" in href:
                for patron in patrones_telefono:
                    if match := re.search(patron, href):
                        telefono = re.sub(r'\D', '', match.group(1))
                        if len(telefono) == 10:
                            vendedor["telefono"] = telefono
                            break
                if vendedor["telefono"]:
                    break
        
        # Si no se encontró en enlaces, buscar en todo el texto
        if not vendedor["telefono"]:
            for patron in patrones_telefono:
                if match := re.search(patron, texto_completo):
                    if len(match.groups()) == 3:  # Patrón con grupos separados
                        telefono = match.group(1) + match.group(2) + match.group(3)
                    else:
                        telefono = re.sub(r'\D', '', match.group(1))
                    if len(telefono) == 10:
                        vendedor["telefono"] = telefono
                        break
    
    # Buscar correo
    patron_correo = r'[\w\.-]+@[\w\.-]+\.\w+'
    if match := re.search(patron_correo, texto_completo):
        vendedor["correo"] = match.group(0)
    
    # Buscar fecha de registro
    try:
        for div in soup.find_all("div"):
            texto = div.get_text(strip=True)
            if "se unió" in texto.lower():
                if match := re.search(r'(?:se unió (?:en|el))?\s*(\d{4})', texto):
                    vendedor["fecha_registro"] = int(match.group(1))
                break
    except:
        pass
    
    # Verificar si está verificado
    try:
        verificado = page.locator('[aria-label="Cuenta verificada"]').is_visible()
        vendedor["verificado"] = verificado
    except:
        pass
    
    # Intentar obtener rating y número de propiedades
    try:
        rating_element = page.locator('[aria-label*="calificación"]').first
        if rating_element:
            rating_text = rating_element.text_content()
            if match := re.search(r'([\d.]+)', rating_text):
                vendedor["rating"] = float(match.group(1))
    except:
        pass
    
    try:
        # Buscar número de propiedades publicadas
        for div in soup.find_all("div"):
            texto = div.get_text(strip=True)
            if "propiedades" in texto.lower() and "publicadas" in texto.lower():
                if match := re.search(r'(\d+)', texto):
                    vendedor["num_propiedades"] = int(match.group(1))
                break
    except:
        pass
    
    return vendedor

def descargar_imagen_por_playwright(page, ciudad, pid, carpeta, date_str):
    """Descarga la imagen de portada usando Playwright"""
    try:
        src = page.locator('img[alt^="Foto de"]').first.get_attribute('src')
    except:
        try:
            src = page.locator('img').first.get_attribute('src')
        except:
            return ""
    if not src or not src.startswith("http"):
        return ""
    filename = f"{ciudad}-{date_str}-{pid}.jpg"
    path_img = os.path.join(carpeta, filename)
    try:
        resp = requests.get(src, timeout=10)
        if resp.status_code == 200:
            with open(path_img, "wb") as f:
                f.write(resp.content)
            return filename
    except:
        pass
    return ""

def guardar_html_y_json(html, datos, ciudad, pid, carpeta, date_str):
    """Guarda los archivos HTML y JSON"""
    base = f"{ciudad}-{date_str}-{pid}"
    ruta_html = os.path.join(carpeta, base + ".html")
    ruta_json = os.path.join(carpeta, base + ".json")
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

def detectar_tipo_operacion(titulo, descripcion, precio_str):
    """Detecta si es venta o renta"""
    txt = " ".join([titulo, descripcion, precio_str]).lower()
    if any(k in txt for k in ("renta", "alquiler", "/mes", "mensual")):
        return "Renta"
    if any(k in txt for k in ("en venta", "venta", "vender", "vendo", "vende")):
        return "Venta"
    m = re.search(r"([\d\.,]+)", precio_str)
    if m and int(m.group(1).replace(".", "").replace(",", "")) >= 300_000:
        return "Venta"
    return "Desconocido"

def expandir_descripcion(page):
    """Intenta expandir el 'Ver más' de manera simple"""
    try:
        ver_mas = page.locator("text=Ver más").first
        if ver_mas and ver_mas.is_visible():
            ver_mas.click()
            page.wait_for_timeout(1000)
    except:
        pass

# ── Flujo principal ───────────────────────────────────────────────────
def main():
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

    # 3) Filtra pendientes y limita a 5 propiedades
    pending = [l for l in links if l["id"] not in existing_ids][:5]  # Limitar a 5 propiedades

    # ── PRINT RESUMEN ANTES DE EMPEZAR ──
    total = len(links)
    falta = len(pending)
    print(f"\nTotal de propiedades: {total}, procesando {falta} propiedades de prueba")

    # 4) Carpeta diaria
    date_str = datetime.now().strftime("%Y-%m-%d")
    carpeta  = os.path.join(CARPETA_RESULTADOS, date_str)
    os.makedirs(carpeta, exist_ok=True)

    # 5) Lanzar navegador y barra de progreso
    pbar = ProgressBar(falta, desc="Extrayendo propiedades", unit="propiedad")
    ok = err = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=ESTADO_FB if os.path.exists(ESTADO_FB) else None,
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

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
                    with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as f:
                        json.dump(data_master, f, ensure_ascii=False, indent=2)
                
                ok += 1
                print(f"   ✓ {pid} procesado en {time.time()-t0:.1f}s")
                
            except Exception as e:
                err += 1
                print(f"❌ Error en {pid}: {str(e)}")
            finally:
                pbar.update(1, ok=ok, err=err, last_time=time.time()-t0)

        pbar.close()
        page.close()
        browser.close()

    print(f"\nTotal de propiedades en el repositorio maestro: {len(data_master)}")

    # 6) Analizar resultados de las 5 propiedades
    print("\nAnalizando resultados de las propiedades procesadas:")
    for item in pending:
        pid = item["id"]
        if pid in data_master:
            datos = data_master[pid]
            print(f"\nPropiedad {pid}:")
            
            # Verificar campos básicos
            if not datos["titulo"]:
                print("❌ Falta título")
            if not datos["descripcion"]:
                print("❌ Falta descripción")
            if not datos["precio"]["es_valido"]:
                print(f"❌ Error en precio: {datos['precio']['error']}")
            
            # Verificar ubicación
            if not datos["ubicacion"]["colonia"]:
                print("⚠️ Falta colonia")
            if not datos["ubicacion"]["referencias"]:
                print("⚠️ Sin referencias de ubicación")
            if not datos["ubicacion"]["calle"]:
                print("⚠️ Falta calle")
            
            # Verificar características básicas
            if datos["caracteristicas"]["tipo_propiedad"] == "otro":
                print("⚠️ Tipo de propiedad no detectado")
            if not datos["caracteristicas"]["tipo_operacion"]:
                print("⚠️ Tipo de operación no detectado")
            if not datos["caracteristicas"]["recamaras"]:
                print("⚠️ Número de recámaras no detectado")
            if not datos["caracteristicas"]["banos"]:
                print("⚠️ Número de baños no detectado")
            if not datos["caracteristicas"]["metros_terreno"] and not datos["caracteristicas"]["metros_construccion"]:
                print("⚠️ No se detectó superficie")
            
            # Verificar amenidades
            if datos["amenidades"]["seguridad"]["tiene"] and not datos["amenidades"]["seguridad"]["detalles"]:
                print("⚠️ Seguridad detectada pero sin detalles")
            
            # Verificar datos legales
            if not datos["estado_legal"]["escrituras"] and not datos["estado_legal"]["cesion_derechos"]:
                print("⚠️ Estado legal no especificado")
            if not datos["estado_legal"]["formas_de_pago"]:
                print("⚠️ Formas de pago no detectadas")
            
            # Verificar vendedor
            if not datos["vendedor"]["nombre"]:
                print("⚠️ Nombre del vendedor no detectado")
            if not datos["vendedor"]["telefono"]:
                print("⚠️ Teléfono no detectado")
            
            # Mostrar resumen de datos extraídos
            print("\nDatos extraídos:")
            print(f"- Tipo: {datos['caracteristicas']['tipo_propiedad']}")
            print(f"- Operación: {datos['caracteristicas']['tipo_operacion']}")
            print(f"- Precio: {datos['precio']['valor_normalizado']}")
            print(f"- Ubicación: {datos['ubicacion']['colonia']}, {datos['ubicacion']['ciudad']}")
            print(f"- Superficie: {datos['caracteristicas']['metros_construccion']}m² construcción, {datos['caracteristicas']['metros_terreno']}m² terreno")
            print(f"- Recámaras: {datos['caracteristicas']['recamaras']}")
            print(f"- Baños: {datos['caracteristicas']['banos']}")
            if datos["amenidades"]["seguridad"]["tiene"]:
                print(f"- Seguridad: {', '.join(datos['amenidades']['seguridad']['detalles'])}")
            if datos["estado_legal"]["formas_de_pago"]:
                print(f"- Formas de pago: {', '.join(datos['estado_legal']['formas_de_pago'])}")

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
        
        # Obtener HTML y crear soup
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Extraer título
        titulo = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
        
        # Extraer descripción (usando la versión mejorada)
        descripcion = extraer_descripcion_estable(soup, page)
        
        # Crear nuevo soup con descripción expandida
        html_completo = html + f"<div class='descripcion_expandida'>{descripcion}</div>"
        soup_completo = BeautifulSoup(html_completo, "html.parser")
        
        # Extraer resto de datos usando el soup completo
        precio = extraer_precio_mejorado(soup_completo)
        ubicacion = extraer_ubicacion_mejorada(soup_completo, page)
        caracteristicas = extraer_caracteristicas(soup_completo)
        amenidades = extraer_amenidades(soup_completo)
        estado_legal = extraer_legal(soup_completo)
        vendedor = extraer_datos_vendedor(soup_completo, page)
        img_portada = descargar_imagen_por_playwright(page, ciudad, id_propiedad, carpeta, fecha_str)
        
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

if __name__ == "__main__":
    main()