#!/usr/bin/env python3
import json
from pathlib import Path

# 1) Ruta de tu JSON ya parseado
in_path = Path("resultados/repositorio_limpio.json")

# 2) Carga todas las propiedades
with in_path.open("r", encoding="utf-8") as f:
    props = json.load(f)

validos = []
invalidos = []

# 3) Sepáralas según tengan id y link
for p in props:
    if p.get("id") and p.get("link"):
        validos.append(p)
    else:
        invalidos.append(p)

# 4) Guarda los dos archivos
out_good = Path("resultados/repositorio_validos.json")
out_bad  = Path("resultados/repositorio_invalidos.json")

out_good.write_text(json.dumps(validos, ensure_ascii=False, indent=2), encoding="utf-8")
out_bad .write_text(json.dumps(invalidos, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"✅ {len(validos)} válidos guardados en {out_good.name}")
print(f"⚠️  {len(invalidos)} incompletos guardados en {out_bad.name}")
