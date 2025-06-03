#!/usr/bin/env python3
import json
import random
import os
from datetime import datetime

# Crear backup
backup_path = f"resultados/backups/repositorio_propiedades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
os.makedirs("resultados/backups", exist_ok=True)

# Cargar repositorio
with open("resultados/repositorio_propiedades.json", "r", encoding="utf-8") as f:
    repo = json.load(f)

# Hacer backup
with open(backup_path, "w", encoding="utf-8") as f:
    json.dump(repo, f, indent=2, ensure_ascii=False)
print(f"Backup creado en: {backup_path}")

# Seleccionar 20 IDs aleatorios
ids = list(repo.keys())
ids_a_borrar = random.sample(ids, 20)

# Borrar propiedades
for id_prop in ids_a_borrar:
    del repo[id_prop]

# Guardar repositorio actualizado
with open("resultados/repositorio_propiedades.json", "w", encoding="utf-8") as f:
    json.dump(repo, f, indent=2, ensure_ascii=False)

print(f"\nSe borraron {len(ids_a_borrar)} propiedades:")
for id_prop in ids_a_borrar:
    print(f"- {id_prop}")

print(f"\nRepositorio actualizado con {len(repo)} propiedades") 