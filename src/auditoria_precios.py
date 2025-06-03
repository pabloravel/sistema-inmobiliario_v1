#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
auditoria_precios.py

Script para analizar y auditar los resultados del procesamiento de precios
de las propiedades inmobiliarias.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any
import statistics
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
ARCHIVO_PROPIEDADES = "resultados/propiedades_estructuradas.json"
ARCHIVO_REPORTE = f"resultados/auditoria_precios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

def cargar_datos() -> List[Dict]:
    """Carga los datos del archivo de propiedades estructuradas."""
    try:
        with open(ARCHIVO_PROPIEDADES, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            return datos if isinstance(datos, list) else []
    except Exception as e:
        logger.error(f"Error cargando datos: {str(e)}")
        return []

def analizar_distribucion_precios(propiedades: List[Dict]) -> Dict[str, Any]:
    """Analiza la distribución de precios por tipo de operación y propiedad."""
    resultados = {
        "venta": defaultdict(list),
        "renta": defaultdict(list),
        "estadisticas": {
            "venta": {},
            "renta": {}
        }
    }
    
    for prop in propiedades:
        tipo_op = prop.get("tipo_operacion", {}).get("tipo", "").lower()
        if tipo_op not in ["venta", "renta"]:
            continue
            
        tipo_prop = prop.get("tipo_propiedad", {}).get("tipo")
        precio = prop.get("precio", {}).get("valor")
        
        if precio and tipo_prop:
            resultados[tipo_op][tipo_prop].append(precio)
    
    # Calcular estadísticas
    for operacion in ["venta", "renta"]:
        for tipo_prop, precios in resultados[operacion].items():
            if precios:
                resultados["estadisticas"][operacion][tipo_prop] = {
                    "promedio": statistics.mean(precios),
                    "mediana": statistics.median(precios),
                    "min": min(precios),
                    "max": max(precios),
                    "desv_std": statistics.stdev(precios) if len(precios) > 1 else 0,
                    "cantidad": len(precios)
                }
    
    return resultados

def analizar_calidad_precios(propiedades: List[Dict]) -> Dict[str, Any]:
    """Analiza la calidad de los datos de precios."""
    resultados = {
        "total_propiedades": len(propiedades),
        "precios_validos": 0,
        "precios_invalidos": 0,
        "monedas": defaultdict(int),
        "confianza_promedio": 0,
        "errores_comunes": defaultdict(int),
        "propiedades_negociables": 0,
        "incluye_mantenimiento": 0,
        "rangos_precio": {
            "con_rango": 0,
            "sin_rango": 0
        }
    }
    
    confianzas = []
    for prop in propiedades:
        precio_info = prop.get("precio", {})
        
        # Contabilizar validez
        if precio_info.get("es_valido"):
            resultados["precios_validos"] += 1
        else:
            resultados["precios_invalidos"] += 1
            resultados["errores_comunes"][precio_info.get("mensaje", "Sin mensaje")] += 1
        
        # Contabilizar monedas
        resultados["monedas"][precio_info.get("moneda", "No especificada")] += 1
        
        # Acumular confianza
        if confianza := precio_info.get("confianza"):
            confianzas.append(confianza)
        
        # Analizar detalles adicionales
        detalles = precio_info.get("detalles", {})
        if detalles.get("es_negociable"):
            resultados["propiedades_negociables"] += 1
        if detalles.get("incluye_mantenimiento"):
            resultados["incluye_mantenimiento"] += 1
        
        # Contabilizar rangos de precio
        if detalles.get("precio_min") is not None:
            resultados["rangos_precio"]["con_rango"] += 1
        else:
            resultados["rangos_precio"]["sin_rango"] += 1
    
    # Calcular confianza promedio
    if confianzas:
        resultados["confianza_promedio"] = statistics.mean(confianzas)
    
    return resultados

def generar_graficas(distribucion: Dict[str, Any], calidad: Dict[str, Any]):
    """Genera gráficas para visualizar los resultados."""
    try:
        # Configurar estilo
        plt.style.use('default')
        
        # 1. Distribución de precios por tipo de propiedad y operación
        for operacion in ["venta", "renta"]:
            datos = []
            for tipo_prop, stats in distribucion["estadisticas"][operacion].items():
                datos.append({
                    "tipo": tipo_prop,
                    "precio_promedio": stats["promedio"],
                    "precio_mediana": stats["mediana"],
                    "cantidad": stats["cantidad"]
                })
            
            if datos:
                df = pd.DataFrame(datos)
                
                # Gráfica de precios promedio
                plt.figure(figsize=(12, 6))
                ax = plt.gca()
                
                # Barras para precio promedio
                bars1 = plt.bar(df.index, df["precio_promedio"], alpha=0.8, label="Precio Promedio")
                
                # Barras para precio mediana
                bars2 = plt.bar(df.index, df["precio_mediana"], alpha=0.5, label="Precio Mediana")
                
                # Configuración de la gráfica
                plt.title(f"Precios por tipo de propiedad ({operacion})")
                plt.xticks(df.index, df["tipo"], rotation=45)
                plt.ylabel("Precio (MXN)")
                
                # Añadir etiquetas de cantidad
                for i, bar in enumerate(bars1):
                    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                            f'n={df["cantidad"].iloc[i]}',
                            ha='center', va='bottom')
                
                plt.legend()
                plt.tight_layout()
                plt.savefig(f"resultados/precios_{operacion}.png")
                plt.close()
        
        # 2. Distribución de monedas
        plt.figure(figsize=(8, 8))
        monedas = calidad["monedas"]
        valores = list(monedas.values())
        etiquetas = [f"{k} ({v})" for k, v in monedas.items()]
        plt.pie(valores, labels=etiquetas, autopct='%1.1f%%')
        plt.title("Distribución de monedas")
        plt.savefig("resultados/distribucion_monedas.png")
        plt.close()
        
        # 3. Histograma de confianza
        for operacion in ["venta", "renta"]:
            precios = []
            for tipo_prop, stats in distribucion["estadisticas"][operacion].items():
                precios.extend([stats["promedio"]] * stats["cantidad"])
            
            if precios:
                plt.figure(figsize=(10, 6))
                plt.hist(precios, bins=50, alpha=0.7)
                plt.title(f"Distribución de precios ({operacion})")
                plt.xlabel("Precio (MXN)")
                plt.ylabel("Frecuencia")
                plt.savefig(f"resultados/distribucion_precios_{operacion}.png")
                plt.close()
    
    except Exception as e:
        logger.error(f"Error generando gráficas: {str(e)}")

def realizar_auditoria():
    """Realiza la auditoría completa de precios."""
    logger.info("Iniciando auditoría de precios...")
    
    # Cargar datos
    propiedades = cargar_datos()
    if not propiedades:
        logger.error("No se pudieron cargar las propiedades")
        return
    
    # Realizar análisis
    distribucion = analizar_distribucion_precios(propiedades)
    calidad = analizar_calidad_precios(propiedades)
    
    # Generar reporte
    reporte = {
        "fecha_auditoria": datetime.now().isoformat(),
        "distribucion_precios": distribucion,
        "calidad_datos": calidad,
        "analisis_detallado": {
            "venta": {},
            "renta": {}
        }
    }
    
    # Análisis detallado por tipo de operación
    for operacion in ["venta", "renta"]:
        stats = distribucion["estadisticas"][operacion]
        if stats:
            reporte["analisis_detallado"][operacion] = {
                "precio_promedio_general": statistics.mean([
                    s["promedio"] for s in stats.values()
                ]),
                "precio_mediana_general": statistics.median([
                    s["mediana"] for s in stats.values()
                ]),
                "total_propiedades": sum(
                    s["cantidad"] for s in stats.values()
                ),
                "distribucion_tipos": {
                    tipo: {
                        "cantidad": s["cantidad"],
                        "porcentaje": (s["cantidad"] / calidad["total_propiedades"]) * 100
                    }
                    for tipo, s in stats.items()
                }
            }
    
    # Guardar reporte
    with open(ARCHIVO_REPORTE, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    
    # Generar gráficas
    try:
        generar_graficas(distribucion, calidad)
    except Exception as e:
        logger.error(f"Error generando gráficas: {str(e)}")
    
    # Mostrar resumen
    logger.info("\nResumen de la auditoría:")
    logger.info(f"Total de propiedades: {calidad['total_propiedades']}")
    logger.info(f"Precios válidos: {calidad['precios_validos']}")
    logger.info(f"Precios inválidos: {calidad['precios_invalidos']}")
    logger.info(f"Confianza promedio: {calidad['confianza_promedio']:.2%}")
    logger.info(f"Propiedades negociables: {calidad['propiedades_negociables']}")
    logger.info(f"Propiedades con mantenimiento incluido: {calidad['incluye_mantenimiento']}")
    
    logger.info("\nDistribución de monedas:")
    for moneda, cantidad in calidad['monedas'].items():
        logger.info(f"- {moneda}: {cantidad}")
    
    logger.info("\nErrores más comunes:")
    for error, cantidad in sorted(calidad['errores_comunes'].items(), key=lambda x: x[1], reverse=True)[:5]:
        logger.info(f"- {error}: {cantidad}")
    
    logger.info("\nAnálisis por tipo de operación:")
    for operacion in ["venta", "renta"]:
        if operacion in reporte["analisis_detallado"]:
            datos = reporte["analisis_detallado"][operacion]
            if datos:
                logger.info(f"\n{operacion.upper()}:")
                logger.info(f"- Total propiedades: {datos['total_propiedades']}")
                logger.info(f"- Precio promedio: ${datos['precio_promedio_general']:,.2f}")
                logger.info(f"- Precio mediana: ${datos['precio_mediana_general']:,.2f}")
                logger.info("- Distribución por tipo:")
                for tipo, info in datos["distribucion_tipos"].items():
                    logger.info(f"  * {tipo}: {info['cantidad']} ({info['porcentaje']:.1f}%)")

if __name__ == "__main__":
    realizar_auditoria() 