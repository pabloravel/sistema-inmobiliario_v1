#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_tipo_operacion.py

Añade o actualiza el campo "tipo_operacion" en todas las entradas
de resultados/repositorio_propiedades.json utilizando la misma función
detectar_tipo_operacion de tu extractor original.
"""

import json, re
from pathlib import Path

# —————————————
# Función de detección (idéntica a la tuya)
# —————————————
def detectar_tipo_operacion(titulo, descripcion, precio_str):
    txt = " ".join([titulo or "", descripcion or "", precio_str or ""]).lower()
    if any(k in txt for k in ("renta", "alquiler", "/mes", "mensual")):
        return "Renta"
    if any(k in txt for k in ("en venta", "venta", "vender", "vendo", "vende")):
        return "Venta"
    m = re.search(r"([\d\.,]+)", precio_str or "")
    if m and int(m.group(1).replace(".", "").replace(",", "")) >= 300_000:
        return "Venta"
    return "Desconocido"

# —————————————
# Ruta a tu JSON maestro
# —————————————
repo_path = Path("resultados/repositorio_propiedades.json")

# —————————————
# Carga, actualiza y guarda
# —————————————
data = json.loads(repo_path.read_text(encoding="utf-8"))
for pid, prop in data.items():
    titulo = prop.get("titulo", "")
    descripcion = prop.get("descripcion") or prop.get("description", "")
    precio = prop.get("precio", "")
    prop["tipo_operacion"] = detectar_tipo_operacion(titulo, descripcion, precio)

repo_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"✅ Actualizado tipo_operacion en {len(data)} propiedades")