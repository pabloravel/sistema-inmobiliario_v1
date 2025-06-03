#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import re
from typing import Optional, Dict, Any, List, Tuple, Union
from collections import defaultdict

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def normalizar_texto(texto: str) -> str:
    """Normaliza el texto para facilitar la búsqueda de patrones."""
    if not texto:
        return ""
    # Convertir a minúsculas y eliminar acentos
    texto = texto.lower()
    texto = re.sub(r'[áàäâ]', 'a', texto)
    texto = re.sub(r'[éèëê]', 'e', texto)
    texto = re.sub(r'[íìïî]', 'i', texto)
    texto = re.sub(r'[óòöô]', 'o', texto)
    texto = re.sub(r'[úùüû]', 'u', texto)
    texto = re.sub(r'[ñ]', 'n', texto)
    # Eliminar caracteres especiales y espacios múltiples
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def extraer_tipo_operacion(texto: str) -> Optional[str]:
    """
    Extrae el tipo de operación (venta/renta) basándose únicamente en el texto de la descripción.
    """
    if not texto:
        return None
        
    texto = normalizar_texto(texto)
    
    # Sistema de puntuación para determinar el tipo de operación
    puntos_venta = 0
    puntos_renta = 0
    
    # Patrones explícitos de venta (3 puntos)
    patrones_venta_explicitos = [
        r'\ben\s+venta\b',
        r'\bse\s+vende\b',
        r'\bvendo\b',
        r'\bvendemos\b',
        r'\bprecio\s+de\s+venta\b',
        r'\bcosto\s+de\s+venta\b',
        r'\bvalor\s+de\s+venta\b',
        r'\ba\s+la\s+venta\b',
        r'\bventa\s+directa\b',
        r'\bventa\s+inmediata\b',
        r'\bventa\s+urgente\b',
        r'\bventa\s+de\s+oportunidad\b',
        r'\bprecio\s+de\s+contado\b',
        r'\bprecio\s+a\s+tratar\b',
        r'\bprecio\s+negociable\b'
    ]
    
    # Patrones explícitos de renta (3 puntos)
    patrones_renta_explicitos = [
        r'\ben\s+renta\b',
        r'\bse\s+renta\b',
        r'\brento\b',
        r'\brentamos\b',
        r'\balquiler\b',
        r'\balquilo\b',
        r'\barrendamiento\b',
        r'\barriendo\b',
        r'\bprecio\s+de\s+renta\b',
        r'\bcosto\s+de\s+renta\b',
        r'\bvalor\s+de\s+renta\b'
    ]
    
    # Indicadores adicionales de venta (1 punto)
    indicadores_venta = [
        r'\bcredito\s+infonavit\b',
        r'\bcredito\s+bancario\b',
        r'\bcredito\s+fovissste\b',
        r'\bfovisste\b',
        r'\binfonavit\b',
        r'\bescrituras\b',
        r'\bpie\s+de\s+casa\b',
        r'\benganche\b',
        r'\bprecio\s+de\s+remate\b',
        r'\boportunidad\s+de\s+compra\b',
        r'\bcompra\s+inmediata\b',
        r'\bprecio\s+de\s+lista\b',
        r'\bprecio\s+de\s+avaluo\b',
        r'\bprecio\s+comercial\b',
        r'\bprecio\s+de\s+mercado\b'
    ]
    
    # Indicadores adicionales de renta (1 punto)
    indicadores_renta = [
        r'\bdeposito\b',
        r'\baval\b',
        r'\bfiador\b',
        r'\bmes\s+de\s+deposito\b',
        r'\bmes\s+adelantado\b',
        r'\bmes\s+corriente\b',
        r'\bcontrato\s+minimo\b',
        r'\bcontrato\s+de\s+arrendamiento\b',
        r'\brenta\s+mensual\b',
        r'\bpago\s+mensual\b',
        r'\bincluye\s+servicios\b',
        r'\bservicios\s+incluidos\b',
        r'\bsin\s+aval\b',
        r'\bsin\s+deposito\b',
        r'\bsin\s+fiador\b'
    ]
    
    # Verificar patrones explícitos (3 puntos cada uno)
    for patron in patrones_venta_explicitos:
        if re.search(patron, texto):
            puntos_venta += 3
            
    for patron in patrones_renta_explicitos:
        if re.search(patron, texto):
            puntos_renta += 3
            
    # Verificar indicadores adicionales (1 punto cada uno)
    for patron in indicadores_venta:
        if re.search(patron, texto):
            puntos_venta += 1
            
    for patron in indicadores_renta:
        if re.search(patron, texto):
            puntos_renta += 1
    
    # Determinar el tipo de operación basado en los puntos
    if puntos_venta > puntos_renta:
        return "venta"
    elif puntos_renta > puntos_venta:
        return "renta"
    elif puntos_venta > 0:  # Si hay empate pero hay indicadores de venta
        return "venta"
    
    return None

def procesar_datos_crudos(archivo_entrada: str = "resultados/repositorio_propiedades.json",
                         archivo_salida: str = "resultados/propiedades_estructuradas.json") -> None:
    """
    Procesa los datos crudos del repositorio y genera un archivo estructurado.
    """
    logger.info(f"Iniciando procesamiento de datos desde {archivo_entrada}")
    
    try:
        with open(archivo_entrada, 'r', encoding='utf-8') as f:
            datos_crudos = json.load(f)
    except Exception as e:
        logger.error(f"Error al leer el archivo de entrada: {e}")
        return
    
    propiedades_procesadas = []
    total_propiedades = len(datos_crudos)
    logger.info(f"Total de propiedades a procesar: {total_propiedades}")
    
    for idx, propiedad in enumerate(datos_crudos, 1):
        try:
            # Extraer descripción
            descripcion = ""
            if isinstance(propiedad, dict):
                if "descripcion" in propiedad:
                    descripcion = propiedad["descripcion"]
                elif "caracteristicas" in propiedad and isinstance(propiedad["caracteristicas"], dict):
                    descripcion = propiedad["caracteristicas"].get("descripcion", "")
            
            # Determinar tipo de operación
            tipo_operacion = extraer_tipo_operacion(descripcion)
            
            # Si no se pudo determinar el tipo de operación, usar el valor original si existe
            if not tipo_operacion and isinstance(propiedad, dict):
                if "tipo_operacion" in propiedad:
                    tipo_operacion = propiedad["tipo_operacion"]
                elif "caracteristicas" in propiedad and isinstance(propiedad["caracteristicas"], dict):
                    tipo_operacion = propiedad["caracteristicas"].get("tipo_operacion")
            
            # Actualizar el tipo de operación en la propiedad
            propiedad_actualizada = propiedad.copy() if isinstance(propiedad, dict) else {}
            if tipo_operacion:
                if "caracteristicas" not in propiedad_actualizada:
                    propiedad_actualizada["caracteristicas"] = {}
                propiedad_actualizada["caracteristicas"]["tipo_operacion"] = tipo_operacion
            
            propiedades_procesadas.append(propiedad_actualizada)
            
            if idx % 10 == 0:
                logger.info(f"Procesadas {idx}/{total_propiedades} propiedades")
                
        except Exception as e:
            logger.error(f"Error al procesar propiedad {idx}: {e}")
            continue
    
    # Guardar resultados
    try:
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            json.dump(propiedades_procesadas, f, ensure_ascii=False, indent=2)
        logger.info(f"Resultados guardados en {archivo_salida}")
        logger.info(f"Total de propiedades procesadas: {len(propiedades_procesadas)}")
    except Exception as e:
        logger.error(f"Error al guardar el archivo de salida: {e}")

if __name__ == "__main__":
    procesar_datos_crudos() 