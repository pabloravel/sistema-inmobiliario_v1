import json
import os
import re
from collections import defaultdict, Counter
from copy import deepcopy
from modelo_banos import predict_banos  # Modelo externo

# Constantes de configuración
ALL_FIELDS = [
    "Id", "Tipo", "Precio", "Moneda", "Operacion", "Provincia", "Ciudad", "Zona", "Direccion",
    "Ambientes", "Dormitorios", "Baños", "Superficie", "SuperficieCubierta", "Antiguedad",
    "Estado", "Orientacion", "Expensas", "Descripcion", "Cocheras", "TipoCocheras", "Piso",
    "Departamento", "Ascensor", "Balcon", "Patio", "Jardin", "Pileta", "Parrilla", "Calefaccion",
    "AguaCaliente", "AireAcondicionado", "Seguridad", "Cochera", "Lavadero", "Terraza",
    "Amoblado", "Categoria", "TipoPiso", "TipoTecho", "TipoVentana", "TipoPuerta"
]

INPUT_FILE = "resultados/repositorio_propiedades.json"
OUTPUT_ALL = "results_v181_all.json"
OUTPUT_INVALID = "results_v181_invalid.json"
OUTPUT_MISSING_BY_FIELD = "results_v181_missing_by_field.json"
OUTPUT_LOGS_HEURISTICAS = "results_v181_logs_heuristicas.json"
OUTPUT_DEBUG_SELECCION = "resultados/debug_seleccion_final.json"
OUTPUT_TRAIN_FORZADO_TEMPLATE = "resultados/train_forzado_{}.json"

def normalizar_texto(texto):
    if not texto:
        return ""
    return re.sub(r"\s+", " ", texto.lower().strip())

def extraer_valor_num(texto):
    try:
        return float(re.sub(r"[^\d.]", "", texto.replace(",", ".")))
    except:
        return None

def aplicar_heuristicas(prop):
    logs = []
    if not prop.get("Baños") and prop.get("Descripcion"):
        pred, conf = predict_banos(prop["Descripcion"])
        if conf >= 0.6:
            prop["Baños"] = pred
            logs.append(f"Heurística: predict_banos={pred} con confianza {conf:.2f}")
        else:
            logs.append(f"Heurística: confianza insuficiente ({conf:.2f}) para predicción de Baños")
    if not prop.get("Ambientes") and prop.get("Dormitorios") and prop.get("Baños"):
        amb = prop["Dormitorios"] + prop["Baños"] - 1
        if amb > 0:
            prop["Ambientes"] = amb
            logs.append(f"Heurística: Ambientes inferidos como {amb}")
    return prop, logs

def calcular_score_sospecha(prop):
    score, razones = 0, []
    if prop.get("Precio") is not None:
        if prop["Precio"] < 10000:
            score += 1
            razones.append("Precio demasiado bajo")
        elif prop["Precio"] > 10000000:
            score += 1
            razones.append("Precio demasiado alto")
    if prop.get("Dormitorios") and prop.get("Ambientes") and prop["Dormitorios"] > prop["Ambientes"]:
        score += 1
        razones.append("Dormitorios > Ambientes")
    if prop.get("Baños") is not None and not (0 <= prop["Baños"] <= 10):
        score += 1
        razones.append("Baños fuera de rango")
    return score, razones

def calcular_completitud(prop):
    completitud = {}
    total, completos = len(ALL_FIELDS), 0
    for campo in ALL_FIELDS:
        v = prop.get(campo)
        if v not in [None, "", []]:
            completitud[campo] = 1
            completos += 1
        else:
            completitud[campo] = 0
    completitud["total"] = completos / total
    return completitud

def extraer_campos_completos(raw_prop):
    prop = {}
    for campo in ALL_FIELDS:
        v = raw_prop.get(campo)
        if isinstance(v, str): v = v.strip()
        if v == "": v = None
        prop[campo] = v
    if prop.get("Descripcion"):
        prop["Descripcion"] = normalizar_texto(prop["Descripcion"])
    if prop.get("Direccion"):
        prop["Direccion"] = normalizar_texto(prop["Direccion"])
    for campo_num in ["Precio", "Ambientes", "Dormitorios", "Baños", "Superficie", "SuperficieCubierta", "Antiguedad", "Expensas", "Cocheras", "Piso"]:
        if prop.get(campo_num) is not None:
            prop[campo_num] = extraer_valor_num(str(prop[campo_num]))
    return prop

def guardar_json(data, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    if not os.path.isfile(INPUT_FILE):
        print(f"❌ No se encontró el archivo: {INPUT_FILE}")
        return

    with open(INPUT_FILE, encoding="utf-8") as f:
        raw_data = json.load(f)

    propiedades_procesadas, propiedades_invalidas = [], []
    logs_heuristicas = []
    debug_seleccion_final = []
    train_forzado = defaultdict(list)
    missing_by_field = {campo: [] for campo in ALL_FIELDS}

    for idx, raw in enumerate(raw_data.values()):
        prop = extraer_campos_completos(raw)
        prop, logs = aplicar_heuristicas(prop)
        sospecha, razones = calcular_score_sospecha(prop)
        completitud = calcular_completitud(prop)

        log_det = {
            "Id": prop.get("Id"),
            "Heuristicas": logs,
            "ScoreSospecha": sospecha,
            "RazonesSospecha": razones,
            "Completitud": completitud
        }

        for campo in ALL_FIELDS:
            if completitud[campo] == 0:
                missing_by_field[campo].append(prop.get("Id") or f"idx_{idx}")

        valido = prop.get("Id") and prop.get("Precio") and prop.get("Tipo") and sospecha == 0

        if valido:
            propiedades_procesadas.append(prop)
        else:
            invalida = deepcopy(prop)
            invalida["Descripcion"] = prop.get("Descripcion", "")
            propiedades_invalidas.append(invalida)

        logs_heuristicas.append(log_det)
        debug_seleccion_final.append({
            "Id": prop.get("Id"),
            "ScoreSospecha": sospecha,
            "CompletitudTotal": completitud["total"],
            "HeuristicasAplicadas": logs,
            "Validacion": log_det.get("Validacion", "OK")
        })

        if valido and completitud["total"] >= 0.8:
            for campo in ALL_FIELDS:
                if completitud[campo] == 1:
                    train_forzado[campo].append({"Id": prop.get("Id"), campo: prop.get(campo)})

    guardar_json(propiedades_procesadas, OUTPUT_ALL)
    guardar_json(propiedades_invalidas, OUTPUT_INVALID)
    guardar_json(missing_by_field, OUTPUT_MISSING_BY_FIELD)
    guardar_json(logs_heuristicas, OUTPUT_LOGS_HEURISTICAS)
    os.makedirs("resultados", exist_ok=True)
    guardar_json(debug_seleccion_final, OUTPUT_DEBUG_SELECCION)
    for campo, registros in train_forzado.items():
        guardar_json(registros, OUTPUT_TRAIN_FORZADO_TEMPLATE.format(campo))

    print(f"✅ Procesamiento completado. Archivos exportados:\n"
          f" - {OUTPUT_ALL}\n"
          f" - {OUTPUT_INVALID}\n"
          f" - {OUTPUT_MISSING_BY_FIELD}\n"
          f" - {OUTPUT_LOGS_HEURISTICAS}\n"
          f" - {OUTPUT_DEBUG_SELECCION}\n"
          f" - Archivos train forzado por campo en 'resultados/'")

if __name__ == "__main__":
    main()
