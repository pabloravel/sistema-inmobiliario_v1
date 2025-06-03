#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_descriptions_with_timestamp.py

Parsee incremental de descripciones inmobiliarias, añade un timestamp
al JSON principal y mantiene separados los válidos e inválidos.
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

# ─── Rutas ─────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent
RESULTADOS_DIR  = BASE_DIR / 'resultados'
INPUT_JSON      = RESULTADOS_DIR / 'repositorio_limpio.json'
VALIDOS_JSON    = RESULTADOS_DIR / 'repositorio_validos.json'
INVALIDOS_JSON  = RESULTADOS_DIR / 'repositorio_invalidos.json'

# ─── Cargar histórico previo ───────────────────────────────────
if INPUT_JSON.exists():
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        prev_container = json.load(f)
    # compatibilidad: antes era una lista; hoy es dict {date, properties}
    if isinstance(prev_container, list):
        prev_props = prev_container
    elif isinstance(prev_container, dict):
        prev_props = prev_container.get('properties', [])
    else:
        prev_props = []
else:
    prev_props = []

processed_ids = {p.get('id') for p in prev_props if p.get('id')}

# ─── Carga limpio sin ubicación ni operación ──────────────────
# (este JSON ya viene de parseo anterior, con campos básicos)
with open(INPUT_JSON, 'r', encoding='utf-8') as f:
    raw = json.load(f)

# Si raw es dict antiguo con lista, extraemos la lista
if isinstance(raw, dict) and 'properties' in raw:
    all_props = raw['properties']
elif isinstance(raw, list):
    all_props = raw
else:
    all_props = raw if isinstance(raw, list) else []

# ─── Filtrar nuevas ────────────────────────────────────────────
nuevas = [p for p in all_props if p.get('id') and p['id'] not in processed_ids]

# ─── Procesar nuevas (aquí no tocamos campos extraídos por extrae_) ──
parsed = prev_props.copy()
for prop in nuevas:
    # Simplemente conservamos tal cual, pues ya contenían descripción y operación
    parsed.append(prop)

# ─── Separar válidos e inválidos ───────────────────────────────
validos = [p for p in parsed if p.get('id') and p.get('link')]
invalidos = [p for p in parsed if not (p.get('id') and p.get('link'))]

# ─── Construir contenedor con fecha y propiedades ─────────────
output_container = {
    "date": datetime.now().strftime("%Y-%m-%d"),
    "properties": parsed
}

# ─── Guardar archivos ──────────────────────────────────────────
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)

with open(INPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output_container, f, ensure_ascii=False, indent=2)

with open(VALIDOS_JSON, 'w', encoding='utf-8') as f:
    json.dump(validos, f, ensure_ascii=False, indent=2)

with open(INVALIDOS_JSON, 'w', encoding='utf-8') as f:
    json.dump(invalidos, f, ensure_ascii=False, indent=2)

print(f"✅ Parse completado. Nuevo repositorio con timestamp → {INPUT_JSON}")
print(f"   • Válidos   → {VALIDOS_JSON} ({len(validos)})")
print(f"   • Inválidos → {INVALIDOS_JSON} ({len(invalidos)})")