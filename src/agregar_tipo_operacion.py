#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from pathlib import Path

# 1. Ruta correcta al repositorio dentro de resultados
REPO_PATH = Path("resultados") / "repositorio_propiedades.json"

# 2. Carga el repositorio
with open(REPO_PATH, 'r', encoding='utf-8') as f:
    repo = json.load(f)

# 3. Función para determinar tipo de operación
def detectar_tipo_operacion(entry):
    texto = ' '.join(filter(None, [
        entry.get('titulo', ''),
        entry.get('descripcion', ''),
    ])).lower()
    if re.search(r'\brenta\b', texto) or re.search(r'\balquiler\b', texto):
        return 'renta'
    if re.search(r'\bventa\b', texto) or re.search(r'\bse vende\b', texto):
        return 'venta'
    # Fallback por defecto
    return 'venta'

# 4. Recorre y añade el campo
if isinstance(repo, dict):
    # formato dict keyed by ID
    for prop in repo.values():
        prop['tipo_operacion'] = detectar_tipo_operacion(prop)
elif isinstance(repo, list):
    # formato lista de dicts
    for prop in repo:
        prop['tipo_operacion'] = detectar_tipo_operacion(prop)
else:
    raise ValueError("Formato de JSON inesperado en repositorio_propiedades.json")

# 5. Guarda el JSON actualizado (sobrescribe el original)
with open(REPO_PATH, 'w', encoding='utf-8') as f:
    json.dump(repo, f, ensure_ascii=False, indent=2)

print(f"✅ Se agregó 'tipo_operacion' a todas las propiedades en:\n  {REPO_PATH}")
