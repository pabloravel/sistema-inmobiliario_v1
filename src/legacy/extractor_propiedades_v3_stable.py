import json
import re
from typing import Dict, List, Union, Optional, Tuple

def normalizar_precio(texto: str) -> Tuple[float, str]:
    """
    Extrae y normaliza el precio y la moneda desde el texto.
    Retorna una tupla de (precio_normalizado, moneda)
    """
    texto = texto.lower().strip()
    
    # Primero limpiar el texto de precio
    texto = texto.replace("$", "").replace("mxn", "").replace("mx", "").replace("usd", "")
    texto = texto.replace(" ", "").replace(",", "")
    
    # Patrones de precio mejorados
    patrones = [
        r'(\d+(?:\.\d{3})*(?:\.\d{2})?)',  # Maneja números con puntos como separadores de miles
        r'(\d+)(?:k|mil)',  # Para precios en miles
        r'(\d+)(?:m|mm|millones?)'  # Para precios en millones
    ]
    
    for patron in patrones:
        if match := re.search(patron, texto):
            try:
                cantidad_str = match.group(1)
                # Si tiene más de un punto, el último es decimal
                if cantidad_str.count('.') > 1:
                    partes = cantidad_str.split('.')
                    cantidad_str = ''.join(partes[:-1]) + '.' + partes[-1]
                
                cantidad = float(cantidad_str)
                
                # Aplicar multiplicador según el patrón
                if 'k' in texto or 'mil' in texto:
                    cantidad *= 1_000
                elif any(m in texto for m in ['m', 'mm', 'millones', 'millón']):
                    cantidad *= 1_000_000
                
                return int(cantidad), 'MXN'
            except ValueError:
                continue
    
    return 0, 'MXN'

def extraer_tipo_operacion(texto: str) -> str:
    """
    Extrae el tipo de operación (venta/renta) del texto.
    Mejorado para detectar más patrones.
    """
    texto = texto.lower()
    
    indicadores_venta = [
        r'\bventa\b', r'\bvendo\b', r'\bse vende\b', r'\ben venta\b',
        r'\bcompra\b', r'\badquiere\b', r'\bprecio de venta\b'
    ]
    
    indicadores_renta = [
        r'\brenta\b', r'\bse renta\b', r'\ben renta\b', r'\barrendamiento\b',
        r'\barriendo\b', r'\brentar?\b', r'\bprecio de renta\b',
        r'\bmensual\b', r'\bal mes\b', r'\bpor mes\b'
    ]
    
    for patron in indicadores_venta:
        if re.search(patron, texto):
            return "venta"
            
    for patron in indicadores_renta:
        if re.search(patron, texto):
            return "renta"
    
    # Si hay un precio mensual, es renta
    if re.search(r'\$[\d,\.]+\s*(?:al mes|mensuales?|por mes)', texto):
        return "renta"
        
    return "No especificado"

def extraer_tipo_propiedad(texto: str) -> str:
    """
    Extrae el tipo de propiedad con reglas mejoradas.
    """
    texto = texto.lower()
    
    # Mapeo mejorado de tipos de propiedad
    tipos = {
        "casa": [
            (r'\bcasa\b(?!\s*(?:club|muestra|tipo))', [
                (r'\bcasa\b.*\bcondominio\b', "casa en condominio"),
                (r'\bcasa\b.*\bprivada\b', "casa en privada"),
                (r'\bcasa\b.*\bfracc\b', "casa en fraccionamiento"),
                (r'\bcasa\b.*\bsola\b', "casa sola"),
                (r'\bcasa\b', "casa sola")  # default si no hay especificador
            ]),
        ],
        "departamento": [
            (r'\b(?:departamento|depto|dpto)\b', "departamento")
        ],
        "terreno": [
            (r'\b(?:terreno|lote|predio)\b', "terreno")
        ],
        "local": [
            (r'\b(?:local comercial|local)\b', "local")
        ],
        "oficina": [
            (r'\b(?:oficina|consultorio)\b', "oficina")
        ],
        "bodega": [
            (r'\b(?:bodega|nave industrial)\b', "bodega")
        ]
    }
    
    # Buscar coincidencias en orden de prioridad
    for categoria, patrones in tipos.items():
        for patron_principal, subtipos in patrones:
            if re.search(patron_principal, texto):
                if isinstance(subtipos, list):
                    for subtipo_patron, subtipo_nombre in subtipos:
                        if re.search(subtipo_patron, texto):
                            return subtipo_nombre
                    # Si no encuentra subtipos, usa el último (default)
                    return subtipos[-1][1]
                else:
                    return subtipos
    
    return "No especificado"

def extraer_superficie(texto: str) -> Dict[str, int]:
    """
    Extrae superficie total y construida con patrones mejorados.
    """
    texto = texto.lower()
    resultado = {"superficie_m2": 0, "construccion_m2": 0}
    
    # Patrones para superficie total
    superficie_patterns = [
        r'(?:superficie|terreno|lote)(?:\s+de)?:?\s*(\d+)\s*(?:m2|metros?|mt2|mts2?)',
        r'(\d+)\s*(?:m2|metros?|mt2|mts2?)\s*(?:de\s*terreno|superficie)',
        r'(\d+)\s*x\s*(\d+)\s*(?:m2|metros?)?',
        r'terreno\s+(?:de\s+)?(\d+)(?:\s*m2|\s*mts2?)?',
        r'(\d+)\s*mts?\.?\s*(?:de\s*terreno)?',
        r'(\d+)\s*m2\s*de\s*terreno',
        r'jardín\s*(?:de\s+)?(?:aproximadamente\s+)?(\d+)\s*(?:m2|metros?|mt2|mts2?)',
        r'(\d+)\s*(?:m2|metros?|mt2|mts2?)\s*(?:de\s*jardín)'
    ]
    
    # Patrones para construcción
    construccion_patterns = [
        r'(?:construcción|construidos?|edificados?)(?:\s+de)?:?\s*(\d+)\s*(?:m2|metros?|mt2|mts2?)',
        r'(\d+)\s*(?:m2|metros?|mt2|mts2?)\s*(?:de\s*construcción|construidos?)',
        r'construccion\s+(?:de\s+)?(\d+)(?:\s*m2|\s*mts2?)?',
        r'(\d+)\s*mts?\.?\s*(?:de\s*construccion)?',
        r'(\d+)\s*m2\s*de\s*construccion'
    ]
    
    # Buscar superficie
    for pattern in superficie_patterns:
        if match := re.search(pattern, texto):
            if 'x' in pattern:
                # Caso especial para dimensiones (frente x fondo)
                try:
                    resultado["superficie_m2"] = int(float(match.group(1)) * float(match.group(2)))
                except (ValueError, TypeError):
                    continue
            else:
                try:
                    valor = int(match.group(1))
                    # Validar que el valor sea razonable (entre 50 y 10000 m2)
                    if 50 <= valor <= 10000:
                        resultado["superficie_m2"] = valor
                except (ValueError, TypeError):
                    continue
            break
    
    # Buscar construcción
    for pattern in construccion_patterns:
        if match := re.search(pattern, texto):
            try:
                valor = int(match.group(1))
                # Validar que el valor sea razonable (entre 30 y 5000 m2)
                if 30 <= valor <= 5000:
                    resultado["construccion_m2"] = valor
            except (ValueError, TypeError):
                continue
            break
    
    # Si no se encontró superficie pero hay dimensiones de alberca, usar eso como referencia mínima
    if resultado["superficie_m2"] == 0:
        alberca_match = re.search(r'alberca\s+de\s+(\d+)\s*x\s*(\d+)', texto)
        if alberca_match:
            try:
                ancho = float(alberca_match.group(1))
                largo = float(alberca_match.group(2))
                # La superficie del terreno debe ser al menos 3 veces el área de la alberca
                area_minima = int(ancho * largo * 3)
                if 50 <= area_minima <= 10000:
                    resultado["superficie_m2"] = area_minima
            except (ValueError, TypeError):
                pass
    
    return resultado

def extraer_caracteristicas(texto: str) -> Dict:
    """
    Extrae características con patrones mejorados.
    """
    texto = texto.lower()
    
    caracteristicas = {
        "recamaras": 0,
        "banos": 0,
        "medio_bano": 0,
        "niveles": 1,
        "estacionamientos": 0,
        "edad": "",
        "recamara_planta_baja": False,
        "cisterna": False
    }
    
    # Recámaras
    recamaras_patterns = [
        r'(\d+)\s*(?:rec[aá]maras?|habitaciones?|dormitorios?|cuartos?)',
        r'(?:rec[aá]maras?|habitaciones?|dormitorios?)\s*:\s*(\d+)'
    ]
    
    for pattern in recamaras_patterns:
        if match := re.search(pattern, texto):
            caracteristicas["recamaras"] = int(match.group(1))
            break
    
    # Baños
    banos_completos = len(re.findall(r'baño(?:s)?\s+completo(?:s)?', texto))
    if banos_completos > 0:
        caracteristicas["banos"] = banos_completos
    else:
        if match := re.search(r'(\d+)\s*baño(?:s)?(?!\s*(?:medio|1/2))', texto):
            caracteristicas["banos"] = int(match.group(1))
    
    # Medios baños
    medios_banos = len(re.findall(r'(?:medio|1/2)\s+baño(?:s)?', texto))
    if medios_banos > 0:
        caracteristicas["medio_bano"] = medios_banos
    
    # Niveles
    if "planta alta" in texto or "segundo piso" in texto:
        caracteristicas["niveles"] = max(2, caracteristicas["niveles"])
    if match := re.search(r'(\d+)\s*(?:nivele?s?|piso?s?|plantas?)', texto):
        caracteristicas["niveles"] = int(match.group(1))
    
    # Estacionamientos
    estacionamiento_patterns = [
        r'(\d+)\s*(?:cajones?|lugares?|espacios?)\s*(?:de\s*)?estacionamiento',
        r'estacionamiento\s*(?:para)?\s*(\d+)\s*(?:auto|carro|coche|vehículo)',
        r'(\d+)\s*(?:autos?|carros?|coches?|vehículos?)\s*(?:en\s*)?(?:estacionamiento|cochera)'
    ]
    
    for pattern in estacionamiento_patterns:
        if match := re.search(pattern, texto):
            caracteristicas["estacionamientos"] = int(match.group(1))
            break
    
    # Características booleanas
    caracteristicas["recamara_planta_baja"] = "recámara en planta baja" in texto or ("recamara" in texto and "planta baja" in texto)
    caracteristicas["cisterna"] = any(term in texto for term in ["cisterna", "aljibe"])
    
    # Edad/Antigüedad
    if "nueva" in texto or "nuevo" in texto or "estrenar" in texto:
        caracteristicas["edad"] = "nuevo"
    elif match := re.search(r'(\d+)\s*años?(?:\s*de\s*(?:antigüedad|construcción))?', texto):
        caracteristicas["edad"] = f"{match.group(1)} años"
    
    return caracteristicas

def extraer_amenidades(texto: str) -> Dict[str, bool]:
    """
    Extrae amenidades con patrones mejorados.
    """
    texto = texto.lower()
    
    amenidades = {
        "seguridad": False,
        "alberca": False,
        "patio": False,
        "bodega": False,
        "terraza": False,
        "jardin": False,
        "estudio": False,
        "roof_garden": False
    }
    
    # Seguridad
    amenidades["seguridad"] = any(term in texto for term in [
        "seguridad", "vigilancia", "privada", "caseta", "acceso controlado"
    ])
    
    # Alberca
    amenidades["alberca"] = any(term in texto for term in [
        "alberca", "piscina", "pool"
    ])
    
    # Patio
    amenidades["patio"] = "patio" in texto or "área exterior" in texto
    
    # Bodega
    amenidades["bodega"] = "bodega" in texto or "storage" in texto
    
    # Terraza
    amenidades["terraza"] = any(term in texto for term in [
        "terraza", "balcón", "balcon"
    ])
    
    # Jardín
    amenidades["jardin"] = any(term in texto for term in [
        "jardin", "jardín", "área verde"
    ])
    
    # Estudio
    amenidades["estudio"] = any(term in texto for term in [
        "estudio", "oficina", "despacho"
    ])
    
    # Roof Garden
    amenidades["roof_garden"] = any(term in texto for term in [
        "roof garden", "roofgarden", "roof-garden", "terraza en azotea"
    ])
    
    return amenidades

def limpiar_y_normalizar_referencias(referencias: List[str]) -> List[str]:
    """
    Limpia y normaliza las referencias de ubicación.
    """
    # Función para verificar si una referencia es parte de otra
    def es_subreferencia(ref1: str, ref2: str) -> bool:
        return ref1.lower() in ref2.lower() and ref1 != ref2

    # Normalizar referencias
    refs_normalizadas = []
    for ref in referencias:
        # Limpiar espacios extras y puntuación al final
        ref = ref.strip().strip('.,;')
        
        # Eliminar referencias que solo contienen medidas
        if re.match(r'^\d+\s*(?:metros?|m2|mts?|km).*$', ref.lower()):
            continue
            
        # Eliminar referencias muy cortas o que son solo números
        if len(ref.split()) < 2 or ref.replace(' ', '').isdigit():
            continue
            
        # Normalizar "minutos" y "metros"
        ref = re.sub(r'(\d+)\s*min(?:utos)?', r'\1 minutos', ref)
        ref = re.sub(r'(\d+)\s*mts?(?!\d)', r'\1 metros', ref)
        
        # Normalizar "a X de" -> "a X minutos/metros de"
        if re.match(r'^a\s+\d+\s+de', ref.lower()):
            continue
            
        refs_normalizadas.append(ref)
    
    # Eliminar duplicados preservando el orden
    refs_unicas = []
    for ref in refs_normalizadas:
        # Verificar si esta referencia ya está incluida en una más completa
        if not any(es_subreferencia(ref, ref_existente) for ref_existente in refs_unicas):
            # Verificar si esta referencia incluye alguna existente y reemplazarla
            refs_unicas = [r for r in refs_unicas if not es_subreferencia(r, ref)]
            refs_unicas.append(ref)
    
    # Ordenar por longitud y relevancia
    refs_unicas.sort(key=lambda x: (-len(x.split()), x))
    
    return refs_unicas

def limpiar_nombre_colonia(colonia: str) -> str:
    """
    Limpia y normaliza el nombre de la colonia.
    """
    if not colonia:
        return ""
        
    # Eliminar emojis y caracteres especiales
    colonia = re.sub(r'[^\w\s\-\.,]', '', colonia)
    
    # Eliminar palabras no deseadas al inicio
    palabras_no_deseadas = ['venta', 'renta', 'en', 'col', 'colonia', 'fracc', 'fraccionamiento', 'unidad']
    for palabra in palabras_no_deseadas:
        patron = f'^{palabra}\s+|^{palabra}\.?\s+'
        colonia = re.sub(patron, '', colonia, flags=re.IGNORECASE)
    
    # Eliminar información de precio
    colonia = re.sub(r'\$\s*[\d,.]+[kKmM]?', '', colonia)
    
    # Eliminar saltos de línea y espacios múltiples
    colonia = ' '.join(colonia.split())
    
    # Capitalizar palabras
    colonia = ' '.join(word.capitalize() for word in colonia.split())
    
    # Eliminar texto después de ciertos caracteres
    colonia = re.split(r'[\\\/\|\-\$]', colonia)[0].strip()
    
    return colonia

def limpiar_nombre_calle(calle: str) -> str:
    """
    Limpia y normaliza el nombre de la calle.
    """
    if not calle:
        return ""
        
    # Eliminar emojis y caracteres especiales
    calle = re.sub(r'[^\w\s\-\.,]', '', calle)
    
    # Eliminar palabras no deseadas al inicio
    palabras_no_deseadas = ['calle', 'av', 'avenida', 'blvd', 'boulevard', 'calzada', 'privada']
    for palabra in palabras_no_deseadas:
        patron = f'^{palabra}\s+|^{palabra}\.?\s+'
        calle = re.sub(patron, '', calle, flags=re.IGNORECASE)
    
    # Eliminar saltos de línea y espacios múltiples
    calle = ' '.join(calle.split())
    
    # Capitalizar palabras
    calle = ' '.join(word.capitalize() for word in calle.split())
    
    return calle

def es_referencia_valida(texto: str) -> bool:
    """
    Determina si una referencia de ubicación es válida.
    """
    # Palabras que indican que la referencia no es válida
    palabras_invalidas = [
        'precio', 'pesos', 'costo', 'venta', 'renta', 'compra', 'anticipo', 'enganche',
        'habitaciones', 'recamaras', 'baños', 'cocina', 'sala', 'comedor', 'garage',
        'estacionamiento', 'jardín', 'alberca', 'terraza', 'roof', 'garden', 'planta',
        'alta', 'baja', 'piso', 'nivel', 'construcción', 'terreno', 'superficie',
        'metros', 'cuadrados', 'm2', 'mt2', 'mts2', 'escritura', 'título', 'papeles',
        'crédito', 'credito', 'infonavit', 'fovissste', 'bancario', 'contado',
        'acabados', 'remodelada', 'nueva', 'usada', 'recién', 'recien', 'terminada',
        'equipada', 'amueblada', 'sin amueblar', 'vacía', 'vacia', 'disponible',
        'entrega', 'inmediata', 'preventa', 'oportunidad', 'inversión', 'inversion',
        'negociable', 'trato', 'directo', 'dueño', 'particular', 'inmobiliaria',
        'agencia', 'broker', 'asesor', 'corredor', 'bienes', 'raices', 'raíces',
        'lavamanos', 'lavabo', 'regadera', 'ducha', 'tina', 'jacuzzi', 'closet',
        'vestidor', 'alacena', 'bodega', 'cuarto', 'servicio', 'lavado', 'tendido'
    ]
    
    texto_lower = texto.lower()
    
    # Verificar si contiene palabras inválidas
    for palabra in palabras_invalidas:
        if palabra in texto_lower:
            return False
    
    return True

def obtener_colonia_conocida(texto: str) -> Tuple[str, str]:
    """
    Busca colonias conocidas en el texto y retorna la colonia y su ciudad.
    """
    # Repositorio de colonias conocidas con su ciudad correspondiente
    colonias_conocidas = {
        # Cuernavaca
        'lomas de cortes': ('Lomas De Cortes', 'Cuernavaca'),
        'lomas de cortés': ('Lomas De Cortes', 'Cuernavaca'),
        'lomas tetela': ('Lomas De Tetela', 'Cuernavaca'),
        'rancho tetela': ('Rancho Tetela', 'Cuernavaca'),
        'lomas de tzompantle': ('Lomas De Tzompantle', 'Cuernavaca'),
        'tzompantle': ('Tzompantle', 'Cuernavaca'),
        'reforma': ('Reforma', 'Cuernavaca'),
        'vista hermosa': ('Vista Hermosa', 'Cuernavaca'),
        'vistahermosa': ('Vista Hermosa', 'Cuernavaca'),
        'delicias': ('Delicias', 'Cuernavaca'),
        'jardines delicias': ('Jardines Delicias', 'Cuernavaca'),
        'rancho cortes': ('Rancho Cortes', 'Cuernavaca'),
        'flores magón': ('Flores Magón', 'Cuernavaca'),
        'plan de ayala': ('Plan De Ayala', 'Cuernavaca'),
        'paraiso': ('Paraiso', 'Cuernavaca'),
        'paraíso': ('Paraiso', 'Cuernavaca'),
        'unidad deportiva': ('Unidad Deportiva', 'Cuernavaca'),
        'ocotepec': ('Ocotepec', 'Cuernavaca'),
        'tlaltenango': ('Tlaltenango', 'Cuernavaca'),
        'tabachines': ('Tabachines', 'Cuernavaca'),
        'polvorín': ('Polvorin', 'Cuernavaca'),
        'buenavista': ('Buenavista', 'Cuernavaca'),
        
        # Jiutepec
        'las fincas': ('Las Fincas', 'Jiutepec'),
        'tejalpa': ('Tejalpa', 'Jiutepec'),
        'lomas del pedregal': ('Lomas Del Pedregal', 'Jiutepec'),
        'pedregal': ('Pedregal', 'Jiutepec'),
        
        # Temixco
        'burgos': ('Burgos', 'Temixco'),
        'burgos bugambilias': ('Burgos Bugambilias', 'Temixco'),
        'lomas de cuernavaca': ('Lomas De Cuernavaca', 'Temixco'),
        
        # Emiliano Zapata
        'san francisco': ('San Francisco', 'Emiliano Zapata'),
        'residencial encinos': ('Residencial Encinos', 'Emiliano Zapata'),
        'tezoyuca': ('Tezoyuca', 'Emiliano Zapata')
    }
    
    # Buscar coincidencias exactas primero
    texto_limpio = texto.lower().strip()
    for colonia_key, (colonia_nombre, ciudad) in colonias_conocidas.items():
        if f" {colonia_key} " in f" {texto_limpio} ":
            return colonia_nombre, ciudad
    
    # Si no hay coincidencias exactas, buscar coincidencias parciales
    for colonia_key, (colonia_nombre, ciudad) in colonias_conocidas.items():
        if colonia_key in texto_limpio:
            return colonia_nombre, ciudad
    
    return "", ""

def limpiar_referencias_ubicacion(referencias: List[str]) -> List[str]:
    """
    Limpia y normaliza las referencias de ubicación.
    """
    referencias_limpias = []
    
    for ref in referencias:
        # Convertir a minúsculas y eliminar espacios extras
        ref = ref.lower().strip()
        
        # Eliminar caracteres especiales y emojis
        ref = re.sub(r'[^\w\s,.-]', '', ref)
        
        # Normalizar espacios
        ref = ' '.join(ref.split())
        
        # Verificar longitud mínima y máxima
        if 5 <= len(ref) <= 150:
            referencias_limpias.append(ref)
    
    # Eliminar duplicados preservando el orden
    referencias_unicas = []
    for ref in referencias_limpias:
        if ref not in referencias_unicas:
            referencias_unicas.append(ref)
    
    return referencias_unicas

def extraer_ubicacion(texto: str, location: str = "", ciudad: str = "") -> Dict[str, str]:
    """
    Extrae información de ubicación con patrones mejorados.
    """
    texto_completo = f"{texto} {location} {ciudad}".lower()
    
    ubicacion = {
        "colonia": "",
        "calle": "",
        "estado": "",
        "ciudad": "",
        "ubicacion_referencia": ""
    }
    
    # Primero buscar menciones explícitas de ciudad
    ciudades_morelos = {
        'cuernavaca': 'Cuernavaca',
        'jiutepec': 'Jiutepec',
        'temixco': 'Temixco',
        'emiliano zapata': 'Emiliano Zapata',
        'xochitepec': 'Xochitepec',
        'yautepec': 'Yautepec',
        'cuautla': 'Cuautla',
        'jojutla': 'Jojutla',
        'zacatepec': 'Zacatepec',
        'tepoztlan': 'Tepoztlan',
        'tepoztlán': 'Tepoztlan'
    }
    
    # Patrones para detectar ciudad
    patrones_ciudad = [
        r'(?:municipio|en|de)\s+(?:de\s+)?([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'ubicad[oa]\s+en\s+([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'(?:col(?:onia)?|fracc(?:ionamiento)?)\s+[^,\n]+?,\s*([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'(?:en|de)\s+(?:la\s+)?(?:ciudad\s+de\s+)?([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
    ]
    
    # Buscar ciudad en el texto usando patrones
    ciudad_encontrada = ""
    
    # Primero buscar menciones directas de ciudad
    for ciudad_key, ciudad_nombre in ciudades_morelos.items():
        if f" {ciudad_key} " in f" {texto_completo} ":
            ciudad_encontrada = ciudad_nombre
            break
    
    # Si no se encontró ciudad con menciones directas exactas, buscar menciones parciales
    if not ciudad_encontrada:
        for ciudad_key, ciudad_nombre in ciudades_morelos.items():
            if ciudad_key in texto_completo:
                ciudad_encontrada = ciudad_nombre
                break
    
    # Si no se encontró ciudad con menciones directas, usar patrones
    if not ciudad_encontrada:
        for patron in patrones_ciudad:
            if match := re.search(patron, texto_completo):
                ciudad_candidata = match.group(1).strip().lower()
                # Verificar si la ciudad candidata está en nuestro diccionario
                for ciudad_key, ciudad_nombre in ciudades_morelos.items():
                    if ciudad_key in ciudad_candidata:
                        ciudad_encontrada = ciudad_nombre
                        break
                if ciudad_encontrada:
                    break
    
    if ciudad_encontrada:
        ubicacion["ciudad"] = ciudad_encontrada
        ubicacion["estado"] = "Morelos"
    
    # Buscar primero en el repositorio de colonias conocidas
    colonia_conocida, ciudad_conocida = obtener_colonia_conocida(texto_completo)
    if colonia_conocida:
        ubicacion["colonia"] = colonia_conocida
        if not ubicacion["ciudad"]:  # Solo asignar ciudad si no se encontró una mención explícita
            ubicacion["ciudad"] = ciudad_conocida
            ubicacion["estado"] = "Morelos"
    
    # Si no se encontró en el repositorio, continuar con la lógica existente de colonias
    if not ubicacion["colonia"]:
        # Patrones para calles
        patrones_calle = [
            r'(?:calle|av(?:enida)?|blvd?\.?|boulevard|calzada|privada)\s+([^,\.\n]+)',
            r'(?:ubicad[oa]\s+en\s+)(?:calle|av(?:enida)?|blvd?\.?|boulevard|calzada|privada)\s+([^,\.\n]+)',
            r'(?:sobre\s+)(?:calle|av(?:enida)?|blvd?\.?|boulevard|calzada|privada)\s+([^,\.\n]+)'
        ]
        
        # Buscar calle
        for patron in patrones_calle:
            if match := re.search(patron, texto_completo):
                calle = match.group(1).strip()
                if len(calle.split()) <= 5:  # No más de 5 palabras
                    ubicacion["calle"] = limpiar_nombre_calle(calle)
                    break
        
        # Patrones para detectar colonias
        colonia_patterns = [
            r'(?:col(?:onia)?\.?\s+)((?:[^\s,\.\n]+(?:\s+(?:de|del|la|las|los|el))?\s+)*[^\s,\.\n]+?)(?=\s*(?:,|\.|$|\n|junto|cerca|a un lado))',
            r'(?:fracc(?:ionamiento)?\.?\s+)((?:[^\s,\.\n]+(?:\s+(?:de|del|la|las|los|el))?\s+)*[^\s,\.\n]+?)(?=\s*(?:,|\.|$|\n|junto|cerca|a un lado))',
            r'(?:unidad\s+(?:hab(?:itacional)?|deportiva)\.?\s+)((?:[^\s,\.\n]+(?:\s+(?:de|del|la|las|los|el))?\s+)*[^\s,\.\n]+?)(?=\s*(?:,|\.|$|\n|junto|cerca|a un lado))',
            r'(?:residencial\s+)((?:[^\s,\.\n]+(?:\s+(?:de|del|la|las|los|el))?\s+)*[^\s,\.\n]+?)(?=\s*(?:,|\.|$|\n|junto|cerca|a un lado))',
            r'ubicad[oa]\s+en\s+((?:[^\s,\.\n]+(?:\s+(?:de|del|la|las|los|el))?\s+)*[^\s,\.\n]+?)(?=\s*(?:,|\.|$|\n|junto|cerca|a un lado))',
            r'en\s+(?:la\s+)?(?:col\.?\s+)?((?:[^\s,\.\n]+(?:\s+(?:de|del|la|las|los|el))?\s+)*[^\s,\.\n]+?)(?=\s*(?:,|\.|$|\n|junto|cerca|a un lado))'
        ]
        
        # Buscar colonias
        for pattern in colonia_patterns:
            if match := re.search(pattern, texto_completo):
                colonia = match.group(1).strip()
                if len(colonia.split()) <= 5:  # No más de 5 palabras
                    ubicacion["colonia"] = limpiar_nombre_colonia(colonia)
                    break
    
    # Buscar referencias de ubicación
    referencias = []
    
    # Patrones para referencias de ubicación
    patrones_referencia = [
        r'(?:a|en)\s+(?:\d+\s+)?(?:min(?:utos)?|cuadras?|pasos?|metros?|km)\s+(?:de|del|dela|a)\s+([^,\.\n]+)',
        r'(?:cerca|junto|próximo|proximo)\s+(?:de|a|al)\s+([^,\.\n]+)',
        r'(?:sobre|frente\s+a|enfrente\s+de|atrás\s+de|atras\s+de|a\s+espaldas\s+de)\s+([^,\.\n]+)',
        r'(?:esquina\s+con|cruce\s+con|entre)\s+([^,\.\n]+)',
        r'(?:a\s+la\s+altura\s+de)\s+([^,\.\n]+)',
        r'(?:en\s+la\s+zona\s+de)\s+([^,\.\n]+)',
        r'(?:zona|área|area)\s+(?:de|del|dela)\s+([^,\.\n]+)'
    ]
    
    # Buscar referencias basadas en patrones
    for patron in patrones_referencia:
        matches = re.finditer(patron, texto_completo)
        for match in matches:
            if match.groups():
                ref = match.group(0).strip()
                if 5 <= len(ref) <= 150 and es_referencia_valida(ref):
                    referencias.append(ref)
    
    # Limpiar y normalizar referencias
    referencias = limpiar_referencias_ubicacion(referencias)
    
    if referencias:
        ubicacion["ubicacion_referencia"] = "; ".join(referencias)
    
    # Si no se encontró ciudad pero hay referencias a Morelos, NO asignar Cuernavaca por defecto
    if not ubicacion["ciudad"] and "morelos" in texto_completo:
        ubicacion["estado"] = "Morelos"
    
    # Si se encontró una referencia a una ciudad en las referencias, usarla como ciudad
    if ubicacion["ubicacion_referencia"] and not ubicacion["ciudad"]:
        for ciudad_key, ciudad_nombre in ciudades_morelos.items():
            if ciudad_key in ubicacion["ubicacion_referencia"].lower():
                ubicacion["ciudad"] = ciudad_nombre
                ubicacion["estado"] = "Morelos"
                break
    
    return ubicacion

def extraer_legal(texto: str) -> Dict:
    """
    Extrae información legal con patrones mejorados.
    """
    texto = texto.lower()
    
    legal = {
        "escrituras": False,
        "cesion_derechos": False,
        "formas_de_pago": []
    }
    
    # Escrituras
    legal["escrituras"] = any(term in texto for term in [
        "escrituras", "escriturada", "título de propiedad"
    ])
    
    # Cesión de derechos
    legal["cesion_derechos"] = any(term in texto for term in [
        "cesión de derechos", "cesion de derechos", "traspaso"
    ])
    
    # Formas de pago
    formas_pago = {
        "contado": ["contado", "efectivo"],
        "crédito": ["credito", "crédito", "bancario", "hipotecario"],
        "infonavit": ["infonavit", "fovissste", "issste"],
    }
    
    for forma, keywords in formas_pago.items():
        if any(keyword in texto for keyword in keywords):
            legal["formas_de_pago"].append(forma)
    
    return legal

def procesar_propiedad(id_prop: str, datos: Dict) -> Dict:
    """
    Procesa una propiedad individual con la lógica mejorada.
    """
    if not isinstance(datos, dict):
        return None
    
    descripcion = str(datos.get("description", ""))
    precio = str(datos.get("precio", ""))
    location = str(datos.get("location", ""))
    ciudad = str(datos.get("ciudad", ""))
    link = str(datos.get("link", ""))
    titulo = str(datos.get("titulo", ""))
    
    # Normalizar precio
    precio_normalizado, moneda = normalizar_precio(precio)
    
    # Extraer tipo de operación
    tipo_operacion = extraer_tipo_operacion(descripcion + " " + titulo)
    
    # Extraer tipo de propiedad
    tipo_propiedad = extraer_tipo_propiedad(descripcion + " " + titulo)
    
    # Extraer superficie y construcción
    superficies = extraer_superficie(descripcion)
    
    # Extraer características
    caracteristicas = extraer_caracteristicas(descripcion)
    
    # Extraer amenidades
    amenidades = extraer_amenidades(descripcion)
    
    # Extraer ubicación
    ubicacion = extraer_ubicacion(descripcion, location, ciudad)
    
    # Extraer información legal
    legal = extraer_legal(descripcion)
    
    return {
        "id": id_prop,
        "link": link,
        "descripcion_original": descripcion,
        "ubicacion": ubicacion,
        "propiedad": {
            "tipo_propiedad": tipo_propiedad,
            "precio": precio,
            "precio_normalizado": precio_normalizado,
            "tipo_operacion": tipo_operacion,
            "moneda": moneda
        },
        "descripcion": {
            "caracteristicas": {
                **caracteristicas,
                **superficies
            },
            "amenidades": amenidades,
            "legal": legal
        }
    }

def es_propiedad(texto: str, titulo: str, precio: str = "", location: str = "") -> bool:
    """
    Determina si el elemento es una propiedad inmobiliaria o no.
    """
    # Función auxiliar para normalizar texto
    def normalizar_texto(texto: str) -> str:
        # Convertir a minúsculas
        texto = texto.lower()
        
        # Reemplazar caracteres decorativos comunes
        caracteres_decorativos = {
            '𝑨': 'a', '𝑩': 'b', '𝑪': 'c', '𝑫': 'd', '𝑬': 'e', '��': 'f', '𝑮': 'g',
            '𝑯': 'h', '𝑰': 'i', '𝑱': 'j', '𝑲': 'k', '𝑳': 'l', '𝑴': 'm', '𝑵': 'n',
            '𝑶': 'o', '𝑷': 'p', '𝑸': 'q', '𝑹': 'r', '𝑺': 's', '𝑻': 't', '𝑼': 'u',
            '𝑽': 'v', '𝑾': 'w', '𝑿': 'x', '𝒀': 'y', '𝒁': 'z',
            '𝓪': 'a', '𝓫': 'b', '𝓬': 'c', '𝓭': 'd', '𝓮': 'e', '𝓯': 'f', '𝓰': 'g',
            '𝓱': 'h', '𝓲': 'i', '𝓳': 'j', '𝓴': 'k', '𝓵': 'l', '𝓶': 'm', '𝓷': 'n',
            '𝓸': 'o', '𝓹': 'p', '𝓺': 'q', '𝓻': 'r', '𝓼': 's', '𝓽': 't', '𝓾': 'u',
            '𝓿': 'v', '𝔀': 'w', '𝔁': 'x', '𝔂': 'y', '𝔃': 'z',
            '🏠': 'casa', '🏡': 'casa', '🏢': 'edificio', '🏣': 'edificio',
            '📍': '', '✨': '', '🔹': '', '📏': '', '🛏️': '', '🍽️': '',
            '🛋️': '', '🚿': '', '🎥': '', '🚪': '', '🔐': '', '🏊': '',
            '🌴': '', '🚗': '', '📜': '', '💰': '', '💲': '', '💳': '',
            '⚠️': '', '✅': '', '❗': '', '‼️': '', '❌': '', '⭐': '',
            '🌟': '', '🔥': '', '📱': '', '☎️': '', '📞': '', '💬': '',
            '🏆': '', '🎯': '', '📌': '', '📍': '', '🗺️': '', '🌍': '',
            '⚡': '', '🔔': '', '📢': '', '🔊': '', '📣': '', '💥': '',
            '✨': '', '💫': '', '🌈': '', '🎨': '', '🎭': '', '🎪': ''
        }
        
        for decorativo, normal in caracteres_decorativos.items():
            texto = texto.replace(decorativo, normal)
        
        # Eliminar caracteres no alfanuméricos excepto espacios y puntuación básica
        texto = re.sub(r'[^\w\s.,;:()¿?¡!-]', '', texto)
        
        # Normalizar espacios múltiples
        texto = ' '.join(texto.split())
        
        return texto
    
    # Normalizar todos los textos de entrada
    texto = normalizar_texto(texto)
    titulo = normalizar_texto(titulo)
    precio = normalizar_texto(precio)
    location = normalizar_texto(location)
    
    # Si el título es genérico ("Chats" o "Marketplace"), nos enfocamos en la descripción
    if titulo in ["chats", "marketplace", "(20+) marketplace - venta", "notificaciones"]:
        # Verificar si la primera línea de la descripción contiene información de propiedad
        primera_linea = texto.split('\n')[0] if texto else ""
        if any(palabra in primera_linea.lower() for palabra in [
            'casa', 'departamento', 'terreno', 'local', 'propiedad', 'venta', 'renta',
            'habitaciones', 'recamaras', 'baños', 'inmueble', 'bienes raices', 'cuarto',
            'recamara', 'habitacion', 'monoambiente', 'loft', 'bungalo', 'bungalow'
        ]):
            return True
            
        # Buscar patrones específicos en la descripción completa
        patrones_descripcion = [
            # Patrones en español
            r'(?:casa|departamento|terreno|local|propiedad)\s+(?:en|de)\s+(?:venta|renta)',
            r'\d+\s*(?:habitaciones|recamaras|banos|cuartos)',
            r'(?:superficie|terreno|construccion):\s*\d+\s*m2',
            r'(?:bienes raices|inmobiliaria)',
            r'codigo\s+[a-z]\d+',  # Para códigos de inmobiliarias
            r'\$[\d,\.]+(?:\s*(?:m\.n\.|mxn|pesos))?',  # Para precios en formato mexicano
            r'(?:planta\s+(?:baja|alta))',  # Para descripciones de niveles
            r'(?:estancia|comedor|cocina|area\s+de\s+lavado)',  # Áreas comunes
            r'(?:habitaciones?|recamaras?|dormitorios?|cuartos?)',  # Dormitorios
            r'(?:bano\s+completo|medio\s+bano|bano\s+privado)',  # Baños
            r'(?:estacionamiento|cochera)',  # Estacionamiento
            r'(?:balcon|terraza|patio)',  # Áreas exteriores
            r'(?:escrituras?|titulo\s+de\s+propiedad)',  # Documentación
            r'(?:infonavit|fovissste|credito)',  # Financiamiento
            r'(?:m2|metros\s+cuadrados)',  # Medidas
            r'(?:ubicado|ubicada)\s+en',  # Ubicación
            r'(?:cerca\s+de|proximo\s+a|a\s+unos\s+pasos)',  # Referencias
            r'(?:vigilancia|seguridad)\s+24',  # Seguridad
            r'(?:acabados|remodelado|nuevo)',  # Estado
            r'(?:oportunidad|inversion|plusvalia)',  # Términos de venta
            r'(?:rento|alquilo)\s+(?:cuarto|habitacion|recamara|departamento)',  # Rentas
            r'(?:servicios?|internet|luz|agua)\s+incluidos?',  # Servicios incluidos
            r'(?:amueblado|sin amueblar)',  # Amueblado
            r'(?:estudiantes?|profesionistas?)',  # Público objetivo
            r'entrada\s+independiente',  # Características específicas
            
            # Patrones en inglés
            r'(?:house|home|apartment|condo|townhouse|property)\s+(?:for\s+)?(?:sale|rent)',
            r'(?:\d+)\s*(?:bed|bath|bedroom|bathroom)',
            r'(?:sq\s*ft|square\s*feet)',
            r'(?:real\s+estate|realty)',
            r'(?:listing|mls)',
            r'(?:residential|commercial)\s+(?:property|building)',
            r'(?:utilities|internet|water|electricity)\s+included',
            r'(?:furnished|unfurnished)',
            r'(?:private|shared)\s+(?:bathroom|entrance)',
            r'(?:parking|garage)',
            r'(?:yard|garden|patio)',
            r'(?:location|near|close\s+to)',
            r'(?:investment|opportunity)',
            r'(?:remodeled|updated|new)',
            r'(?:students|professionals)',
            r'(?:lease|rental)',
            r'(?:studio|loft)',
            r'(?:amenities|features)',
            r'(?:security|gated)',
            r'(?:community|complex)'
        ]
        
        if any(re.search(patron, texto, re.IGNORECASE) for patron in patrones_descripcion):
            return True
    
    # Si tiene dimensiones típicas de una propiedad
    patrones_dimension = [
        r'\d+\s*m2', r'\d+\s*metros?\s*cuadrados?',
        r'terreno\s*(?:de)?\s*\d+',
        r'construccion\s*(?:de)?\s*\d+',
        r'superficie\s*(?:de)?\s*\d+',
        r'\d+\s*mts?2?',  # Detectar "200 mt2", "200 mts", etc.
        r'\d+\s*m²',  # Detectar con símbolo especial de metros cuadrados
        r'(?:terreno|construccion|superficie):\s*\d+\s*m?2?',  # "terreno: 200m2"
        r'frente\s*(?:de)?\s*\d+(?:\.\d+)?\s*mts?',  # "frente de 23.71 mts"
        r'superficie\s*plana\s*(?:de)?\s*\d+',  # "superficie plana de 300"
        r'\$\s*\d+(?:,\d+)*(?:\.\d+)?\s*(?:m2|mt2|mts2|por\s+metro\s+cuadrado)',  # "$3,000 por metro cuadrado"
        r'\d+(?:\.\d+)?\s*(?:x|por)\s*\d+(?:\.\d+)?\s*(?:m2|mts?)?',  # "10 x 20", "10.5 x 20.5 m2"
        r'\d+\s*sq\s*ft',  # Medidas en inglés
        r'\d+\s*square\s*feet'
    ]
    
    for patron in patrones_dimension:
        if re.search(patron, texto, re.IGNORECASE):
            return True
    
    # Verificar si hay palabras clave que indiquen una propiedad
    palabras_clave_propiedad = [
        'casa', 'depto', 'departamento', 'terreno', 'lote', 'venta', 'renta',
        'recamara', 'recamaras', 'habitacion', 'habitaciones', 'm2', 'metros',
        'fraccionamiento', 'privada', 'condominio', 'alberca', 'jardin', 'jardin',
        'estacionamiento', 'garage', 'cochera', 'bano', 'banos', 'cocina',
        'sala', 'comedor', 'escrituras', 'infonavit', 'fovissste', 'credito',
        'construccion', 'construccion', 'plusvalia', 'plusvalia', 'inversion',
        'bienes raices', 'inmobiliaria', 'amenidades', 'vigilancia', 'seguridad',
        'roof garden', 'terraza', 'balcon', 'balcon', 'cuarto de servicio',
        'area de lavado', 'area de lavado', 'cisterna', 'tinaco', 'gas estacionario',
        'propiedad', 'inmueble', 'finca', 'residencia', 'vivienda', 'hogar',
        'duplex', 'triplex', 'penthouse', 'ph', 'suite', 'estudio', 'oficina',
        'local', 'bodega', 'nave', 'consultorio', 'edificio', 'planta baja',
        'planta alta', 'piso', 'nivel', 'acabados', 'remodelada', 'nueva',
        'estrenar', 'ubicada', 'ubicado', 'cerca de', 'zona', 'colonia',
        'fraccion', 'fracc', 'unidad', 'conjunto', 'residencial', 'habitacional',
        'minisplit', 'closet', 'vestidor', 'porton', 'porton', 'reja',
        'constancia comunal', 'sesion de derechos', 'superficie plana',
        'bardado', 'toma de agua', 'frente', 'calefaccion solar',
        'regadera exterior', 'iluminacion natural', 'ventilacion',
        'preventa', 'estrena ya', 'meses sin intereses', 'caseta',
        'green', 'hoyo', 'country club', 'residencial', 'exclusiva',
        'desarrollo', 'lotificar', 'avenida principal', 'monoambiente',
        'loft', 'bungalo', 'bungalow', 'townhouse', 'tiny house',
        'cuarto', 'recamara', 'habitacion',
        # Palabras clave en inglés
        'house', 'home', 'apartment', 'condo', 'townhouse', 'property',
        'real estate', 'bedroom', 'bathroom', 'kitchen', 'living room',
        'dining room', 'garage', 'yard', 'garden', 'patio', 'pool',
        'security', 'gated', 'community', 'complex', 'utilities',
        'furnished', 'unfurnished', 'remodeled', 'updated', 'new',
        'location', 'near', 'close to', 'investment', 'opportunity',
        'residential', 'commercial', 'studio', 'loft', 'amenities',
        'features', 'parking', 'storage', 'laundry'
    ]
    
    texto_completo = f"{texto} {titulo} {location}"
    palabras_encontradas = sum(1 for palabra in palabras_clave_propiedad if palabra in texto_completo.lower())
    
    # Si encontramos al menos 2 palabras clave de propiedad
    if palabras_encontradas >= 2:
        return True
    
    # Ubicaciones específicas de Morelos
    ubicaciones = [
        'cuernavaca', 'jiutepec', 'temixco', 'emiliano zapata', 'xochitepec',
        'yautepec', 'cuautla', 'jojutla', 'zacatepec', 'tepoztlan', 'tepoztlan',
        'civac', 'tezoyuca', 'tejalpa', 'zapata', 'las fuentes',
        'la pradera', 'la joya', 'el miraval', 'la herradura',
        'lomas de la herradura', 'lomas de cuernavaca', 'lomas de cocoyoc',
        'club de golf', 'hacienda de las palmas', 'rinconada',
        'buenavista', 'centro', 'la carolina', 'las palmas',
        'los pinos', 'los ciruelos', 'los limones', 'los naranjos',
        'los sabinos', 'los laureles', 'los cedros', 'los robles',
        'los almendros', 'los olivos', 'los mangos', 'los duraznos',
        'las flores', 'las rosas', 'las margaritas', 'las violetas',
        'las azucenas', 'las orquideas', 'las bugambilias',
        'ahuatepec', 'ocotepec', 'chapultepec', 'tlaltenango',
        'vista hermosa', 'palmira', 'delicias', 'reforma',
        'san anton', 'san jeronimo', 'santa maria',
        'burgos', 'sumiya', 'tabachines', 'los cizos', 'acapantzingo',
        'campo verde', 'las aguilas', 'las aguilas', 'las palmas',
        'chipitlan', 'antonio barona', 'atlacomulco', 'huitzilac',
        'paraiso', 'country club', 'milpillas', 'paseos del rio',
        'jardines de delicias', 'nueva santa maria', 'tulipanes',
        'texcal', 'upemor', 'satelite'  # Agregadas nuevas ubicaciones
    ]
    
    # Verificar si la ubicación es de Morelos y hay al menos una palabra clave
    for ubicacion in ubicaciones:
        if ubicacion in texto_completo.lower() or ubicacion in location.lower():
            if any(palabra in texto_completo.lower() for palabra in palabras_clave_propiedad):
                return True
    
    return False

def procesar_archivo():
    """
    Procesa el archivo completo de propiedades.
    """
    try:
        # Leer archivo de entrada
        with open('resultados/repositorio_propiedades.json', 'r', encoding='utf-8') as f:
            propiedades_dict = json.load(f)
        
        # Procesar propiedades
        propiedades_procesadas = []
        no_propiedades = []
        errores = []
        
        # Contadores para depuración
        total_items = len(propiedades_dict)
        items_sin_descripcion = 0
        items_sin_precio = 0
        
        for id_prop, datos in propiedades_dict.items():
            try:
                if id_prop != "None":
                    # Obtener campos asegurándonos de que existan, probando diferentes nombres
                    descripcion = ""
                    # Lista expandida de posibles nombres para el campo descripción
                    campos_descripcion = [
                        "description", "desc", "texto", "descripcion", "descripcion_raw",
                        "descrition", "descripion", "description_raw", "texto_raw",
                        "texto_original", "descripcion_original", "description_original",
                        "desc_raw", "desc_original"
                    ]
                    
                    for campo in campos_descripcion:
                        if campo in datos:
                            descripcion = str(datos[campo]).strip()
                            if descripcion:
                                break
                    
                    # También buscar en el diccionario ignorando mayúsculas/minúsculas
                    if not descripcion:
                        for campo in campos_descripcion:
                            for key in datos.keys():
                                if key.lower() == campo.lower():
                                    descripcion = str(datos[key]).strip()
                                    if descripcion:
                                        break
                            if descripcion:
                                break
                    
                    titulo = ""
                    for campo in ["titulo", "title", "titulo_raw", "title_raw"]:
                        if campo in datos:
                            titulo = str(datos[campo]).strip()
                            if titulo:
                                break
                    
                    precio = ""
                    for campo in ["precio", "price", "precio_raw", "price_raw"]:
                        if campo in datos:
                            precio = str(datos[campo]).strip()
                            if precio:
                                break
                    
                    location = ""
                    for campo in ["location", "ubicacion", "ciudad", "location_raw", "ubicacion_raw"]:
                        if campo in datos:
                            location = str(datos[campo]).strip()
                            if location:
                                break
                    
                    # Contar campos vacíos
                    if not descripcion:
                        items_sin_descripcion += 1
                    if not precio:
                        items_sin_precio += 1
                    
                    # Verificar si es una propiedad
                    if es_propiedad(descripcion, titulo, precio, location):
                        resultado = procesar_propiedad(id_prop, datos)
                        if resultado:
                            propiedades_procesadas.append(resultado)
                    else:
                        # Asegurarnos de obtener la descripción original
                        descripcion_original = ""
                        for campo in ["descripcion_raw", "description_raw", "description", "descripcion_original", "texto_original"]:
                            if campo in datos:
                                descripcion_original = str(datos[campo]).strip()
                                if descripcion_original:
                                    break
                        
                        no_propiedades.append({
                            "id": id_prop,
                            "link": datos.get("link", ""),
                            "titulo": titulo,
                            "descripcion": descripcion,
                            "descripcion_original": descripcion_original or descripcion,  # Si no hay original, usar la descripción normal
                            "precio": precio,
                            "precio_original": datos.get("precio_original", datos.get("price_original", "")),
                            "location": location,
                            "ciudad": datos.get("ciudad", ""),
                            "fecha": datos.get("fecha", datos.get("date", "")),
                            "vendedor": datos.get("vendedor", datos.get("seller", "")),
                            "vendedor_id": datos.get("vendedor_id", datos.get("seller_id", "")),
                            "categoria": datos.get("categoria", datos.get("category", "")),
                            "subcategoria": datos.get("subcategoria", datos.get("subcategory", "")),
                            "estado_producto": datos.get("estado_producto", datos.get("condition", "")),
                            "razon": "No es una propiedad inmobiliaria"
                        })
            except Exception as e:
                errores.append({
                    "id": id_prop,
                    "error": str(e),
                    "datos": datos
                })
        
        # Guardar resultados de propiedades válidas
        with open('resultados/propiedades_estructuradas.json', 'w', encoding='utf-8') as f:
            json.dump({
                "propiedades": propiedades_procesadas,
                "metadata": {
                    "total_procesadas": len(propiedades_procesadas),
                    "total_errores": len(errores),
                    "total_no_propiedades": len(no_propiedades)
                }
            }, f, ensure_ascii=False, indent=2)
        
        # Guardar elementos que no son propiedades
        with open('resultados/no_propiedades.json', 'w', encoding='utf-8') as f:
            json.dump({
                "items": no_propiedades,
                "metadata": {
                    "total": len(no_propiedades),
                    "items_sin_descripcion": items_sin_descripcion,
                    "items_sin_precio": items_sin_precio
                }
            }, f, ensure_ascii=False, indent=2)
        
        # Guardar log de errores si hay alguno
        if errores:
            with open('resultados/errores_procesamiento.json', 'w', encoding='utf-8') as f:
                json.dump(errores, f, ensure_ascii=False, indent=2)
        
        print(f"Procesamiento completado:")
        print(f"- Total de items en repositorio: {total_items}")
        print(f"- Items sin descripción: {items_sin_descripcion}")
        print(f"- Items sin precio: {items_sin_precio}")
        print(f"- Propiedades válidas procesadas: {len(propiedades_procesadas)}")
        print(f"- Items que no son propiedades: {len(no_propiedades)}")
        print(f"- Errores encontrados: {len(errores)}")
        
    except Exception as e:
        print(f"Error durante el procesamiento: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    procesar_archivo() 