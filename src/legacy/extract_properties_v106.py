# extract_properties_v106.py
# v106: mejoras 10x en dimensiones, precios, baños, niveles, ubicación, propiedad, estacionamiento y métricas

import json
import re
import unicodedata
from tqdm import tqdm
from collections import defaultdict

REPO_FILE = "resultados/repositorio_propiedades.json"
VALID_OUT = "resultados/results_v106_all.json"
INVALID_OUT = "resultados/results_v106_invalid.json"
MISSING_BY_FIELD = "resultados/results_v106_missing_by_field.json"

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
    return ''.join(c for c in unicodedata.normalize('NFD', str(txt).lower()) if unicodedata.category(c) != 'Mn')

def texto_a_num(token):
    return NUM_TXT.get(token.strip().lower())

def get_descripcion(entry):
    return str(entry.get("description") or entry.get("descripcion_raw") or "").strip()

def parse_precio(text, raw):
    text = normalize(text)
    raw = normalize(raw)
    if any(x in text for x in ["a tratar", "negociable", "por definir"]): return None
    if re.search(r"por\s+m2|unitario|precio\s+por\s+m2", text): return None
    patterns = [
        r"\$?\s?([\d,.]+)\s*(m{1,2}|k)?\s*(mxn|pesos|mx)?",
        r"(\d{1,3}(?:[.,]\d{3}){1,2})"
    ]
    for pat in patterns:
        for match in re.findall(pat, text):
            num, mult, _ = match if isinstance(match, tuple) else (match, '', '')
            try:
                val = float(num.replace(',', '').replace('.', '', num.count('.') - 1))
                if 'k' in mult: val *= 1_000
                elif 'm' in mult: val *= 1_000_000
                if 1 < val < 100_000_000:
                    return val
            except: continue
    try:
        fallback = float(re.sub(r"[^\d.]", "", raw.replace(",", ".")))
        return fallback if fallback > 0 else None
    except:
        return None

def extract_from_text(text):
    text = normalize(text)
    out = {}

    if "cesion de derechos" in text:
        out["Tipo_de_operacion"] = "Cesion"
        out["Cesion_derechos"] = True
    elif "renta" in text and any(w in text for w in ["al mes", "mensual", "por mes"]):
        out["Tipo_de_operacion"] = "Renta"
    elif any(w in text for w in ["venta", "liquido", "oferta"]):
        out["Tipo_de_operacion"] = "Venta"

    tipos = ["ph", "departamento", "casa", "terreno", "bodega", "local", "residencial", "duplex"]
    for tipo in tipos:
        if tipo in text:
            out["Tipo_propiedad"] = tipo.title()
            break

    if "cuernavaca" in text:
        out["Ciudad"] = "Cuernavaca"
        out["Estado"] = "Morelos"
    if "bellavista" in text:
        out["Colonia"] = "Bellavista"

    comp = {
        "Recamaras": r"(\d+|\w+)\s*(recamaras?|habitaciones?|cuartos)",
        "Baños": r"(\d+|\w+)\s*(baños?|bano|toilette|wc|medios?)",
        "Niveles": r"(\d+|\w+)\s*(niveles|plantas|pisos)",
        "Estacionamientos": r"(\d+|\w+)\s*(cocheras?|autos?|vehiculos|estacionamientos?)"
    }

    for campo, pat in comp.items():
        total = 0
        for val, _ in re.findall(pat, text):
            val = re.sub(r"[^\d.]", "", val)
            if val.isdigit():
                total += int(val)
            elif texto_a_num(val):
                total += texto_a_num(val)
        if total:
            out[campo] = total

    if any(x in text for x in ["una planta", "planta baja"]):
        out["Niveles"] = 1

    for match in re.findall(r"(\d{2,3})\s*[x×X]\s*(\d{2,3})", text):
        try:
            a, b = map(int, match)
            if "Superficie_m2" not in out:
                out["Superficie_m2"] = a * b
        except: pass

    for pat in [r"(\d+[.,]?\d*)\s*(m2|m²|mt2|mts2)\s*(techado|construido|cubiertos?)"]:
        for m in re.findall(pat, text):
            try:
                val = float(m[0].replace(",", "."))
                if not out.get("Construccion_m2"):
                    out["Construccion_m2"] = val
            except: continue

    return out

def completar(d):
    for f in ALL_FIELDS:
        d.setdefault(f, None)
    return d

def main():
    with open(REPO_FILE, encoding="utf-8") as f:
        base = json.load(f)

    results, excluidos, faltantes = {}, {}, defaultdict(list)

    for k, v in tqdm(base.items(), desc="Procesando v106"):
        if not k or k == "None": continue
        texto = get_descripcion(v)
        if texto.strip() == "" or any(p in normalize(texto) for p in ["moto", "bicicleta", "juguete", "reloj"]):
            excluidos[k] = completar({"Id": k, "Descripcion": texto, "Flag_no_propiedad": True})
            continue

        d = extract_from_text(texto)
        d["Id"] = k
        d["Descripcion"] = texto
        raw = str(v.get("precio", "")).strip()
        d["Precio"] = raw
        d["Precio_raw"] = raw
        d["Precio_normalizado"] = parse_precio(texto, raw)

        if not d.get("Tipo_de_operacion") and d.get("Precio_normalizado"):
            d["Tipo_de_operacion"] = "Renta" if d["Precio_normalizado"] < 30000 else "Venta"

        if d.get("Construccion_m2") and d.get("Superficie_m2") and not d.get("Niveles"):
            ratio = d["Construccion_m2"] / d["Superficie_m2"]
            if ratio > 2:
                d["Niveles"] = round(ratio)

        salida = completar(d)
        vacios = [f for f in ALL_FIELDS if salida[f] in [None, ""] and f not in ["Warnings", "Completeness_score", "Flag_no_propiedad"]]
        salida["Warnings"] = [f"Falta_{f}" for f in vacios]
        salida["Completeness_score"] = round(len([f for f in ALL_FIELDS if salida[f]]) / len(ALL_FIELDS) * 100, 2)
        results[k] = salida

        for f in vacios[:3]:
            faltantes[f].append({"id": k, "descripcion": salida.get("Descripcion", "")[:160]})

    json.dump(results, open(VALID_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(excluidos, open(INVALID_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    json.dump(faltantes, open(MISSING_BY_FIELD, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"✅ v106 exportados: {len(results)} válidos | {len(excluidos)} excluidos")

if __name__ == "__main__":
    main()
