#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

def verificar_caso():
    """Verifica los cambios en el caso específico"""
    # Cargar datos
    with open("resultados/propiedades_estructuradas.json", "r", encoding="utf-8") as f:
        datos = json.load(f)
    
    # Buscar la propiedad específica
    id_buscar = "1002198755279328"
    propiedad = None
    
    for prop in datos["propiedades"]:
        if prop["id"] == id_buscar:
            propiedad = prop
            break
    
    if not propiedad:
        print(f"No se encontró la propiedad con ID {id_buscar}")
        return
    
    # Imprimir resultados
    print("\n=== VERIFICACIÓN DE CASO ESPECÍFICO ===")
    print(f"ID: {propiedad['id']}")
    print(f"Link: {propiedad['link']}")
    print("\nDatos extraídos:")
    print(f"Precio: {propiedad['propiedad']['precio']}")
    print(f"Tipo propiedad: {propiedad['propiedad']['tipo_propiedad']}")
    print(f"Tipo operación: {propiedad['propiedad']['tipo_operacion']}")
    
    caract = propiedad['descripcion_detallada']['caracteristicas']
    print("\nCaracterísticas:")
    print(f"- Superficie: {caract['superficie_m2']} m²")
    print(f"- Construcción: {caract['construccion_m2']} m²")
    print(f"- Recámaras: {caract['recamaras']}")
    print(f"- Baños: {caract['banos']}")
    print(f"- Niveles: {caract['niveles']}")
    print(f"- Es un nivel: {caract['es_un_nivel']}")
    print(f"- Recámara en PB: {caract['recamara_pb']}")
    print(f"- Estacionamientos: {caract['estacionamientos']}")

if __name__ == "__main__":
    verificar_caso() 