#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
borrar_propiedades_v2.py

Script para borrar 10 propiedades aleatorias del repositorio maestro
y crear un backup antes de realizar los cambios.
"""

import json
import random
import shutil
from datetime import datetime
import os

# Constantes
REPO_MASTER = "resultados/repositorio_propiedades.json"
NUM_PROPIEDADES = 10

def main():
    # Verificar que existe el repositorio
    if not os.path.exists(REPO_MASTER):
        print("❌ No se encontró el repositorio maestro")
        return

    # Crear backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{REPO_MASTER}.{timestamp}.backup"
    shutil.copy2(REPO_MASTER, backup_path)
    print(f"✓ Backup creado en: {backup_path}")

    # Cargar repositorio
    with open(REPO_MASTER, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    total_inicial = len(data)
    print(f"\nTotal de propiedades inicial: {total_inicial}")

    # Seleccionar propiedades aleatorias
    ids = list(data.keys())
    ids_a_borrar = random.sample(ids, NUM_PROPIEDADES)

    print("\nPropiedades que serán eliminadas:")
    for i, id_prop in enumerate(ids_a_borrar, 1):
        prop = data[id_prop]
        print(f"{i}. ID: {id_prop}")
        print(f"   Título: {prop.get('titulo', 'Sin título')}")
        print(f"   Link: {prop.get('link', 'Sin link')}\n")

    # Confirmar borrado
    confirmar = input("¿Desea proceder con el borrado? (s/n): ")
    if confirmar.lower() != "s":
        print("\n❌ Operación cancelada")
        return

    # Borrar propiedades
    for id_prop in ids_a_borrar:
        del data[id_prop]

    # Guardar cambios
    with open(REPO_MASTER, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Se eliminaron {NUM_PROPIEDADES} propiedades")
    print(f"✓ Total de propiedades final: {len(data)}")
    print(f"✓ Backup guardado en: {backup_path}")

if __name__ == "__main__":
    main() 