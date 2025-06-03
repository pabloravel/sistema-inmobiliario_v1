#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

# ID de la propiedad a verificar
ID_PROPIEDAD = "1002198755279328"

# Cargar datos
with open("resultados/propiedades_estructuradas.json", "r", encoding="utf-8") as f:
    datos = json.load(f)

# Buscar la propiedad
for prop in datos["propiedades"]:
    if prop["id"] == ID_PROPIEDAD:
        print("\n=== PROPIEDAD ENCONTRADA ===")
        print(f"ID: {prop['id']}")
        print(f"\nDESCRIPCIÓN:")
        print(prop['descripcion'])
        print("\nCARACTERÍSTICAS:")
        caract = prop['descripcion_detallada']['caracteristicas']
        print(f"- Niveles: {caract['niveles']}")
        print(f"- Es un nivel: {caract['es_un_nivel']}")
        print(f"- Recámara en PB: {caract['recamara_pb']}")
        print(f"- Total recámaras: {caract['recamaras']}")
        print(f"- Total baños: {caract['banos']}")
        print(f"- Superficie: {caract['superficie_m2']} m²")
        print(f"- Construcción: {caract['construccion_m2']} m²")
        break 