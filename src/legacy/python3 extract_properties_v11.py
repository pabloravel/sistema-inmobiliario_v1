import json
import re

def extraer_propiedad_v11(id_, item):
    """
    Extrae los campos según Prompt Oficial V11:
    - Toda la información proviene de item['description'] excepto 'precio'.
    """
    desc = item.get("description", "") or item.get("descripcion_raw", "")
    desc_lower = desc.lower()
    
    precio = item.get("price") or item.get("precio") or None
    
    def buscar(pat, group=1):
        m = re.search(pat, desc, flags=re.IGNORECASE)
        return m.group(group).strip() if m else None

    colonia = buscar(r"\\bcol(?:\\.|onia)?\\s+([A-Za-zÁÉÍÓÚñáéíóú\\s]+)")
    ubicacion = buscar(
        r"(sobre avenida\\s+[A-Za-z0-9\\s]+|avenida\\s+[A-Za-z0-9\\s]+|calle\\s+[A-Za-z0-9\\s]+|junto a\\s+[A-Za-z0-9\\s]+"
        r"|a \\d+ minutos de\\s+[A-Za-z0-9\\s]+|frente a\\s+[A-Za-z0-9\\s]+|cerca de\\s+[A-Za-z0-9\\s]+"
        r"|detrás de\\s+[A-Za-z0-9\\s]+|en esquina con\\s+[A-Za-z0-9\\s]+)"
    )

    ciudad = buscar(r"\\b(?:en\\s+)?(cuernavaca|jiutepec|temixco|emiliano zapata)\\b")
    ciudad = ciudad.title() if ciudad else None
    estado = "Morelos" if ciudad and ciudad.lower() in ["cuernavaca","jiutepec","temixco","emiliano zapata"] else None

    tipo_propiedad = buscar(
        r"\\b(Casa en condominio|Casa en privada|Casa sola|Departamento|Terreno|Oficina|Local|Bodega|PH|Cuarto|Villa|Hotel|Cabañ[ae]s?|Townhouse|Monoambiente)\\b"
    )

    tipo_operacion = buscar(r"\\b(Venta|Renta)\\b") or item.get("tipo_operacion", "Desconocido")
    moneda = "MXN" if precio and ("$" in precio or "pesos" in desc_lower) else ("USD" if "usd" in desc_lower or "dólares" in desc_lower else None)

    def to_int(x): return int(x) if x and x.isdigit() else None
    def to_float(x): return float(x.replace(",","")) if x else None

    recamaras = to_int(buscar(r"(\\d+)\\s*(?:recámaras|recamaras|habitaciones|cuartos)"))
    banos = to_float(buscar(r"(\\d+(?:\\.\\d+)?)\\s*(?:baños|banos)"))
    niveles = to_int(buscar(r"(\\d+)\\s*(?:pisos|plantas|niveles)"))
    es_de_un_nivel = True if re.search(r"una sola planta|todo en planta baja", desc_lower) else None
    superficie_m2 = to_float(buscar(r"(\\d+(?:\\.\\d+)?)\\s*(?:m2 de terreno|m² de terreno|superficie)"))
    construccion_m2 = to_float(buscar(r"(\\d+(?:\\.\\d+)?)\\s*(?:m2 construidos|metros construidos|construcción de)"))
    recamara_en_pb = True if re.search(r"planta baja.*recámara|en pb.*recámara", desc_lower) else None
    cisterna = True if "cisterna" in desc_lower or "tinaco" in desc_lower else None
    apto_discapacitados = True if any(x in desc_lower for x in ["movilidad reducida", "silla de ruedas", "acceso para discapacitados"]) else None
    tipo_de_condominio = buscar(r"\\b(condominio|privada|conjunto|coto)\\b")
    fraccionamiento = buscar(r"fracc\\.?\\s*([A-Za-zÁÉÍÓÚñáéíóú\\s]+)") or buscar(r"residencial\\s+([A-Za-zÁÉÍÓÚñáéíóú\\s]+)")
    estacionamientos = to_int(buscar(r"(\\d+)\\s*(?:cochera para|garage para|espacios para)\\s*\\d*"))
    edad = "Nuevo" if re.search(r"\\bnuevo\\b|\\bestrena\\b", desc_lower) else buscar(r"(\\d+)\\s*años")

    def flag(words): return True if any(w in desc_lower for w in words) else None
    seguridad = flag(["seguridad", "vigilancia", "acceso controlado"])
    alberca = flag(["alberca", "piscina"])
    patio = flag(["patio"])
    bodega = flag(["bodega"])
    terraza = flag(["terraza", "roof garden", "roofgarden"])
    jardin = flag(["jardín", "jardin"])
    estudio = flag(["estudio", "oficina", "sala de tv"])
    roof_garden = terraza

    escrituras = flag(["escriturado", "documentación en regla"]) or flag(["infonavit","fovissste","hipotecario","bancario"])
    cesion_derechos = flag(["cesión de derechos", "solo recurso propio", "no acepta créditos"])
    formas_de_pago = [term for term in ["Infonavit","Fovissste","Crédito bancario","Contado","Recurso propio","CFE","ISSFAM","IMSS","Pemex"]
                      if term.lower() in desc_lower]
    formas_de_pago = formas_de_pago if formas_de_pago else None

    return {
        "id": id_,
        "descripcion": desc,
        "colonia": colonia,
        "ubicacion": ubicacion,
        "estado": estado,
        "ciudad": ciudad,
        "tipo_propiedad": tipo_propiedad,
        "precio": precio,
        "tipo_operacion": tipo_operacion,
        "moneda": moneda,
        "recamaras": recamaras,
        "baños": banos,
        "niveles": niveles,
        "es_de_un_nivel": es_de_un_nivel,
        "superficie_m2": superficie_m2,
        "construccion_m2": construccion_m2,
        "recamara_en_pb": recamara_en_pb,
        "cisterna": cisterna,
        "apto_discapacitados": apto_discapacitados,
        "tipo_de_condominio": tipo_de_condominio,
        "fraccionamiento": fraccionamiento,
        "estacionamientos": estacionamientos,
        "edad": edad,
        "seguridad": seguridad,
        "alberca": alberca,
        "patio": patio,
        "bodega": bodega,
        "terraza": terraza,
        "jardin": jardin,
        "estudio": estudio,
        "roof_garden": roof_garden,
        "escrituras": escrituras,
        "cesion_derechos": cesion_derechos,
        "formas_de_pago": formas_de_pago
    }

if __name__ == "__main__":
    # Cargar el JSON de propiedades
    with open("repositorio_propiedades.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Procesar y guardar las primeras 50
    primeras_50 = list(data.items())[:50]
    resultados = [extraer_propiedad_v11(id_, item) for id_, item in primeras_50]

    with open("resultados_estructurados_v11_0_50.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)

    print("Archivo generado: resultados_estructurados_v11_0_50.json")
 ​:contentReference[oaicite:0]{index=0}​
