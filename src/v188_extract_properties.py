import json
import re

# --------------------------------------------
# Función simple en lugar del modelo real
def predecir_banos(texto):
    texto = texto.lower()
    completos = len(re.findall(r"\bbañ[oa]s?\b|\bcompleto[s]?\b", texto))
    medios = len(re.findall(r"medio[s]?\s+bañ[oa]", texto))
    return completos, medios
# --------------------------------------------

ALL_FIELDS = [
    "Descripcion", "Precio", "Precio_normalizado", "Tipo_de_operacion", "Tipo_propiedad",
    "Superficie_m2", "Construccion_m2", "Recamaras", "Banios", "Medio_banio",
    "Estacionamientos", "Niveles", "Colonia", "Ciudad", "Estado",
    "CP", "Antiguedad", "Amenidades", "Mantenimiento", "Amueblado",
    "Mascotas", "Uso_de_suelo", "Metros_frente", "Metros_fondo",
    "Terreno_irregular", "Elevador", "Cuarto_servicio", "Bodega", "Balcon",
    "Cisterna", "Condominio", "Roof_garden", "Vigilancia", "Zona_comercial",
    "Agua", "Luz", "Gas", "Alberca", "Jardin", "Sotano", "Duplex", "Penthouse"
]

regex_precio = r"(?:\$|MXN|mnx|MX\$)?\s?([\d.,]+)\s?(millones?|millón|mil|k|M|MM)?"
regex_superficie = r"(\d{1,4})\s?(?:m2|mts2|m²|metros|metros cuadrados)"
regex_construccion = r"(?:construcci[oó]n|construida)\s+de\s+(\d+)\s?(?:m2|mts2|m²)?"
regex_recamaras = r"(\d+)\s?(?:rec[aá]maras?|cuartos|habitaciones)"
regex_estacionamientos = r"(\d+)\s?(?:cajones|autos|estacionamientos?)"
regex_niveles = r"(\d+)\s?(?:pisos|niveles|plantas)"

def normalizar_precio(texto):
    texto = texto.lower()
    match = re.search(regex_precio, texto)
    if match:
        numero, unidad = match.groups()
        try:
            numero = float(numero.replace(',', '').replace('.', '')) if ',' in numero and '.' in numero else float(numero.replace(',', '').replace('.', '', 1))
        except:
            return None
        if unidad in ['millon', 'millones', 'mm', 'm']:
            return int(numero * 1_000_000)
        if unidad in ['mil', 'k']:
            return int(numero * 1_000)
        return int(numero)
    return None

def inferir_tipo_operacion(desc):
    desc = desc.lower()
    if re.search(r"\b(renta|rent|mensual|al mes|se renta|arriendo|arrendamiento)\b", desc):
        return "Renta"
    if re.search(r"\b(venta|se vende|en venta|adquiere)\b", desc):
        return "Venta"
    if re.search(r"\$[\d,\.]+\s?(al mes|mensuales)", desc):
        return "Renta"
    return ""

def extraer_campos(prop):
    descripcion = prop.get("Descripcion", "")
    campos = {campo: "" for campo in ALL_FIELDS}
    campos["Descripcion"] = descripcion
    campos["Precio"] = prop.get("Precio", "")

    campos["Precio_normalizado"] = normalizar_precio(descripcion)
    campos["Tipo_de_operacion"] = inferir_tipo_operacion(descripcion)

    if match := re.search(regex_superficie, descripcion.lower()):
        campos["Superficie_m2"] = int(match.group(1))
    if match := re.search(regex_construccion, descripcion.lower()):
        campos["Construccion_m2"] = int(match.group(1))
    if match := re.search(regex_recamaras, descripcion.lower()):
        campos["Recamaras"] = int(match.group(1))
    if match := re.search(regex_estacionamientos, descripcion.lower()):
        campos["Estacionamientos"] = int(match.group(1))
    if match := re.search(regex_niveles, descripcion.lower()):
        campos["Niveles"] = int(match.group(1))

    campos["Banios"], campos["Medio_banio"] = predecir_banos(descripcion)

    return campos

def calcular_score_sospecha(campos):
    score = 0
    motivos = []
    if not campos["Precio_normalizado"]:
        score += 1
        motivos.append("precio_invalido")
    if campos["Tipo_de_operacion"] == "":
        score += 1
        motivos.append("tipo_operacion_no_determinado")
    if not campos["Recamaras"]:
        score += 1
        motivos.append("recamaras_no_detectadas")
    if not campos["Banios"]:
        score += 1
        motivos.append("banios_no_detectados")
    return score, motivos

def main():
    with open("resultados/repositorio_propiedades.json", "r", encoding="utf-8") as f:
        datos = json.load(f)
        propiedades = list(datos.values()) if isinstance(datos, dict) else datos

    resultados_validos = []
    resultados_invalidos = []

    for prop in propiedades:
        if not isinstance(prop, dict):
            continue
        campos = extraer_campos(prop)
        score, motivos = calcular_score_sospecha(campos)
        campos["score_sospecha"] = score
        if score <= 2:
            resultados_validos.append(campos)
        else:
            campos["motivos_exclusion"] = motivos
            resultados_invalidos.append(campos)

    with open("resultados/resultados_completos_v188.json", "w", encoding="utf-8") as f:
        json.dump(resultados_validos, f, ensure_ascii=False, indent=2)
    with open("resultados/resultados_excluidos_v188.json", "w", encoding="utf-8") as f:
        json.dump(resultados_invalidos, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
