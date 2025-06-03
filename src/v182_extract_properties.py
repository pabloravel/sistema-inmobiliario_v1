import json
import re
import os
import math
from modelo_banos import predecir_banos_desde_modelo  # ✅ Corregido aquí

# Definición de campos esperados
ALL_FIELDS = [
    'ID', 'Titulo', 'Descripcion', 'Tipo_de_operacion', 'Tipo_propiedad',
    'Precio_raw', 'Precio_normalizado', 'Superficie_m2', 'Construccion_m2',
    'Recamaras', 'Baños', 'Medio_bano', 'Estacionamientos', 'Niveles',
    'Edad', 'Antigüedad', 'Mantenimiento', 'Amueblado', 'Mascotas',
    'Cocina_integral', 'Cocina_equipada', 'Bodega', 'Terraza', 'Jardin',
    'Cuarto_de_servicio', 'Cuarto_de_lavado', 'Vigilancia', 'Condominio',
    'Roof_garden', 'Alberca', 'Balcon', 'Elevador', 'Estado', 'Ciudad',
    'Colonia', 'CP', 'Calle', 'Ubicacion_textual', 'Latitud', 'Longitud',
    'URL', 'Fuente', 'Completeness_score'
]

# Rutas de entrada y salida
INPUT_PATH = "resultados/repositorio_propiedades.json"
OUTPUT_VALID = "resultados/propiedades_validas_v182.json"
OUTPUT_INVALID = "resultados/propiedades_invalidas_v182.json"
OUTPUT_LOG = "resultados/logs_v182.json"
OUTPUT_STATS = "resultados/stats_completitud_v182.json"

# Funciones auxiliares
def normalizar_precio(texto):
    texto = texto.lower().replace(",", "").strip()
    match = re.search(r'(\$|mxn|\bmx\$)?\s*([\d\.]+)\s*(k|m|mm|mil|millones)?', texto)
    if not match:
        return None
    cantidad = float(match.group(2))
    unidad = match.group(3)
    if unidad in ['k', 'mil']:
        return int(cantidad * 1_000)
    elif unidad in ['m', 'mm', 'millones']:
        return int(cantidad * 1_000_000)
    return int(cantidad)

def extraer_superficie(texto):
    patrones = [r'(\d{2,4})\s*(m2|m²|mt2|metros)', r'(\d+)\s*x\s*(\d+)\s*(m)?']
    for patron in patrones:
        match = re.search(patron, texto, flags=re.IGNORECASE)
        if match:
            if 'x' in patron:
                ancho, largo = float(match.group(1)), float(match.group(2))
                return round(ancho * largo, 1)
            return int(match.group(1))
    return None

def extraer_valor(texto, patrones):
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

def parse_banos(texto):
    compuesto = re.findall(r'(\d+)\s*(baños|baño)(\s*y\s*(medio|1/2))?', texto, re.IGNORECASE)
    completos, medios = 0, 0
    for grupo in compuesto:
        completos += int(grupo[0])
        if grupo[2]:
            medios += 1
    medios += len(re.findall(r'baño\s*medio|medio\s*baño|1/2\s*baño', texto, re.IGNORECASE))
    return completos, medios

def score_completitud(prop):
    campos_completos = sum(1 for campo in ALL_FIELDS if prop.get(campo))
    return round(campos_completos / len(ALL_FIELDS), 2)

# Cargar datos
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    propiedades = json.load(f)

propiedades_validas = []
propiedades_invalidas = []
log = []
stats = []

for prop in propiedades:
    descripcion = prop.get("Descripcion", "") or ""
    titulo = prop.get("Titulo", "") or ""
    texto = f"{titulo} {descripcion}".lower()

    heuristicas = {}

    # Precio
    precio_raw = prop.get("Precio_raw", "")
    precio_normalizado = normalizar_precio(precio_raw)
    prop["Precio_normalizado"] = precio_normalizado
    heuristicas["precio_normalizado"] = bool(precio_normalizado)

    # Tipo de operación
    if "venta" in texto or "se vende" in texto:
        prop["Tipo_de_operacion"] = "Venta"
    elif "renta" in texto or "al mes" in texto or "mensual" in texto:
        prop["Tipo_de_operacion"] = "Renta"
    heuristicas["tipo_operacion"] = prop.get("Tipo_de_operacion") is not None

    # Superficie
    superficie = extraer_superficie(texto)
    if not prop.get("Superficie_m2") and superficie:
        prop["Superficie_m2"] = superficie
    heuristicas["superficie"] = superficie is not None

    # Construcción
    construccion = extraer_superficie(texto)
    if not prop.get("Construccion_m2") and construccion:
        prop["Construccion_m2"] = construccion
    heuristicas["construccion"] = construccion is not None

    # Recámaras
    recs = extraer_valor(texto, [r'(\d+)\s*rec[aá]maras?', r'(\d+)\s*habs?', r'(\d+)\s*dormitorios?'])
    if not prop.get("Recamaras") and recs:
        prop["Recamaras"] = recs
    heuristicas["recamaras"] = recs is not None

    # Baños y medio baño
    if not prop.get("Baños"):
        baños, medios = parse_banos(texto)
        prop["Baños"] = baños
        prop["Medio_bano"] = medios
    heuristicas["baños"] = prop.get("Baños") is not None

    # Niveles
    niveles = extraer_valor(texto, [r'(\d+)\s*niveles?', r'(\d+)\s*pisos?'])
    if not prop.get("Niveles") and niveles:
        prop["Niveles"] = niveles
    heuristicas["niveles"] = niveles is not None

    # Estacionamientos
    estacion = extraer_valor(texto, [r'(\d+)\s*autos?', r'(\d+)\s*cocheras?', r'(\d+)\s*estacionamientos?'])
    if not prop.get("Estacionamientos") and estacion:
        prop["Estacionamientos"] = estacion
    heuristicas["estacionamientos"] = estacion is not None

    # Inferencia con modelo externo
    if not prop.get("Baños"):
        pred = predecir_banos_desde_modelo(descripcion)
        if pred is not None:
            prop["Baños"] = pred
            heuristicas["modelo_banos"] = True

    # Completeness score
    prop["Completeness_score"] = score_completitud(prop)

    # Evaluación sospechosa
    score_sospecha = 0
    if prop.get("Precio_normalizado") is None: score_sospecha += 1
    if prop.get("Tipo_de_operacion") is None: score_sospecha += 1
    if prop.get("Baños") is None and prop.get("Recamaras") is None: score_sospecha += 1

    if score_sospecha >= 2:
        prop["Descripcion"] = descripcion  # asegurar inclusión
        propiedades_invalidas.append(prop)
        log.append({"ID": prop.get("ID"), "motivo": "score_sospecha", "score": score_sospecha})
    else:
        propiedades_validas.append(prop)

    stats.append({
        "ID": prop.get("ID"),
        "Completeness_score": prop["Completeness_score"],
        "Heuristicas": heuristicas
    })

# Guardar resultados
with open(OUTPUT_VALID, "w", encoding="utf-8") as f:
    json.dump(propiedades_validas, f, indent=2, ensure_ascii=False)

with open(OUTPUT_INVALID, "w", encoding="utf-8") as f:
    json.dump(propiedades_invalidas, f, indent=2, ensure_ascii=False)

with open(OUTPUT_LOG, "w", encoding="utf-8") as f:
    json.dump(log, f, indent=2, ensure_ascii=False)

with open(OUTPUT_STATS, "w", encoding="utf-8") as f:
    json.dump(stats, f, indent=2, ensure_ascii=False)

print(f"Exportados: {len(propiedades_validas)} válidas, {len(propiedades_invalidas)} inválidas")
