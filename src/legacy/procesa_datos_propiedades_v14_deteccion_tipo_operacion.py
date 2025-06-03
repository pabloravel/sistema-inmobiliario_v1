#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
procesa_datos_propiedades_v14_deteccion_tipo_operacion.py

Script para procesar los datos crudos extraídos y generar el repositorio
completo con todos los campos necesarios.
Esta versión mejora la detección del tipo de operación para basarse únicamente
en el texto, ignorando completamente el precio.
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

def extraer_tipo_operacion(texto: str) -> Optional[str]:
    """
    Extrae el tipo de operación (venta/renta) basándose únicamente en el texto.
    """
    if not texto:
        return None
        
    texto = normalizar_texto(texto)
    
    # Patrones explícitos de venta (ordenados por prioridad)
    patrones_venta = [
        r'(?:en\s+)?venta',
        r'(?:se\s+)?vende',
        r'vendemos',
        r'vendo',
        r'precio\s+de\s+venta',
        r'costo\s+de\s+venta',
        r'valor\s+de\s+venta',
        r'oportunidad\s+de\s+compra',
        r'a\s+la\s+venta',
        r'venta\s+directa',
        r'venta\s+inmediata',
        r'venta\s+urgente',
        r'venta\s+de\s+oportunidad',
        r'precio\s+de\s+contado',
        r'precio\s+a\s+tratar',
        r'acepto\s+credito',
        r'credito\s+infonavit',
        r'credito\s+fovissste',
        r'credito\s+bancario',
        r'contado\s+y\s+credito',
        r'facilidades\s+de\s+pago',
        r'enganche\s+de',
        r'mensualidades\s+de',
        r'precio\s+total',
        r'precio\s+final',
        r'precio\s+negociable',
        r'escrituras?\s+al\s+dia',
        r'titulo\s+de\s+propiedad',
        r'cesion\s+de\s+derechos'
    ]
    
    # Patrones explícitos de renta (ordenados por prioridad)
    patrones_renta = [
        r'(?:en\s+)?renta(?:\s+mensual)?',
        r'(?:se\s+)?renta\s+por\s+mes',
        r'(?:para|en)\s+alquiler',
        r'alquiler\s+mensual',
        r'arrendamiento',
        r'precio\s+de\s+renta',
        r'rento\s+(?:bonita|hermosa|bella|linda|preciosa)?',
        r'rentamos',
        r'deposito\s+en\s+garantia',
        r'aval\s+requerido',
        r'fiador',
        r'contrato\s+de\s+arrendamiento',
        r'contrato\s+minimo',
        r'renta\s+mensual\s+de',
        r'mensualidad\s+de',
        r'por\s+mes',
        r'/\s*mes',
        r'al\s+mes'
    ]
    
    # Primero buscar patrones de venta
    for patron in patrones_venta:
        if re.search(patron, texto):
            # Verificar que no sea una falsa detección por contexto de renta
            contexto_renta = any(re.search(p, texto) for p in patrones_renta)
            if not contexto_renta:
                return "venta"
    
    # Luego buscar patrones de renta
    for patron in patrones_renta:
        if re.search(patron, texto):
            return "renta"
    
    # Si no se encontró ningún patrón explícito, buscar indicadores adicionales
    indicadores_venta = [
        r'inversion',
        r'oportunidad',
        r'remato',
        r'ultimos\s+lotes',
        r'precio\s+de\s+remate',
        r'precio\s+de\s+oportunidad',
        r'excelente\s+inversion',
        r'gran\s+oportunidad',
        r'escriturada',
        r'cesion',
        r'credito',
        r'hipoteca'
    ]
    
    indicadores_renta = [
        r'mensual(?:idad)?',
        r'deposito',
        r'aval',
        r'fiador',
        r'contrato\s+minimo',
        r'servicios\s+incluidos',
        r'incluye\s+servicios',
        r'sin\s+deposito'
    ]
    
    # Contar indicadores
    puntos_venta = sum(1 for patron in indicadores_venta if re.search(patron, texto))
    puntos_renta = sum(1 for patron in indicadores_renta if re.search(patron, texto))
    
    # Si hay más indicadores de un tipo que de otro, usar ese tipo
    if puntos_venta > puntos_renta:
        return "venta"
    elif puntos_renta > puntos_venta:
        return "renta"
    
    # Si no hay suficiente información, asumir venta por defecto
    return "venta"

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
ARCHIVO_ENTRADA = "repositorio_propiedades.json"
ARCHIVO_SALIDA = "resultados/propiedades_estructuradas.json"

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

def procesar_propiedad(datos_crudos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Procesa los datos crudos de una propiedad y extrae información estructurada.
    """
    # Obtener el texto de la descripción
    texto = ""
    if isinstance(datos_crudos.get('descripcion'), dict):
        texto = datos_crudos['descripcion'].get('texto_original', '') or datos_crudos['descripcion'].get('texto_limpio', '')
    elif isinstance(datos_crudos.get('descripcion'), str):
        texto = datos_crudos['descripcion']
    
    # Agregar el título a la descripción si existe
    if datos_crudos.get('titulo'):
        texto = datos_crudos['titulo'] + ". " + texto
        
    # Si no hay texto, retornar diccionario vacío
    if not texto:
        return {}
        
    # Normalizar el texto para procesamiento
    texto_normalizado = normalizar_texto(texto)
    
    # Extraer tipo de operación basándose únicamente en el texto
    tipo_operacion = extraer_tipo_operacion(texto_normalizado)
    
    # Si no se encontró en el texto, usar el valor existente
    if not tipo_operacion and isinstance(datos_crudos.get('caracteristicas'), dict):
        tipo_operacion = datos_crudos['caracteristicas'].get('tipo_operacion')
    
    # Construir objeto de propiedad estructurada
    propiedad_estructurada = {
        'id': datos_crudos.get('id'),
        'link': datos_crudos.get('link') or datos_crudos.get('url', ''),
        'titulo': datos_crudos.get('titulo', ''),
        'descripcion_original': texto,
        'ubicacion': datos_crudos.get('ubicacion', {}),
        'propiedad': {
            'tipo_propiedad': datos_crudos.get('caracteristicas', {}).get('tipo_propiedad', ''),
            'tipo_operacion': tipo_operacion,
            'precio': datos_crudos.get('precio') or datos_crudos.get('precios', {}),
            'niveles': datos_crudos.get('caracteristicas', {}).get('niveles', 0),
            'un_nivel': datos_crudos.get('caracteristicas', {}).get('un_nivel', False),
            'superficie_m2': datos_crudos.get('caracteristicas', {}).get('superficie_m2', 0),
            'construccion_m2': datos_crudos.get('caracteristicas', {}).get('construccion_m2', 0)
        },
        'caracteristicas': {
            'recamaras': datos_crudos.get('caracteristicas', {}).get('recamaras', 0),
            'banos': datos_crudos.get('caracteristicas', {}).get('banos', 0),
            'estacionamientos': datos_crudos.get('caracteristicas', {}).get('estacionamientos', 0),
            'edad': datos_crudos.get('caracteristicas', {}).get('edad', '')
        },
        'amenidades': datos_crudos.get('amenidades', {}),
        'legal': datos_crudos.get('legal', {}),
        'metadata': datos_crudos.get('metadata', {})
    }
    
    return propiedad_estructurada

def main():
    """Función principal del script."""
    logger.info("Iniciando procesamiento de datos...")
    
    # Verificar que exista el archivo de entrada
    if not os.path.exists(ARCHIVO_ENTRADA):
        logger.error(f"No se encontró el archivo {ARCHIVO_ENTRADA}")
        return
        
    # Crear directorio de resultados si no existe
    os.makedirs(os.path.dirname(ARCHIVO_SALIDA), exist_ok=True)
    
    # Lista para almacenar todas las propiedades procesadas
    propiedades_procesadas = []
    propiedades_totales = 0
    
    try:
        # Leer archivo de entrada
        with open(ARCHIVO_ENTRADA, 'r', encoding='utf-8') as f:
            datos_crudos = json.load(f)
            
        # Procesar cada propiedad
        for id_propiedad, propiedad_cruda in datos_crudos.items():
            propiedad_procesada = procesar_propiedad(propiedad_cruda)
            if propiedad_procesada:
                propiedades_procesadas.append(propiedad_procesada)
                propiedades_totales += 1
                
        logger.info(f"Procesadas {propiedades_totales} propiedades")
            
    except Exception as e:
        logger.error(f"Error procesando datos: {str(e)}")
        return
    
    # Guardar resultados
    try:
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            json.dump(propiedades_procesadas, f, ensure_ascii=False, indent=2)
        logger.info(f"Resultados guardados en {ARCHIVO_SALIDA}")
    except Exception as e:
        logger.error(f"Error guardando resultados: {str(e)}")

if __name__ == "__main__":
    main() 