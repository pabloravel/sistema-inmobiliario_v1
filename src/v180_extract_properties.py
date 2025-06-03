# v180_extract_properties.py
# Versión restaurada completa con todas las mejoras acumuladas

import json
import os
import re
from collections import defaultdict, Counter
from copy import deepcopy
from modelo_banos import predict_banos  # Módulo externo para predicción de Baños

# Constantes y configuración
ALL_FIELDS = [
    "Id", "Tipo", "Precio", "Moneda", "Operacion", "Provincia", "Ciudad", "Zona", "Direccion",
    "Ambientes", "Dormitorios", "Baños", "Superficie", "SuperficieCubierta", "Antiguedad",
    "Estado", "Orientacion", "Expensas", "Descripcion", "Cocheras", "TipoCocheras", "Piso",
    "Departamento", "Ascensor", "Balcon", "Patio", "Jardin", "Pileta", "Parrilla", "Calefaccion",
    "AguaCaliente", "AireAcondicionado", "Seguridad", "Cochera", "Lavadero", "Terraza",
    "Amoblado", "Categoria", "TipoPiso", "TipoTecho", "TipoVentana", "TipoPuerta"
]

INPUT_FILE = "resultados/repositorio_propiedades.json"
OUTPUT_ALL = "resultados/results_v180_all.json"
OUTPUT_INVALID = "resultados/results_v180_invalid.json"
OUTPUT_MISSING_BY_FIELD = "resultados/results_v180_missing_by_field.json"
OUTPUT_LOGS_HEURISTICAS = "resultados/results_v180_logs_heuristicas.json"
OUTPUT_DEBUG_SELECCION = "resultados/debug_seleccion_final.json"
OUTPUT_TRAIN_FORZADO_TEMPLATE = "resultados/train_forzado_{}.json"

# ==================== FUNCIONES AUXILIARES ====================

def normalizar(texto):
    return re.sub(r"\s+", " ", texto.strip().lower()) if texto else ""

def extraer_valor_numerico(texto):
    if not texto: return None
    texto = texto.replace(",", ".")
    match = re.search(r"(\d+(\.\d+)?)", texto)
    return float(match.group(1)) if match else None

def calcular_completitud(prop):
    llenos = sum(1 for campo in ALL_FIELDS if prop.get(campo) not in [None, "", []])
    return round(100 * llenos / len(ALL_FIELDS), 2)

def aplicar_heuristicas(prop):
    logs = []
    if not prop.get("Baños") and prop.get("Descripcion"):
        pred, conf = predict_banos(prop["Descripcion"])
        if conf >= 0.5:
            prop["Baños"] = pred
            logs.append(f"Heurística: modelo_banos {pred} (conf {conf:.2f})")
        else:
            logs.append(f"Modelo de Baños: baja confianza ({conf:.2f})")

    if not prop.get("Ambientes") and prop.get("Dormitorios") and prop.get("Baños"):
        try:
            prop["Ambientes"] = prop["Dormitorios"] + prop["Baños"] - 1
            logs.append("Heurística: Ambientes inferido por Dormitorios + Baños")
        except:
            pass

    return prop, logs

def extraer_propiedad_estandar(raw):
    prop = {campo: raw.get(campo) for campo in ALL_FIELDS}
    if isinstance(prop.get("Descripcion"), str):
        prop["Descripcion"] = normalizar(prop["Descripcion"])
    if isinstance(prop.get("Direccion"), str):
        prop["Direccion"] = normalizar(prop["Direccion"])
    for campo in ["Precio", "Baños", "Ambientes", "Dormitorios", "Superficie", "SuperficieCubierta", "Cocheras"]:
        if prop.get(campo):
            try:
                prop[campo] = extraer_valor_numerico(str(prop[campo]))
            except:
                prop[campo] = None
    return prop

def sospechosa(prop):
    score, razones = 0, []
    if prop.get("Precio") is not None:
        if prop["Precio"] < 10000:
            score += 1
            razones.append("Precio muy bajo")
        elif prop["Precio"] > 100_000_000:
            score += 1
            razones.append("Precio exagerado")
    if prop.get("Baños") is not None and prop["Baños"] > 10:
        score += 1
        razones.append("Baños > 10")
    return score, razones

# ==================== MAIN ====================

def main():
    if not os.path.isfile(INPUT_FILE):
        print(f"❌ No se encontró el archivo: {INPUT_FILE}")
        return

    with open(INPUT_FILE, encoding="utf-8") as f:
        base = json.load(f)

    resultados, excluidos = [], []
    logs = []
    faltantes = defaultdict(list)
    train_forzado = defaultdict(list)

    for raw in base.values() if isinstance(base, dict) else base:
        prop = extraer_propiedad_estandar(raw)
        prop, heuristicas = aplicar_heuristicas(prop)
        score_sospecha, razones = sospechosa(prop)

        log = {
            "Id": prop.get("Id"),
            "Completitud": calcular_completitud(prop),
            "ScoreSospecha": score_sospecha,
            "Razones": razones,
            "Heuristicas": heuristicas
        }

        if not prop.get("Id") or not prop.get("Precio") or not prop.get("Tipo") or score_sospecha > 0:
            excl = deepcopy(prop)
            excl["Descripcion"] = prop.get("Descripcion", "")
            excluidos.append(excl)
            logs.append(log)
            continue

        resultados.append(prop)
        logs.append(log)

        for campo in ALL_FIELDS:
            if not prop.get(campo):
                faltantes[campo].append(prop.get("Id"))
            else:
                train_forzado[campo].append({"Id": prop.get("Id"), campo: prop.get(campo)})

    # Exportar
    os.makedirs("resultados", exist_ok=True)
    json.dump(resultados, open(OUTPUT_ALL, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(excluidos, open(OUTPUT_INVALID, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(logs, open(OUTPUT_LOGS_HEURISTICAS, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(faltantes, open(OUTPUT_MISSING_BY_FIELD, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    json.dump(logs, open(OUTPUT_DEBUG_SELECCION, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for campo, registros in train_forzado.items():
        path = OUTPUT_TRAIN_FORZADO_TEMPLATE.format(campo)
        json.dump(registros, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\n✅ Procesamiento completado y resultados exportados.")

if __name__ == "__main__":
    main()
