#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import logging
import re
from typing import Dict, Any, List, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def extraer_tipo_propiedad(texto: str) -> Optional[str]:
    """Extrae el tipo de propiedad del texto."""
    if not texto:
        return None
        
    texto = texto.lower()
    
    # Patrones de búsqueda mejorados
    patrones = {
        "casa": [
            r"\bcasa\b(?!\s+(?:club|muestra))",
            r"\bresidencia\b",
            r"\bvilla\b"
        ],
        "departamento": [
            r"\bdepartamento\b",
            r"\bdepto\b",
            r"\bapartamento\b",
            r"\bpent\s*house\b"
        ],
        "terreno": [
            r"\bterreno\b",
            r"\blote\b(?!\s+de\s+\w+)",
            r"\bpredio\b"
        ],
        "local": [
            r"\blocal\s+comercial\b",
            r"\blocal\b(?!\s+(?:idad|mente|izaci[oó]n))",
            r"\bcomercio\b"
        ],
        "oficina": [
            r"\boficina\b",
            r"\bconsultorio\b"
        ],
        "bodega": [
            r"\bbodega\b",
            r"\bnave\s+industrial\b",
            r"\bgalp[oó]n\b"
        ]
    }
    
    for tipo, lista_patrones in patrones.items():
        for patron in lista_patrones:
            if re.search(patron, texto):
                return tipo
                
    return None

def extraer_caracteristicas(texto: str) -> Dict[str, Any]:
    """Extrae características detalladas de la propiedad."""
    if not texto:
        return {}
        
    texto = texto.lower()
    
    def extraer_numero(patrones: List[str]) -> Optional[int]:
        for patron in patrones:
            if match := re.search(patron, texto):
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None
    
    caracteristicas = {
        "recamaras": extraer_numero([
            r"(\d+)\s*rec[aá]maras?",
            r"(\d+)\s*habitaciones?",
            r"(\d+)\s*dormitorios?"
        ]),
        "banos": extraer_numero([
            r"(\d+)\s*baños?(?!\s*y\s*medio)",
            r"(\d+)\s*sanitarios?"
        ]),
        "medio_bano": any(patron in texto for patron in [
            "medio baño", "baño y medio", "1/2 baño"
        ]),
        "niveles": extraer_numero([
            r"(\d+)\s*nivele?s?",
            r"(\d+)\s*pisos?"
        ]),
        "un_nivel": any(patron in texto for patron in [
            "un nivel", "una planta", "planta baja",
            "todo en pb", "sin escaleras"
        ]),
        "recamara_planta_baja": any(patron in texto for patron in [
            "recámara en planta baja",
            "recamara en pb",
            "habitación en planta baja"
        ])
    }
    
    return caracteristicas

def extraer_legal(texto: str) -> Dict[str, bool]:
    """Extrae información legal de la propiedad."""
    if not texto:
        return {}
        
    texto = texto.lower()
    
    return {
        "escrituras": any(patron in texto for patron in [
            "escrituras", "escriturada", "título de propiedad",
            "documentos en regla", "papeles en regla"
        ]),
        "cesion_derechos": any(patron in texto for patron in [
            "cesión de derechos", "cesion de derechos",
            "traspaso", "derechos de posesión"
        ])
    }

def procesar_precio(precio: Any) -> Dict[str, Any]:
    """Procesa y valida el precio de la propiedad."""
    if isinstance(precio, dict):
        # Si ya es un diccionario, validar y limpiar
        valor = precio.get("valor", "0")
        # Asegurar que el valor sea string
        return {
            "valor": str(valor),
            "moneda": precio.get("moneda", "MXN"),
            "es_valido": True
        }
    elif isinstance(precio, (int, float)):
        # Si es número, convertir a string
        return {
            "valor": str(int(precio)),
            "moneda": "MXN",
            "es_valido": True
        }
    elif isinstance(precio, str):
        # Si es string, limpiar y validar
        valor = re.sub(r'[^\d.]', '', precio)
        try:
            return {
                "valor": str(int(float(valor))),
                "moneda": "MXN",
                "es_valido": True
            }
        except ValueError:
            pass
            
    return {
        "valor": "0",
        "moneda": "MXN",
        "es_valido": False
    }

def procesar_datos(datos: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Procesa los datos y mantiene estadísticas."""
    propiedades_procesadas = []
    estadisticas = {
        "total": 0,
        "validas": 0,
        "por_tipo": {},
        "caracteristicas": {
            "un_nivel": 0,
            "recamara_pb": 0,
            "escrituras": 0,
            "cesion": 0
        }
    }
    
    # Obtener lista de propiedades
    if isinstance(datos, dict):
        propiedades = datos.get("propiedades", [])
    else:
        propiedades = datos
    
    total = len(propiedades)
    logger.info(f"Procesando {total} propiedades...")
    
    for i, propiedad in enumerate(propiedades, 1):
        try:
            # Procesar la propiedad
            descripcion = propiedad.get("descripcion_original", "") or propiedad.get("descripcion", "")
            
            # Extraer información
            tipo_propiedad = extraer_tipo_propiedad(descripcion)
            caracteristicas = extraer_caracteristicas(descripcion)
            legal = extraer_legal(descripcion)
            precio_procesado = procesar_precio(propiedad.get("precio", {}))
            
            # Actualizar estadísticas
            estadisticas["total"] += 1
            if tipo_propiedad:
                estadisticas["por_tipo"][tipo_propiedad] = estadisticas["por_tipo"].get(tipo_propiedad, 0) + 1
            if caracteristicas.get("un_nivel"):
                estadisticas["caracteristicas"]["un_nivel"] += 1
            if caracteristicas.get("recamara_planta_baja"):
                estadisticas["caracteristicas"]["recamara_pb"] += 1
            if legal.get("escrituras"):
                estadisticas["caracteristicas"]["escrituras"] += 1
            if legal.get("cesion_derechos"):
                estadisticas["caracteristicas"]["cesion"] += 1
            
            # Actualizar la propiedad
            propiedad_procesada = propiedad.copy()
            propiedad_procesada.update({
                "tipo_propiedad": tipo_propiedad,
                "caracteristicas": caracteristicas,
                "legal": legal,
                "precio": precio_procesado
            })
            
            propiedades_procesadas.append(propiedad_procesada)
            estadisticas["validas"] += 1
            
            if i % 100 == 0:
                logger.info(f"Procesadas {i}/{total} propiedades")
                
        except Exception as e:
            logger.error(f"Error procesando propiedad {i}: {str(e)}")
            continue
    
    # Mostrar estadísticas
    logger.info("\nEstadísticas de procesamiento:")
    logger.info(f"Total propiedades: {estadisticas['total']}")
    logger.info(f"Propiedades válidas: {estadisticas['validas']}")
    logger.info("\nPor tipo de propiedad:")
    for tipo, cantidad in estadisticas["por_tipo"].items():
        logger.info(f"- {tipo}: {cantidad}")
    logger.info("\nCaracterísticas especiales:")
    for caract, cantidad in estadisticas["caracteristicas"].items():
        logger.info(f"- {caract}: {cantidad}")
    
    return propiedades_procesadas

def main():
    """Función principal del script."""
    try:
        # Cargar datos
        with open("resultados/repositorio_propiedades.json", 'r', encoding='utf-8') as f:
            datos_raw = json.load(f)
            logger.info("Archivo de datos cargado correctamente")
            
        # Convertir el diccionario en lista
        propiedades = list(datos_raw.values())
        logger.info(f"Encontradas {len(propiedades)} propiedades en el repositorio")
        
        # Procesar datos
        propiedades_procesadas = procesar_datos(propiedades)
        
        # Guardar resultados
        with open("resultados/propiedades_estructuradas.json", 'w', encoding='utf-8') as f:
            json.dump({"propiedades": propiedades_procesadas}, f, indent=4, ensure_ascii=False)
            logger.info("Resultados guardados correctamente")
            
    except Exception as e:
        logger.error(f"Error al procesar los datos: {str(e)}")
        raise

if __name__ == "__main__":
    main() 