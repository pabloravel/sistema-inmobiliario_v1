#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from collections import Counter

def analizar_resultados():
    """Analiza los resultados del procesamiento"""
    # Cargar datos
    with open("resultados/propiedades_estructuradas.json", "r", encoding="utf-8") as f:
        datos = json.load(f)
    
    propiedades = datos["propiedades"]
    total = len(propiedades)
    
    # Contadores
    niveles = Counter()
    recamaras_pb = Counter()
    casos_especiales = []
    
    # Análisis detallado
    for prop in propiedades:
        caract = prop["descripcion_detallada"]["caracteristicas"]
        desc = prop["descripcion"].lower()
        
        # Clasificar por niveles
        if caract["es_un_nivel"]:
            niveles["un_nivel"] += 1
        else:
            niveles["multiple_niveles"] += 1
        
        # Clasificar por recámara en PB
        if caract["recamara_pb"]:
            recamaras_pb["con_recamara_pb"] += 1
            
            # Si tiene recámara en PB, verificar que no sea de un nivel
            if caract["es_un_nivel"]:
                casos_especiales.append({
                    "id": prop["id"],
                    "link": prop["link"],
                    "descripcion": prop["descripcion"],
                    "error": "Marcada con recámara en PB pero es de un nivel"
                })
        else:
            recamaras_pb["sin_recamara_pb"] += 1
            
            # Buscar posibles falsos negativos
            if not caract["es_un_nivel"] and any(p in desc for p in [
                "recámara en planta baja", "recamara en pb", 
                "habitación en planta baja", "dormitorio en pb"
            ]):
                casos_especiales.append({
                    "id": prop["id"],
                    "link": prop["link"],
                    "descripcion": prop["descripcion"],
                    "error": "Posible falso negativo en detección de recámara en PB"
                })
    
    # Imprimir resultados
    print("\n=== ANÁLISIS DE NIVELES Y RECÁMARAS EN PB ===")
    print(f"\nTotal de propiedades analizadas: {total}")
    
    print("\nDistribución por niveles:")
    for tipo, cantidad in niveles.items():
        porcentaje = (cantidad / total) * 100
        print(f"- {tipo}: {cantidad} ({porcentaje:.1f}%)")
    
    print("\nDistribución de recámaras en PB:")
    for tipo, cantidad in recamaras_pb.items():
        porcentaje = (cantidad / total) * 100
        print(f"- {tipo}: {cantidad} ({porcentaje:.1f}%)")
    
    if casos_especiales:
        print("\nCasos que requieren revisión:")
        for caso in casos_especiales:
            print(f"\nID: {caso['id']}")
            print(f"Link: {caso['link']}")
            print(f"Error: {caso['error']}")
            print(f"Descripción: {caso['descripcion'][:200]}...")

if __name__ == "__main__":
    analizar_resultados() 