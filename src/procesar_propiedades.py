import json
import re
import os
import math
from modelo_banos import predecir_banos_desde_modelo  # ✅ Corregido aquí
from typing import Dict, List, Union, Optional

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

def extraer_numero(texto: str) -> Optional[Union[int, float]]:
    """Extrae números de un texto, incluyendo decimales."""
    if not texto:
        return None
    matches = re.findall(r'(\d+\.?\d*)', texto)
    return float(matches[0]) if matches else None

def extraer_moneda(precio: str) -> str:
    """Determina si el precio está en MXN basado en el símbolo $."""
    return "MXN" if "$" in str(precio) else "USD"

def extraer_tipo_operacion(descripcion: str, titulo: str) -> str:
    """Determina si es renta o venta basado en el texto."""
    texto_completo = (descripcion + " " + titulo).lower()
    if "rent" in texto_completo or "renta" in texto_completo:
        return "renta"
    elif "venta" in texto_completo or "se vende" in texto_completo:
        return "venta"
    return "No especificado"

def extraer_caracteristicas(descripcion: str, titulo: str) -> Dict:
    """Extrae características de la propiedad desde la descripción."""
    texto_completo = (descripcion + " " + titulo).lower()
    
    caracteristicas = {
        "recamaras": 0,
        "banos": 0,
        "niveles": 0,
        "es_un_nivel": False,
        "superficie_m2": 0,
        "construccion_m2": 0,
        "recamara_planta_baja": False,
        "cisterna": False,
        "apto_discapacitados": False,
        "tipo_de_condominio": "",
        "fraccionamiento": "",
        "estacionamientos": 0,
        "edad": ""
    }
    
    # Buscar recámaras - primero en el texto completo
    recamaras_total = len(re.findall(r'rec[aá]mara', texto_completo, re.IGNORECASE))
    recamaras_match = re.search(r'(\d+)\s*(?:recamara|recámaras?|rec\.?|habitacion|habitación|dormitorios?)', texto_completo)
    if recamaras_match:
        caracteristicas["recamaras"] = int(recamaras_match.group(1))
    elif recamaras_total > 0:
        caracteristicas["recamaras"] = recamaras_total
    
    # Buscar baños
    banos_completos = len(re.findall(r'baño completo', texto_completo, re.IGNORECASE))
    banos_match = re.search(r'(\d+\.?\d*)\s*(?:baños?|bano|baño)', texto_completo)
    if banos_match:
        caracteristicas["banos"] = float(banos_match.group(1))
    elif banos_completos > 0:
        caracteristicas["banos"] = float(banos_completos)
    
    # Detectar niveles
    niveles = 1  # Por defecto asumimos 1 nivel
    if any(term in texto_completo for term in ["planta alta", "segundo piso", "2do piso", "planta baja"]):
        niveles = 2
    if "3er" in texto_completo or "tercer" in texto_completo:
        niveles = 3
    
    # Buscar niveles explícitos
    niveles_match = re.search(r'(\d+)\s*(?:nivele?s?|piso?s?|planta?s?)', texto_completo)
    if niveles_match:
        niveles = int(niveles_match.group(1))
    
    caracteristicas["niveles"] = niveles
    caracteristicas["es_un_nivel"] = niveles == 1
    
    # Superficie - primero buscar superficie explícita
    superficie_patterns = [
        r'(?:superficie|terreno)(?:\s+de)?:?\s*(\d+)\s*(?:m2|metros?|mt2)',
        r'(\d+)\s*(?:m2|metros?|mt2)\s*(?:de\s*terreno|superficie)',
        r'lote\s*(?:de)?\s*(\d+)\s*(?:m2|metros?|mt2)',
        r'(\d+)\s*mt2\s*(?:de\s*terreno)?'
    ]
    
    # Primero buscar números con m2
    for pattern in superficie_patterns:
        superficie = re.search(pattern, texto_completo, re.IGNORECASE)
        if superficie:
            caracteristicas["superficie_m2"] = int(superficie.group(1))
            break
            
    # Si no se encontró superficie, buscar dimensiones (frente x fondo)
    if caracteristicas["superficie_m2"] == 0:
        dimensiones = re.search(r'(\d+)\s*(?:metros\s*)?(?:x|por)\s*(\d+)(?:\s*metros)?', texto_completo)
        if dimensiones:
            frente = int(dimensiones.group(1))
            fondo = int(dimensiones.group(2))
            caracteristicas["superficie_m2"] = frente * fondo

    # Construcción
    construccion_patterns = [
        r'(?:construcción|construidos?)(?:\s+de)?:?\s*(\d+)\s*(?:m2|metros?|mt2)',
        r'(\d+)\s*(?:m2|metros?|mt2)\s*(?:de\s*construcción|construidos?)',
        r'(\d+)\s*mt2\s*(?:de\s*construcción)'
    ]
    
    for pattern in construccion_patterns:
        construccion = re.search(pattern, texto_completo, re.IGNORECASE)
        if construccion:
            caracteristicas["construccion_m2"] = int(construccion.group(1))
            break
    
    # Características booleanas
    caracteristicas["recamara_planta_baja"] = "recámara en planta baja" in texto_completo or ("recamara" in texto_completo and "planta baja" in texto_completo)
    caracteristicas["cisterna"] = any(term in texto_completo for term in ["cisterna", "aljibe"])
    caracteristicas["apto_discapacitados"] = "discapacitados" in texto_completo
    
    # Tipo de condominio
    if "condominio" in texto_completo:
        tipo_condominio = re.search(r'(?:condominio\s+)(\w+)', texto_completo)
        if tipo_condominio:
            caracteristicas["tipo_de_condominio"] = tipo_condominio.group(1)
    
    # Estacionamientos - buscar diferentes patrones
    estacionamiento_patterns = [
        r'estacionamiento\s*(?:para)?\s*(\d+)\s*(?:auto|carro|coche|vehículo)',
        r'(\d+)\s*(?:lugar|espacio|cajón|cajon)(?:\s+de\s+estacionamiento)?',
        r'(\d+)\s*estacionamiento'
    ]
    
    for pattern in estacionamiento_patterns:
        estacionamiento = re.search(pattern, texto_completo, re.IGNORECASE)
        if estacionamiento:
            caracteristicas["estacionamientos"] = int(estacionamiento.group(1))
            break
    
    # Edad
    if "nueva" in texto_completo or "nuevo" in texto_completo or "estrenar" in texto_completo:
        caracteristicas["edad"] = "nuevo"
    elif "años" in texto_completo:
        edad = re.search(r'(\d+)\s*años', texto_completo)
        if edad:
            caracteristicas["edad"] = f"{edad.group(1)} años"
    
    return caracteristicas

def extraer_amenidades(descripcion: str) -> Dict:
    """Extrae amenidades de la propiedad desde la descripción."""
    descripcion = descripcion.lower()
    
    return {
        "seguridad": any(word in descripcion for word in ["seguridad", "vigilancia", "privada"]),
        "alberca": any(word in descripcion for word in ["alberca", "piscina"]),
        "patio": "patio" in descripcion,
        "bodega": "bodega" in descripcion,
        "terraza": "terraza" in descripcion,
        "jardin": any(word in descripcion for word in ["jardin", "jardín"]),
        "estudio": "estudio" in descripcion,
        "roof_garden": any(word in descripcion for word in ["roof garden", "roofgarden", "roof-garden"])
    }

def extraer_legal(descripcion: str) -> Dict:
    """Extrae información legal desde la descripción."""
    descripcion = descripcion.lower()
    
    formas_pago = []
    if "contado" in descripcion:
        formas_pago.append("contado")
    if "credito" in descripcion or "crédito" in descripcion:
        formas_pago.append("crédito")
    if "infonavit" in descripcion:
        formas_pago.append("infonavit")
    
    return {
        "escrituras": "escrituras" in descripcion,
        "cesion_derechos": "cesión de derechos" in descripcion or "cesion de derechos" in descripcion,
        "formas_de_pago": formas_pago
    }

def extraer_ubicacion(descripcion: str, location: str, ciudad: str) -> Dict:
    """Extrae información de ubicación desde la descripción."""
    ubicacion = {
        "colonia": "",
        "calle": "",
        "estado": "Morelos",  # Por defecto
        "ciudad": ciudad.title() if ciudad else ""
    }
    
    texto_completo = (descripcion + " " + location).lower()
    
    # Buscar colonia
    colonias_pattern = r'(?:col(?:onia)?\.?\s+)([^,\.]+)'
    colonia_match = re.search(colonias_pattern, texto_completo)
    if colonia_match:
        ubicacion["colonia"] = colonia_match.group(1).strip().title()
    
    # Buscar calle
    calle = re.search(r'(?:calle|av\.|avenida)\s+([^,\.]+)', texto_completo)
    if calle:
        ubicacion["calle"] = calle.group(1).strip().title()
    
    return ubicacion

def procesar_propiedad(id_prop: str, datos: Dict) -> Dict:
    """Procesa una propiedad individual y retorna la información estructurada."""
    if not isinstance(datos, dict):
        return None
    
    descripcion = str(datos.get("description", ""))
    titulo = str(datos.get("titulo", ""))
    precio = datos.get("precio", "")
    location = str(datos.get("location", ""))
    ciudad = str(datos.get("ciudad", ""))
    link = str(datos.get("link", ""))
    
    # Determinar tipo de propiedad
    texto_completo = (descripcion + " " + titulo).lower()
    tipos_propiedad = {
        "casa sola": ["casa sola", "casa individual"],
        "casa en condominio": ["casa en condominio"],
        "casa en privada": ["casa en privada"],
        "departamento": ["departamento", "depto"],
        "terreno": ["terreno", "lote"],
        "oficina": ["oficina"],
        "local": ["local comercial", "local"],
        "bodega": ["bodega"],
        "villa": ["villa"],
        "hotel": ["hotel"]
    }
    
    tipo_propiedad = "No especificado"
    for tipo, keywords in tipos_propiedad.items():
        if any(keyword in texto_completo for keyword in keywords):
            tipo_propiedad = tipo
            break
    
    # Si no se encontró un tipo específico pero contiene "casa"
    if tipo_propiedad == "No especificado" and "casa" in texto_completo:
        tipo_propiedad = "casa sola"
    
    return {
        "id": id_prop,
        "link": link,
        "descripcion_original": descripcion,
        "ubicacion": extraer_ubicacion(descripcion, location, ciudad),
        "propiedad": {
            "tipo_propiedad": tipo_propiedad,
            "precio": precio,
            "tipo_operacion": extraer_tipo_operacion(descripcion, titulo),
            "moneda": extraer_moneda(precio)
        },
        "descripcion": {
            "caracteristicas": extraer_caracteristicas(descripcion, titulo),
            "amenidades": extraer_amenidades(descripcion),
            "legal": extraer_legal(descripcion)
        }
    }

def procesar_archivo():
    """Procesa el archivo de propiedades completo."""
    try:
        # Leer el archivo original
        with open('resultados/repositorio_propiedades.json', 'r', encoding='utf-8') as f:
            contenido = f.read()
            propiedades_dict = json.loads(contenido)
        
        # Procesar cada propiedad
        propiedades_procesadas = []
        for id_prop, datos in propiedades_dict.items():
            if id_prop != "None":  # Ignorar la entrada None
                resultado = procesar_propiedad(id_prop, datos)
                if resultado:
                    propiedades_procesadas.append(resultado)
        
        resultado_final = {
            "propiedades": propiedades_procesadas
        }
        
        # Guardar el resultado
        with open('resultados/propiedades_estructuradas.json', 'w', encoding='utf-8') as f:
            json.dump(resultado_final, f, ensure_ascii=False, indent=2)
        
        print("Procesamiento completado con éxito.")
        print(f"Se procesaron {len(propiedades_procesadas)} propiedades.")
        
    except Exception as e:
        print(f"Error durante el procesamiento: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    procesar_archivo()
