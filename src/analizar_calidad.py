#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import statistics
from typing import Dict, List
from collections import defaultdict

def analizar_precios(propiedades: List[Dict]) -> Dict:
    """Analiza la distribución y validez de los precios."""
    resultados = {
        "venta": {
            "total": 0,
            "validos": 0,
            "promedio": 0,
            "min": float('inf'),
            "max": 0,
            "sin_precio": 0
        },
        "renta": {
            "total": 0,
            "validos": 0,
            "promedio": 0,
            "min": float('inf'),
            "max": 0,
            "sin_precio": 0
        }
    }
    
    precios_venta = []
    precios_renta = []
    
    for prop in propiedades:
        tipo_op = prop.get("tipo_operacion")
        if not tipo_op or tipo_op == "desconocido":
            continue
            
        precio = prop.get("propiedad", {}).get("precio", {})
        if tipo_op == "venta":
            resultados["venta"]["total"] += 1
            if precio.get("es_valido") and precio.get("valor_normalizado"):
                resultados["venta"]["validos"] += 1
                valor = precio["valor_normalizado"]
                precios_venta.append(valor)
                resultados["venta"]["min"] = min(resultados["venta"]["min"], valor)
                resultados["venta"]["max"] = max(resultados["venta"]["max"], valor)
            else:
                resultados["venta"]["sin_precio"] += 1
        elif tipo_op == "renta":
            resultados["renta"]["total"] += 1
            if precio.get("es_valido") and precio.get("valor_normalizado"):
                resultados["renta"]["validos"] += 1
                valor = precio["valor_normalizado"]
                precios_renta.append(valor)
                resultados["renta"]["min"] = min(resultados["renta"]["min"], valor)
                resultados["renta"]["max"] = max(resultados["renta"]["max"], valor)
            else:
                resultados["renta"]["sin_precio"] += 1
    
    if precios_venta:
        resultados["venta"]["promedio"] = statistics.mean(precios_venta)
    if precios_renta:
        resultados["renta"]["promedio"] = statistics.mean(precios_renta)
    
    return resultados

def analizar_ubicaciones(propiedades: List[Dict]) -> Dict:
    """Analiza la calidad de la extracción de ubicaciones."""
    resultados = {
        "total": len(propiedades),
        "con_ciudad": 0,
        "con_colonia": 0,
        "con_referencias": 0,
        "ciudades": defaultdict(int),
        "colonias": defaultdict(int)
    }
    
    for prop in propiedades:
        ubicacion = prop.get("ubicacion", {})
        if ubicacion.get("ciudad"):
            resultados["con_ciudad"] += 1
            resultados["ciudades"][ubicacion["ciudad"]] += 1
        if ubicacion.get("colonia"):
            resultados["con_colonia"] += 1
            resultados["colonias"][ubicacion["colonia"]] += 1
        if ubicacion.get("referencias"):
            resultados["con_referencias"] += 1
    
    return resultados

def analizar_caracteristicas(propiedades: List[Dict]) -> Dict:
    """Analiza la calidad de la extracción de características."""
    resultados = {
        "total": len(propiedades),
        "con_recamaras": 0,
        "con_banos": 0,
        "con_superficie": 0,
        "con_construccion": 0,
        "distribucion_recamaras": defaultdict(int),
        "distribucion_banos": defaultdict(int),
        "rangos_superficie": {
            "0-100": 0,
            "100-200": 0,
            "200-500": 0,
            "500+": 0
        }
    }
    
    for prop in propiedades:
        caract = prop.get("propiedad", {}).get("caracteristicas", {})
        
        if caract.get("recamaras"):
            resultados["con_recamaras"] += 1
            resultados["distribucion_recamaras"][caract["recamaras"]] += 1
            
        if caract.get("banos"):
            resultados["con_banos"] += 1
            resultados["distribucion_banos"][caract["banos"]] += 1
            
        if caract.get("superficie_m2"):
            resultados["con_superficie"] += 1
            sup = caract["superficie_m2"]
            if sup <= 100:
                resultados["rangos_superficie"]["0-100"] += 1
            elif sup <= 200:
                resultados["rangos_superficie"]["100-200"] += 1
            elif sup <= 500:
                resultados["rangos_superficie"]["200-500"] += 1
            else:
                resultados["rangos_superficie"]["500+"] += 1
                
        if caract.get("construccion_m2"):
            resultados["con_construccion"] += 1
    
    return resultados

def analizar_amenidades(propiedades: List[Dict]) -> Dict:
    """Analiza la calidad de la extracción de amenidades."""
    resultados = {
        "total": len(propiedades),
        "distribucion": defaultdict(int),
        "tipos_seguridad": defaultdict(int),
        "tipos_alberca": defaultdict(int),
        "tipos_areas_comunes": defaultdict(int)
    }
    
    for prop in propiedades:
        amenidades = prop.get("propiedad", {}).get("amenidades", {})
        
        # Contar amenidades básicas
        for amenidad in ["alberca", "jardin", "estacionamiento", "areas_comunes", "deportivas", "seguridad"]:
            if amenidades.get(amenidad, {}).get("presente"):
                resultados["distribucion"][amenidad] += 1
        
        # Analizar tipos específicos
        if amenidades.get("seguridad", {}).get("tipo"):
            resultados["tipos_seguridad"][amenidades["seguridad"]["tipo"]] += 1
            
        if amenidades.get("alberca", {}).get("tipo"):
            resultados["tipos_alberca"][amenidades["alberca"]["tipo"]] += 1
            
        if amenidades.get("areas_comunes", {}).get("tipos"):
            for tipo in amenidades["areas_comunes"]["tipos"]:
                resultados["tipos_areas_comunes"][tipo] += 1
    
    return resultados

def analizar_calidad_datos(propiedades: List[Dict]) -> Dict:
    """Analiza las métricas de calidad de los datos."""
    resultados = {
        "total": len(propiedades),
        "completitud": {
            "promedio": 0,
            "distribucion": defaultdict(int)
        },
        "confiabilidad": {
            "promedio": 0,
            "distribucion": defaultdict(int)
        },
        "consistencia": {
            "promedio": 0,
            "distribucion": defaultdict(int)
        },
        "campos_faltantes_comunes": defaultdict(int),
        "campos_dudosos_comunes": defaultdict(int),
        "inconsistencias_comunes": defaultdict(int)
    }
    
    completitud_total = 0
    confiabilidad_total = 0
    consistencia_total = 0
    
    for prop in propiedades:
        calidad = prop.get("calidad_datos", {})
        
        # Acumular métricas
        completitud = calidad.get("completitud", 0)
        confiabilidad = calidad.get("confiabilidad", 0)
        consistencia = calidad.get("consistencia", 0)
        
        completitud_total += completitud
        confiabilidad_total += confiabilidad
        consistencia_total += consistencia
        
        # Distribuir en rangos
        resultados["completitud"]["distribucion"][f"{(completitud//10)*10}-{(completitud//10)*10+10}"] += 1
        resultados["confiabilidad"]["distribucion"][f"{(confiabilidad//10)*10}-{(confiabilidad//10)*10+10}"] += 1
        resultados["consistencia"]["distribucion"][f"{(consistencia//10)*10}-{(consistencia//10)*10+10}"] += 1
        
        # Contar problemas comunes
        for campo in calidad.get("campos_faltantes", []):
            resultados["campos_faltantes_comunes"][campo] += 1
        for campo in calidad.get("campos_dudosos", []):
            resultados["campos_dudosos_comunes"][campo] += 1
        for inconsistencia in calidad.get("inconsistencias", []):
            resultados["inconsistencias_comunes"][inconsistencia] += 1
    
    # Calcular promedios
    if propiedades:
        resultados["completitud"]["promedio"] = completitud_total / len(propiedades)
        resultados["confiabilidad"]["promedio"] = confiabilidad_total / len(propiedades)
        resultados["consistencia"]["promedio"] = consistencia_total / len(propiedades)
    
    return resultados

def main():
    """Función principal que ejecuta el análisis."""
    print("Analizando propiedades estructuradas...")
    
    # Leer archivo de propiedades
    with open("resultados/propiedades_estructuradas.json", "r", encoding="utf-8") as f:
        datos = json.load(f)
        propiedades = datos.get("propiedades", [])
    
    print(f"\nTotal de propiedades a analizar: {len(propiedades)}")
    
    # Realizar análisis
    analisis_precios = analizar_precios(propiedades)
    analisis_ubicaciones = analizar_ubicaciones(propiedades)
    analisis_caracteristicas = analizar_caracteristicas(propiedades)
    analisis_amenidades = analizar_amenidades(propiedades)
    analisis_calidad = analizar_calidad_datos(propiedades)
    
    # Imprimir resultados
    print("\n=== ANÁLISIS DE PRECIOS ===")
    print("\nVENTA:")
    print(f"Total: {analisis_precios['venta']['total']}")
    print(f"Válidos: {analisis_precios['venta']['validos']}")
    print(f"Promedio: ${analisis_precios['venta']['promedio']:,.2f}")
    print(f"Mínimo: ${analisis_precios['venta']['min']:,.2f}")
    print(f"Máximo: ${analisis_precios['venta']['max']:,.2f}")
    print(f"Sin precio: {analisis_precios['venta']['sin_precio']}")
    
    print("\nRENTA:")
    print(f"Total: {analisis_precios['renta']['total']}")
    print(f"Válidos: {analisis_precios['renta']['validos']}")
    print(f"Promedio: ${analisis_precios['renta']['promedio']:,.2f}")
    print(f"Mínimo: ${analisis_precios['renta']['min']:,.2f}")
    print(f"Máximo: ${analisis_precios['renta']['max']:,.2f}")
    print(f"Sin precio: {analisis_precios['renta']['sin_precio']}")
    
    print("\n=== ANÁLISIS DE UBICACIONES ===")
    print(f"Total con ciudad: {analisis_ubicaciones['con_ciudad']}")
    print(f"Total con colonia: {analisis_ubicaciones['con_colonia']}")
    print(f"Total con referencias: {analisis_ubicaciones['con_referencias']}")
    print("\nTop 5 ciudades:")
    for ciudad, count in sorted(analisis_ubicaciones['ciudades'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"- {ciudad}: {count}")
    
    print("\n=== ANÁLISIS DE CARACTERÍSTICAS ===")
    print(f"Con recámaras: {analisis_caracteristicas['con_recamaras']}")
    print(f"Con baños: {analisis_caracteristicas['con_banos']}")
    print(f"Con superficie: {analisis_caracteristicas['con_superficie']}")
    print(f"Con construcción: {analisis_caracteristicas['con_construccion']}")
    print("\nDistribución de recámaras:")
    for rec, count in sorted(analisis_caracteristicas['distribucion_recamaras'].items()):
        print(f"- {rec} recámaras: {count}")
    
    print("\n=== ANÁLISIS DE AMENIDADES ===")
    print("\nAmenidades más comunes:")
    for amenidad, count in sorted(analisis_amenidades['distribucion'].items(), key=lambda x: x[1], reverse=True):
        print(f"- {amenidad}: {count}")
    
    print("\n=== ANÁLISIS DE CALIDAD DE DATOS ===")
    print(f"\nCompletitud promedio: {analisis_calidad['completitud']['promedio']:.2f}%")
    print(f"Confiabilidad promedio: {analisis_calidad['confiabilidad']['promedio']:.2f}%")
    print(f"Consistencia promedio: {analisis_calidad['consistencia']['promedio']:.2f}%")
    
    print("\nCampos faltantes más comunes:")
    for campo, count in sorted(analisis_calidad['campos_faltantes_comunes'].items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"- {campo}: {count}")
    
    # Guardar resultados detallados
    resultados_completos = {
        "precios": analisis_precios,
        "ubicaciones": analisis_ubicaciones,
        "caracteristicas": analisis_caracteristicas,
        "amenidades": analisis_amenidades,
        "calidad": analisis_calidad
    }
    
    with open("resultados/analisis_calidad_detallado.json", "w", encoding="utf-8") as f:
        json.dump(resultados_completos, f, indent=2, ensure_ascii=False)
    
    print("\nAnálisis detallado guardado en 'resultados/analisis_calidad_detallado.json'")

if __name__ == "__main__":
    main() 