
# extract_properties_v113.py – versión con confianza, conteo múltiple, y métricas de cobertura

import json
import re
import unicodedata
from tqdm import tqdm
from collections import defaultdict, Counter

REPO_FILE = "resultados/repositorio_propiedades.json"
VALID_OUT = "resultados/results_v113_all.json"
INVALID_OUT = "resultados/results_v113_invalid.json"
MISSING_BY_FIELD = "resultados/results_v113_missing_by_field.json"

ALL_FIELDS = [
    "Id", "Descripcion", "Precio", "Precio_raw", "Precio_normalizado",
    "Tipo_de_operacion", "Tipo_propiedad", "Recamaras", "Baños", "Niveles",
    "Estacionamientos", "Superficie_m2", "Construccion_m2", "Ciudad", "Estado",
    "Colonia", "Ubicacion", "Alberca", "Bodega", "Estudio", "Jardin", "Patio",
    "Roof_garden", "Seguridad", "Terraza", "Cocina", "Cuota_de_mantenimiento",
    "Fraccionamiento", "Apto_discapacitados", "Cisterna", "Un_nivel",
    "Recamara_en_PB", "Tipo_de_condominio", "Cesion_derechos", "Escrituras",
    "Formas_de_pago", "Warnings", "Completeness_score", "Flag_no_propiedad",
    "Motivo_exclusion"
]

NUM_TXT = {
    "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "medio": 0.5, "y medio": 0.5
}

def normalize(txt):
    return ''.join(c for c in unicodedata.normalize('NFD', str(txt).lower())
                   if unicodedata.category(c) != 'Mn')

def texto_a_num(token):
    return NUM_TXT.get(token.strip().lower())

def get_descripcion(entry):
    return str(entry.get("description") or entry.get("descripcion_raw") or "").strip()

def parse_valor_multiple(text, patrones):
    total = 0
    for pat in patrones:
        matches = re.findall(pat, text)
        for match in matches:
            val = match[0]
            if val.isdigit():
                total += int(val)
            elif texto_a_num(val):
                total += texto_a_num(val)
    return total if total > 0 else None

def parse_precio(text, raw):
    try:
        match = re.search(r"(\d+[.,]?\d*)\s*(k|m|mm)?", text)
        if match:
            val = float(match[1].replace(",", "."))
            mult = match[2]
            if mult == "k": val *= 1_000
            elif mult in ["m", "mm"]: val *= 1_000_000
            return val if 1 < val < 100_000_000 else None
        fallback = float(re.sub(r"[^\d.]", "", raw.replace(",", ".")))
        return fallback if fallback > 0 else None
    except:
        return None

def parse_dimensiones(text):
    superficies = []
    for match in re.findall(r"(\d{2,3})\s*[x×X]\s*(\d{2,3})", text):
        try:
            a, b = map(int, match)
            superficies.append(a * b)
        except: continue
    return max(superficies) if superficies else None

def parse_construccion(text):
    for m in re.findall(r"(\d+[.,]?\d*)\s*(m2|m²|mt2|mts2)\s*(techado|construido|cubiertos?)", text):
        try: return float(m[0].replace(",", "."))
        except: continue
    return None

def parse_niveles(text, construccion, superficie):
    if "una planta" in text or "planta baja" in text:
        return 1
    elif m := re.search(r"(\d+)\s*(niveles|pisos|plantas)", text):
        return int(m.group(1))
    elif construccion and superficie and superficie > 0:
        ratio = construccion / superficie
        if ratio >= 2: return round(ratio)
    return None

def parse_amenidades(text):
    amenidades = {
        "Alberca": ["alberca", "piscina"],
        "Jardin": ["jardin", "área verde"],
        "Roof_garden": ["roof", "azotea ajardinada", "roof garden"],
        "Seguridad": ["seguridad", "vigilancia", "caseta"],
        "Terraza": ["terraza"],
        "Cisterna": ["cisterna"],
        "Bodega": ["bodega"],
        "Estudio": ["estudio"],
        "Cocina": ["cocina equipada", "cocina integral", "cocina"],
        "Patio": ["patio"],
        "Un_nivel": ["una planta", "un solo nivel"],
        "Recamara_en_PB": ["recamara en planta baja"]
    }
    out = {}
    for campo, sinonimos in amenidades.items():
        out[campo] = any(s in text for s in sinonimos)
    return out

def parse_legalidad(text):
    return {
        "Escrituras": any(k in text for k in ["escritura", "escriturado", "escrituras"]),
        "Cesion_derechos": "cesion de derechos" in text,
        "Formas_de_pago": "infonavit" if "infonavit" in text else ("contado" if "contado" in text else None)
    }

def parse_fraccionamiento(text):
    return {
        "Fraccionamiento": any(k in text for k in ["fraccionamiento", "privada cerrada"]),
        "Tipo_de_condominio": "condominio" if "condominio" in text else None
    }

def parse_ubicacion(text):
    ubicacion = {}
    if "cuernavaca" in text:
        ubicacion["Ciudad"] = "Cuernavaca"
        ubicacion["Estado"] = "Morelos"
    if "bellavista" in text:
        ubicacion["Colonia"] = "Bellavista"
    return ubicacion

def extract_fields(text, raw):
    text = normalize(text)
    out = {}

    out["Precio_normalizado"] = parse_precio(text, raw)
    out["Baños"] = parse_valor_multiple(text, [r"(\d+|\w+)\s*(baños?|toilette|wc|medio)"])
    out["Recamaras"] = parse_valor_multiple(text, [r"(\d+|\w+)\s*(recamaras?|habitaciones?|cuartos)"])
    out["Estacionamientos"] = parse_valor_multiple(text, [r"(\d+|\w+)\s*(autos?|vehiculos|cocheras?)"])
    out["Superficie_m2"] = parse_dimensiones(text)
    out["Construccion_m2"] = parse_construccion(text)
    out["Niveles"] = parse_niveles(text, out.get("Construccion_m2"), out.get("Superficie_m2"))

    out.update(parse_ubicacion(text))
    out.update(parse_amenidades(text))
    out.update(parse_legalidad(text))
    out.update(parse_fraccionamiento(text))

    if "renta" in text and "venta" not in text:
        out["Tipo_de_operacion"] = "Renta"
    elif "venta" in text:
        out["Tipo_de_operacion"] = "Venta"
    elif out.get("Precio_normalizado") is not None:
        out["Tipo_de_operacion"] = "Renta" if out["Precio_normalizado"] < 30000 else "Venta"

    for tipo in ["departamento", "ph", "casa", "terreno", "bodega"]:
        if tipo in text:
            out["Tipo_propiedad"] = tipo.title()
            break

    return out

def completar(d):
    for f in ALL_FIELDS:
        d.setdefault(f, None)
    return d

def main():
    with open(REPO_FILE, encoding="utf-8") as f:
        base = json.load(f)

    results, excluidos, faltantes = {}, {}, defaultdict(list)
    field_counter = Counter()

    for k, v in tqdm(base.items(), desc="Procesando v113"):
        if not k or k == "None": continue
        texto = get_descripcion(v)
        if texto.strip() == "":
            excluidos[k] = completar({"Id": k, "Descripcion": texto, "Flag_no_propiedad": True, "Motivo_exclusion": "Descripcion vacía"})
            continue
        if any(p in normalize(texto) for p in ["moto", "bicicleta", "juguete"]):
            excluidos[k] = completar({"Id": k, "Descripcion": texto, "Flag_no_propiedad": True, "Motivo_exclusion": "Contiene término no inmobiliario"})
            continue

        raw = str(v.get("precio", "")).strip()
        campos = extract_fields(texto, raw)
        campos["Id"] = k
        campos["Descripcion"] = texto
        campos["Precio"] = raw
        campos["Precio_raw"] = raw

        salida = completar(campos)
        vacios = [f for f in ALL_FIELDS if salida[f] in [None, ""] and f not in ["Warnings", "Completeness_score", "Flag_no_propiedad", "Motivo_exclusion"]]
        salida["Warnings"] = [f"Falta_{f}" for f in vacios]
        salida["Completeness_score"] = round(len([f for f in ALL_FIELDS if salida[f]]) / len(ALL_FIELDS) * 100, 2)

        for f in ALL_FIELDS:
            if salida[f] not in [None, ""]:
                field_counter[f] += 1

        results[k] = salida

        for f in vacios[:3]:
            faltantes[f].append({"id": k, "descripcion": salida.get("Descripcion", "")[:160]})

    json.dump(results, open(VALID_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(excluidos, open(INVALID_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(faltantes, open(MISSING_BY_FIELD, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    total = len(results)
    print(f"✅ v113 exportados: {total} válidos | {len(excluidos)} excluidos")
    print("\n🔎 Porcentaje de cobertura por campo:")
    for campo in ALL_FIELDS:
        if campo not in ["Warnings", "Completeness_score", "Flag_no_propiedad", "Motivo_exclusion"]:
            porcentaje = field_counter[campo] / total * 100 if total else 0
            print(f"- {campo:25}: {porcentaje:.2f}%")

if __name__ == "__main__":
    main()
