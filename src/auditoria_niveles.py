#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from collections import Counter

def analizar_descripcion(descripcion, es_un_nivel, recamara_pb):
    """Analiza si hay posibles inconsistencias en la detección"""
    desc_lower = descripcion.lower()
    
    # Palabras clave que indican múltiples niveles
    multi_nivel = any(p in desc_lower for p in [
        'planta alta', 'segundo piso', 'dos niveles', 'dos plantas',
        'primer piso.*segundo piso', 'planta baja.*planta alta'
    ])
    
    # Palabras clave que indican un nivel
    un_nivel = any(p in desc_lower for p in [
        'un nivel', 'una planta', 'solo planta baja'
    ])
    
    # Palabras clave para recámara en PB
    pb_keywords = [
        'recámara en planta baja', 'recamara en pb', 
        'habitación en planta baja', 'dormitorio en pb',
        'planta baja: 1 recámara', 'pb: 1 recamara'
    ]
    tiene_rec_pb = any(p in desc_lower for p in pb_keywords)
    
    # Detectar posibles inconsistencias
    inconsistencias = []
    
    if es_un_nivel and multi_nivel:
        inconsistencias.append("Marcada como un nivel pero menciona múltiples niveles")
    elif not es_un_nivel and un_nivel and not multi_nivel:
        inconsistencias.append("Marcada como múltiples niveles pero solo menciona un nivel")
    
    if recamara_pb and es_un_nivel:
        inconsistencias.append("Marcada con recámara en PB pero es de un nivel (redundante)")
    elif recamara_pb and not tiene_rec_pb and not 'planta baja' in desc_lower:
        inconsistencias.append("Marcada con recámara en PB pero no hay mención clara")
    
    return inconsistencias

# Cargar datos
with open("resultados/propiedades_estructuradas.json", "r", encoding="utf-8") as f:
    datos = json.load(f)

# Contadores y estadísticas
total = len(datos["propiedades"])
stats = {
    "un_nivel": 0,
    "multi_nivel": 0,
    "con_recamara_pb": 0,
    "con_inconsistencias": 0
}

print("\n=== ANÁLISIS DE NIVELES Y RECÁMARAS EN PB ===")
print(f"\nTotal de propiedades: {total}")

# Analizar cada propiedad
propiedades_con_inconsistencias = []

for prop in datos["propiedades"]:
    caract = prop['descripcion_detallada']['caracteristicas']
    es_un_nivel = caract['es_un_nivel']
    recamara_pb = caract['recamara_pb']
    
    # Actualizar estadísticas
    if es_un_nivel:
        stats["un_nivel"] += 1
    else:
        stats["multi_nivel"] += 1
    
    if recamara_pb:
        stats["con_recamara_pb"] += 1
    
    # Buscar inconsistencias
    inconsistencias = analizar_descripcion(
        prop['descripcion'],
        es_un_nivel,
        recamara_pb
    )
    
    if inconsistencias:
        stats["con_inconsistencias"] += 1
        propiedades_con_inconsistencias.append({
            "id": prop["id"],
            "descripcion": prop["descripcion"][:200] + "...",  # Primeros 200 caracteres
            "es_un_nivel": es_un_nivel,
            "recamara_pb": recamara_pb,
            "inconsistencias": inconsistencias
        })

# Imprimir estadísticas
print("\nESTADÍSTICAS:")
print(f"- Propiedades de un nivel: {stats['un_nivel']} ({stats['un_nivel']/total*100:.1f}%)")
print(f"- Propiedades multinivel: {stats['multi_nivel']} ({stats['multi_nivel']/total*100:.1f}%)")
print(f"- Con recámara en PB: {stats['con_recamara_pb']} ({stats['con_recamara_pb']/total*100:.1f}%)")
print(f"- Con inconsistencias: {stats['con_inconsistencias']} ({stats['con_inconsistencias']/total*100:.1f}%)")

# Imprimir casos con inconsistencias
if propiedades_con_inconsistencias:
    print("\nDETALLE DE INCONSISTENCIAS:")
    for i, prop in enumerate(propiedades_con_inconsistencias, 1):
        print(f"\n{i}. ID: {prop['id']}")
        print(f"   Descripción: {prop['descripcion']}")
        print(f"   Es un nivel: {prop['es_un_nivel']}")
        print(f"   Recámara en PB: {prop['recamara_pb']}")
        print("   Inconsistencias detectadas:")
        for inc in prop['inconsistencias']:
            print(f"   - {inc}") 