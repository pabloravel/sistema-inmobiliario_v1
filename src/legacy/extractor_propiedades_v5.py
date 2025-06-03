# Mejoras en la versión 5:
# 1. Detección mejorada de campos de descripción:
#    - Ahora busca en múltiples campos: description, description_raw, descripcion, descripcion_raw, desc, texto
#    - Prioriza la información encontrada en la descripción sobre otros campos
#
# 2. Validación más estricta de propiedades:
#    - Nueva lista de palabras clave que indican que NO es una propiedad (busco, solicito, etc.)
#    - Requiere al menos 2 palabras clave de propiedad o dimensiones específicas
#    - Mejor detección de dimensiones y características típicas de propiedades
#
# 3. Mejoras en la detección de ubicación:
#    - Prioridad a Jiutepec sobre otras ciudades para evitar falsos positivos
#    - Más patrones para detectar referencias de ubicación
#    - Mejor limpieza de nombres de colonias y calles
#
# 4. Procesamiento más robusto:
#    - Mejor manejo de errores y casos edge
#    - Validación de campos antes de procesarlos
#    - Limpieza de espacios y caracteres especiales
#
# 5. Logging mejorado:
#    - Más detalles sobre items sin descripción o precio
#    - Mejor categorización de razones por las que un item no es propiedad
#    - Tracking de errores más detallado

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
    texto = texto.lower().strip()
    resultado = {"superficie_m2": 0, "construccion_m2": 0}
    
    # Limpiar el texto para facilitar la detección
    texto = texto.replace('²', '2')  # Normalizar el superíndice ²
    texto = texto.replace(' x ', 'x')  # Normalizar multiplicación
    texto = texto.replace('*', 'x')  # Normalizar multiplicación
    texto = texto.replace(',', '')  # Eliminar comas en números
    texto = texto.replace('mts', 'm')  # Normalizar metros
    texto = texto.replace('mt', 'm')  # Normalizar metros
    
    # Patrones para superficie total mejorados
    superficie_patterns = [
        # Patrones de superficie explícita
        r'superficie:?\s*(\d+)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)',
        r'superficie\s*(?:del?\s*)?(?:terreno|lote):?\s*(\d+)',
        r'(\d+)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)\s*(?:de\s*)?(?:terreno|superficie|lote)',
        
        # Patrones de dimensiones (frente x fondo)
        r'(\d+)\s*(?:m|metros?)?\s*(?:de\s*)?frente\s*(?:por|x|\*)\s*(\d+)\s*(?:m|metros?)?\s*(?:de\s*)?fondo',
        r'(\d+)\s*(?:por|x|\*)\s*(\d+)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)?',
        
        # Patrones de terreno/lote
        r'terreno:?\s*(\d+)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)',
        r'lote\s*(?:de)?\s*(\d+)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)',
        
        # Patrones simples de metros
        r'(\d+)\s*m2\b',
        r'(\d+)\s*metros?\s*cuadrados?',
        r'(\d+)\s*m²',
        
        # Patrones específicos de área
        r'área\s*(?:de|del?)?\s*(\d+)\s*(?:m2|m²|metros?)',
        r'area\s*(?:de|del?)?\s*(\d+)\s*(?:m2|m²|metros?)',
        
        # Patrones de medidas sueltas
        r'mide\s*(\d+)\s*(?:m2|m²|metros?)',
        r'son\s*(\d+)\s*(?:m2|m²|metros?)',
        
        # Patrones de números seguidos de unidades
        r'\b(\d+)\s*m(?:ts?)?2?\b',
        r'\b(\d+)\s*metros?\b'
    ]
    
    # Patrones para construcción mejorados
    construccion_patterns = [
        # Patrones explícitos de construcción
        r'(?:área|area|superficie)\s*(?:de\s*)?construida:?\s*(\d+)',
        r'(?:área|area|superficie)\s*(?:de\s*)?construcción:?\s*(\d+)',
        r'construcción:?\s*(\d+)\s*(?:m2|m²|metros?)',
        r'(\d+)\s*(?:m2|m²|metros?)\s*(?:de)?\s*construcción',
        
        # Patrones de metros construidos
        r'(\d+)\s*(?:m2|m²|metros?)\s*construidos?',
        r'construidos?:?\s*(\d+)\s*(?:m2|m²|metros?)',
        
        # Patrones simples de construcción
        r'construccion\s*(?:de)?\s*(\d+)',
        r'(\d+)\s*de\s*construccion',
        
        # Patrones específicos
        r'\b(\d+)\s*(?:m2|m²|metros?)\s*(?:de)?\s*(?:const|construcción)',
        r'const(?:ruidos?)?:?\s*(\d+)',
        r'área\s*construida:?\s*(\d+)',
        r'area\s*construida:?\s*(\d+)',
        
        # Patrón para números seguidos de "de construcción"
        r'\b(\d+)\s*(?:de)?\s*construccion\b'
    ]
    
    # Buscar superficie
    for pattern in superficie_patterns:
        if match := re.search(pattern, texto):
            try:
                # Caso especial para dimensiones (frente x fondo)
                if ('frente' in pattern or 'por' in pattern or 'x' in pattern) and len(match.groups()) == 2:
                    frente = float(match.group(1))
                    fondo = float(match.group(2))
                    valor = int(frente * fondo)
                else:
                    valor = int(float(match.group(1)))
                
                # Validar que el valor sea razonable (entre 20 y 10000 m2)
                if 20 <= valor <= 10000:
                    resultado["superficie_m2"] = valor
                    break
            except (ValueError, TypeError):
                continue
    
    # Buscar construcción
    for pattern in construccion_patterns:
        if match := re.search(pattern, texto):
            try:
                valor = int(float(match.group(1)))
                # Validar que el valor sea razonable (entre 20 y 5000 m2)
                if 20 <= valor <= 5000:
                    resultado["construccion_m2"] = valor
                    break
            except (ValueError, TypeError):
                continue
    
    # Si no se encontró superficie pero hay dimensiones en el texto
    if resultado["superficie_m2"] == 0:
        # Buscar números que podrían ser metros cuadrados
        numeros = re.findall(r'\b(\d+)\s*(?:m2|mts2?|metros?(?:\s*cuadrados?)?)\b', texto)
        if numeros:
            for num in numeros:
                try:
                    valor = int(float(num))
                    if 20 <= valor <= 10000:
                        resultado["superficie_m2"] = valor
                        break
                except (ValueError, TypeError):
                    continue
    
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
        'el capiri': ('El Capiri', 'Cuernavaca'),
        'capiri': ('El Capiri', 'Cuernavaca'),
        'los pinos': ('Los Pinos', 'Cuernavaca'),
        'los volcanes': ('Los Volcanes', 'Cuernavaca'),
        'las palmas': ('Las Palmas', 'Cuernavaca'),
        
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
            
    # Buscar referencias a lugares conocidos
    lugares_conocidos = {
        'oxxo del capiri': ('El Capiri', 'Cuernavaca'),
        'oxxo capiri': ('El Capiri', 'Cuernavaca'),
        'capiri': ('El Capiri', 'Cuernavaca'),
        'el capiri': ('El Capiri', 'Cuernavaca'),
        'plaza capiri': ('El Capiri', 'Cuernavaca'),
    }
    
    for lugar_key, (colonia_nombre, ciudad) in lugares_conocidos.items():
        if lugar_key in texto_limpio:
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

def obtener_zona_conocida(texto: str) -> str:
    """
    Detecta la zona de la ciudad basada en patrones y referencias conocidas.
    """
    texto = texto.lower()
    
    # Mapeo de zonas conocidas con sus variantes y referencias
    zonas = {
        "Zona Dorada": [
            r'zona\s*dorada',
            r'área\s*dorada',
            r'sector\s*dorado',
            r'av(?:enida)?\s*san\s*diego',
            r'rio\s*mayo',
            r'diana\s*cazadora',
            r'av(?:enida)?\s*diana',
            r'jardines\s*delicias',
            r'delicias',
            r'vista\s*hermosa',
            r'reforma'
        ],
        "Zona Norte": [
            r'zona\s*norte',
            r'área\s*norte',
            r'sector\s*norte',
            r'lomas\s*de\s*cortes',
            r'lomas\s*tetela',
            r'rancho\s*tetela',
            r'tzompantle',
            r'ahuatepec',
            r'santa\s*maría',
            r'chamilpa'
        ],
        "Zona Sur": [
            r'zona\s*sur',
            r'área\s*sur',
            r'sector\s*sur',
            r'chipitlan',
            r'palmira',
            r'bellavista',
            r'tlaltenango',
            r'acapantzingo',
            r'antonio\s*barona'
        ],
        "Zona Centro": [
            r'zona\s*centro',
            r'área\s*centro',
            r'sector\s*centro',
            r'centro\s*histórico',
            r'centro\s*historico',
            r'downtown',
            r'zócalo',
            r'zocalo',
            r'jardín\s*juárez',
            r'jardin\s*juarez',
            r'guerrero'
        ],
        "Zona Este": [
            r'zona\s*este',
            r'área\s*este',
            r'sector\s*este',
            r'buenavista',
            r'ocotepec',
            r'atlacomulco',
            r'chapultepec'
        ],
        "Zona Oeste": [
            r'zona\s*oeste',
            r'área\s*oeste',
            r'sector\s*oeste',
            r'tabachines',
            r'provincias',
            r'lomas\s*de\s*la\s*selva',
            r'la\s*selva'
        ]
    }
    
    # Buscar coincidencias en el texto
    for zona, patrones in zonas.items():
        for patron in patrones:
            if re.search(patron, texto):
                return zona
    
    return ""

def extraer_ubicacion(texto: str, location: str = "", ciudad: str = "") -> Dict[str, str]:
    """
    Extrae información de ubicación con patrones mejorados.
    Prioriza la información encontrada en la descripción.
    """
    # Inicializar el diccionario de ubicación
    ubicacion = {
        "colonia": "",
        "calle": "",
        "estado": "",
        "ciudad": "",
        "zona": "",
        "ubicacion_referencia": ""
    }
    
    # Detectar zona
    ubicacion["zona"] = obtener_zona_conocida(texto.lower())
    
    # Ciudades conocidas de Morelos
    ciudades_morelos = {
        'jiutepec': 'Jiutepec',  # Ponemos Jiutepec primero para darle prioridad
        'cuernavaca': 'Cuernavaca',
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
    
    # Patrones para detectar ciudad en la descripción
    patrones_ciudad = [
        r'(?:ubicad[oa]\s+en)\s+([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'(?:en|de)\s+(?:la\s+ciudad\s+de\s+)?([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'(?:municipio\s+de)\s+([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'(?:col(?:onia)?|fracc(?:ionamiento)?)\s+[^,\n]+?,\s*([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'(?:en)\s+([a-zá-úñ\s]+?)(?:,|\s+morelos|\s+mor\.?|$)',
        r'propiedad\s+(?:en|ubicada\s+en)\s+([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'casa\s+(?:en|ubicada\s+en)\s+([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'departamento\s+(?:en|ubicado\s+en)\s+([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'terreno\s+(?:en|ubicado\s+en)\s+([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)'
    ]
    
    ciudad_encontrada = ""
    
    # 1. Buscar ciudad explícitamente mencionada en la descripción
    texto_lower = texto.lower()
    
    # Primero buscar patrones específicos en la descripción
    for patron in patrones_ciudad:
        if match := re.search(patron, texto_lower):
            ciudad_candidata = match.group(1).strip().lower()
            for ciudad_key, ciudad_nombre in ciudades_morelos.items():
                if ciudad_key in ciudad_candidata:
                    ciudad_encontrada = ciudad_nombre
                    break
            if ciudad_encontrada:
                break
    
    # Si no se encontró con patrones, buscar menciones directas en la descripción
    if not ciudad_encontrada:
        for ciudad_key, ciudad_nombre in ciudades_morelos.items():
            # Buscar coincidencias exactas primero
            if f" {ciudad_key} " in f" {texto_lower} ":
                ciudad_encontrada = ciudad_nombre
                break
            # Si no hay coincidencia exacta, buscar coincidencia parcial
            elif ciudad_key in texto_lower:
                ciudad_encontrada = ciudad_nombre
                break
    
    # 2. Si se encontró una ciudad, asignarla
    if ciudad_encontrada:
        ubicacion["ciudad"] = ciudad_encontrada
        ubicacion["estado"] = "Morelos"
    
    # 3. Buscar colonia conocida
    colonia_conocida, ciudad_conocida = obtener_colonia_conocida(texto_lower)
    if colonia_conocida:
        ubicacion["colonia"] = colonia_conocida
        # Solo asignar la ciudad de la colonia si no se encontró una mención explícita en la descripción
        if not ubicacion["ciudad"]:
            ubicacion["ciudad"] = ciudad_conocida
            ubicacion["estado"] = "Morelos"
    
    # 4. Si no se encontró colonia en el repositorio, buscar en el texto
    if not ubicacion["colonia"]:
        # Patrones para calles
        patrones_calle = [
            r'(?:calle|av(?:enida)?|blvd?\.?|boulevard|calzada|privada)\s+([^,\.\n]+)',
            r'(?:ubicad[oa]\s+en\s+)(?:calle|av(?:enida)?|blvd?\.?|boulevard|calzada|privada)\s+([^,\.\n]+)',
            r'(?:sobre\s+)(?:calle|av(?:enida)?|blvd?\.?|boulevard|calzada|privada)\s+([^,\.\n]+)'
        ]
        
        # Buscar calle
        for patron in patrones_calle:
            if match := re.search(patron, texto_lower):
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
            if match := re.search(pattern, texto_lower):
                colonia = match.group(1).strip()
                if len(colonia.split()) <= 5:  # No más de 5 palabras
                    ubicacion["colonia"] = limpiar_nombre_colonia(colonia)
                    break
    
    # 5. Buscar referencias de ubicación
    referencias = []
    patrones_referencia = [
        r'(?:a|en)\s+(\d+)\s*(?:min(?:utos)?|cuadras?|pasos?|metros?|km)\s+(?:de|del|dela|a)\s+([^,\.\n]+)',
        r'(?:cerca|junto|próximo|proximo)\s+(?:de|a|al)\s+([^,\.\n]+)',
        r'(?:sobre|frente\s+a|enfrente\s+de|atrás\s+de|atras\s+de|a\s+espaldas\s+de)\s+([^,\.\n]+)',
        r'(?:esquina\s+con|cruce\s+con|entre)\s+([^,\.\n]+)',
        r'(?:a\s+la\s+altura\s+de)\s+([^,\.\n]+)',
        r'(?:en\s+la\s+zona\s+de)\s+([^,\.\n]+)',
        r'(?:zona|área|area)\s+(?:de|del|dela)\s+([^,\.\n]+)'
    ]
    
    # Buscar referencias basadas en patrones
    for patron in patrones_referencia:
        matches = re.finditer(patron, texto_lower)
        for match in matches:
            if match.groups():
                ref = match.group(0).strip()
                if 5 <= len(ref) <= 150 and es_referencia_valida(ref):
                    referencias.append(ref)
    
    # Limpiar y normalizar referencias
    referencias = limpiar_referencias_ubicacion(referencias)
    
    if referencias:
        ubicacion["ubicacion_referencia"] = "; ".join(referencias)
    
    # Si no se encontró ciudad pero hay referencias a Morelos
    if not ubicacion["ciudad"] and "morelos" in texto_lower:
        ubicacion["estado"] = "Morelos"
    
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

def extraer_precios(texto: str) -> Dict[str, Union[str, float]]:
    """
    Extrae diferentes tipos de precios y costos del texto.
    """
    precios = {
        "precio_venta": "",
        "precio_renta": "",
        "precio_mantenimiento": "",
        "precio_m2": "",
        "rango_precio": {
            "min": "",
            "max": ""
        }
    }
    
    texto = texto.lower()
    
    # Patrones para diferentes tipos de precios
    patrones_precio = {
        "venta": [
            r'(?:precio|costo|valor)\s*(?:de\s*)?(?:venta|total)?\s*:?\s*\$?\s*([\d,\.]+)(?:k|m|mil|millones?)?',
            r'(?:vendo|vendemos|se\s+vende\s+en)\s*(?:en)?\s*\$?\s*([\d,\.]+)(?:k|m|mil|millones?)?',
            r'\$\s*([\d,\.]+)(?:k|m|mil|millones?)?\s*(?:pesos)?(?:\s*(?:a\s*tratar|negociables?|fijos?))?'
        ],
        "renta": [
            r'(?:renta|alquiler)\s*(?:mensual)?\s*:?\s*\$?\s*([\d,\.]+)',
            r'(?:se\s+renta\s+en|rento|rentamos)\s*\$?\s*([\d,\.]+)',
            r'\$\s*([\d,\.]+)\s*(?:al\s*mes|mensuales?|por\s*mes)'
        ],
        "mantenimiento": [
            r'(?:cuota|pago|costo)\s*(?:de\s*)?mantenimiento\s*(?:mensual|anual)?\s*:?\s*\$?\s*([\d,\.]+)',
            r'mantenimiento\s*(?:mensual|anual)?\s*:?\s*\$?\s*([\d,\.]+)',
            r'mantenimiento\s*de\s*\$?\s*([\d,\.]+)'
        ],
        "m2": [
            r'\$\s*([\d,\.]+)\s*(?:por|x|\*)\s*m2',
            r'(?:precio|costo|valor)\s*(?:por\s*)?m2\s*:?\s*\$?\s*([\d,\.]+)',
            r'(?:metro\s*cuadrado|m2)\s*(?:a|en)\s*\$?\s*([\d,\.]+)'
        ]
    }
    
    # Buscar precios específicos
    for tipo, patrones in patrones_precio.items():
        for patron in patrones:
            if match := re.search(patron, texto):
                precio = match.group(1).replace(',', '')
                try:
                    valor = float(precio)
                    # Aplicar multiplicadores
                    if 'k' in match.group(0).lower() or 'mil' in match.group(0).lower():
                        valor *= 1_000
                    elif 'm' in match.group(0).lower() or 'millon' in match.group(0).lower():
                        valor *= 1_000_000
                    
                    # Validar rangos razonables
                    if tipo == "venta" and 500_000 <= valor <= 50_000_000:
                        precios["precio_venta"] = f"${valor:,.2f}"
                    elif tipo == "renta" and 3_000 <= valor <= 150_000:
                        precios["precio_renta"] = f"${valor:,.2f}"
                    elif tipo == "mantenimiento" and 100 <= valor <= 20_000:
                        precios["precio_mantenimiento"] = f"${valor:,.2f}"
                    elif tipo == "m2" and 1_000 <= valor <= 100_000:
                        precios["precio_m2"] = f"${valor:,.2f}"
                except ValueError:
                    continue
    
    # Buscar rangos de precios
    patrones_rango = [
        r'(?:entre|desde)\s*\$?\s*([\d,\.]+)(?:k|m|mil|millones?)?\s*(?:hasta|y|a)\s*\$?\s*([\d,\.]+)(?:k|m|mil|millones?)?',
        r'\$?\s*([\d,\.]+)(?:k|m|mil|millones?)?\s*(?:a|hasta)\s*\$?\s*([\d,\.]+)(?:k|m|mil|millones?)?'
    ]
    
    for patron in patrones_rango:
        if match := re.search(patron, texto):
            try:
                min_precio = float(match.group(1).replace(',', ''))
                max_precio = float(match.group(2).replace(',', ''))
                
                # Aplicar multiplicadores
                if 'k' in match.group(0).lower() or 'mil' in match.group(0).lower():
                    min_precio *= 1_000
                    max_precio *= 1_000
                elif 'm' in match.group(0).lower() or 'millon' in match.group(0).lower():
                    min_precio *= 1_000_000
                    max_precio *= 1_000_000
                
                # Validar que el rango sea razonable
                if 500_000 <= min_precio <= max_precio <= 50_000_000:
                    precios["rango_precio"]["min"] = f"${min_precio:,.2f}"
                    precios["rango_precio"]["max"] = f"${max_precio:,.2f}"
            except ValueError:
                continue
    
    return precios

def validar_precio_por_zona(precio: float, zona: str, tipo_operacion: str) -> bool:
    """
    Valida si el precio es razonable para la zona y tipo de operación.
    """
    rangos_precio = {
        "Zona Dorada": {
            "venta": (5_000_000, 50_000_000),
            "renta": (15_000, 150_000)
        },
        "Zona Norte": {
            "venta": (2_000_000, 20_000_000),
            "renta": (8_000, 80_000)
        },
        "Zona Sur": {
            "venta": (1_500_000, 15_000_000),
            "renta": (6_000, 60_000)
        },
        "Zona Centro": {
            "venta": (2_500_000, 25_000_000),
            "renta": (10_000, 100_000)
        },
        "Zona Este": {
            "venta": (1_800_000, 18_000_000),
            "renta": (7_000, 70_000)
        },
        "Zona Oeste": {
            "venta": (2_000_000, 20_000_000),
            "renta": (8_000, 80_000)
        }
    }
    
    # Si no tenemos información de la zona, no podemos validar
    if not zona or zona not in rangos_precio:
        return True
        
    rango = rangos_precio[zona].get(tipo_operacion)
    if not rango:
        return True
        
    min_precio, max_precio = rango
    return min_precio <= precio <= max_precio

def extraer_mantenimiento(texto: str) -> Dict[str, str]:
    """
    Extrae información sobre mantenimiento y cuotas.
    """
    texto = texto.lower()
    
    resultado = {
        "cuota_mantenimiento": "",
        "periodo": "",
        "incluye": []
    }
    
    # Patrones para detectar cuota de mantenimiento
    patrones = [
        r'(?:cuota|pago|costo)\s*(?:de\s*)?mantenimiento\s*(?:mensual|anual)?\s*:?\s*\$?\s*([\d,\.]+)',
        r'mantenimiento\s*(?:mensual|anual)?\s*:?\s*\$?\s*([\d,\.]+)',
        r'mantenimiento\s*de\s*\$?\s*([\d,\.]+)',
        r'cuota\s*mensual\s*:?\s*\$?\s*([\d,\.]+)',
        r'cuota\s*de\s*\$?\s*([\d,\.]+)\s*(?:mensual|al mes)',
        r'(?:cuota|pago)\s*(?:de\s*)?(?:mantenimiento|administración)\s*\$?\s*([\d,\.]+)'
    ]
    
    # Detectar periodo
    if 'mensual' in texto or 'al mes' in texto or 'por mes' in texto:
        resultado["periodo"] = "mensual"
    elif 'anual' in texto or 'al año' in texto or 'por año' in texto:
        resultado["periodo"] = "anual"
    
    # Buscar monto de mantenimiento
    for patron in patrones:
        if match := re.search(patron, texto):
            try:
                valor = float(match.group(1).replace(',', ''))
                # Validar que el valor sea razonable
                if resultado["periodo"] == "mensual" and 100 <= valor <= 20000:
                    resultado["cuota_mantenimiento"] = f"${valor:,.2f}"
                elif resultado["periodo"] == "anual" and 1000 <= valor <= 200000:
                    resultado["cuota_mantenimiento"] = f"${valor:,.2f}"
                elif 100 <= valor <= 20000:  # Si no hay periodo especificado, asumir mensual
                    resultado["cuota_mantenimiento"] = f"${valor:,.2f}"
                    resultado["periodo"] = "mensual"
            except ValueError:
                continue
    
    # Detectar qué incluye el mantenimiento
    servicios = {
        "seguridad": [r'seguridad', r'vigilancia', r'guardia'],
        "jardinería": [r'jardin(?:eria)?', r'areas verdes', r'áreas verdes'],
        "limpieza": [r'limpieza', r'mantenimiento de areas comunes'],
        "agua": [r'agua', r'servicio de agua'],
        "luz áreas comunes": [r'luz de areas comunes', r'electricidad de areas comunes'],
        "gas": [r'gas', r'servicio de gas'],
        "portón eléctrico": [r'porton electrico', r'portón eléctrico', r'acceso automatico'],
        "alberca": [r'mantenimiento de alberca', r'servicio de alberca'],
        "elevador": [r'elevador', r'ascensor'],
        "internet": [r'internet', r'wifi']
    }
    
    # Buscar menciones de servicios incluidos
    contexto_incluye = re.findall(r'(?:incluye|con|cubre)\s*(?::|los siguientes servicios)?([^\.]+)', texto)
    for contexto in contexto_incluye:
        for servicio, patrones_servicio in servicios.items():
            for patron in patrones_servicio:
                if re.search(patron, contexto):
                    if servicio not in resultado["incluye"]:
                        resultado["incluye"].append(servicio)
    
    return resultado

def obtener_puntos_interes(texto: str) -> List[Dict[str, str]]:
    """
    Detecta referencias a puntos de interés en el texto.
    """
    texto = texto.lower()
    
    # Diccionario de puntos de interés conocidos
    puntos_interes = {
        "comercial": {
            "centros_comerciales": [
                "galerías", "galerias", "averanda", "plaza cuernavaca",
                "forum", "city market", "walmart", "sams", "costco",
                "soriana", "comercial mexicana", "mega", "aurrera",
                "plaza diana", "plaza capiri"
            ],
            "mercados": [
                "mercado adolfo lópez mateos", "mercado alta vista",
                "mercado central", "mercado lagunilla"
            ]
        },
        "educativo": {
            "universidades": [
                "uaem", "universidad autónoma", "tec de monterrey",
                "tecnológico de monterrey", "uninter", "univac",
                "universidad latina", "universidad americana",
                "universidad lasalle", "lasalle", "universidad del valle"
            ],
            "escuelas": [
                "boston", "williams", "williams college", "harkness",
                "colegio williams", "colegio boston", "montessori",
                "colegio montessori", "colegio morelos"
            ]
        },
        "salud": {
            "hospitales": [
                "hospital henri dunant", "henri dunant", "hospital morelos",
                "sanatorio morelos", "hospital san diego", "imss",
                "issste", "cruz roja", "hospital inovamed", "inovamed",
                "hospital medsur", "medsur"
            ],
            "farmacias": [
                "farmacia guadalajara", "farmacias del ahorro",
                "farmacia del ahorro", "similares"
            ]
        },
        "transporte": {
            "avenidas": [
                "plan de ayala", "diana", "morelos", "cuauhnahuac",
                "universidad", "río mayo", "teopanzolco", "vicente guerrero",
                "emiliano zapata", "álvaro obregón", "san diego"
            ],
            "terminales": [
                "terminal de autobuses", "central camionera",
                "pullman de morelos"
            ]
        },
        "recreativo": {
            "parques": [
                "parque alameda", "alameda", "parque chapultepec",
                "chapultepec", "parque ecológico", "parque barranca",
                "barranca"
            ],
            "deportivo": [
                "unidad deportiva", "deportiva", "alberca olimpica",
                "gimnasio", "sports world", "sports plaza"
            ]
        }
    }
    
    referencias = []
    
    # Patrones de distancia
    patrones_distancia = [
        r'(?:a|en)\s+(\d+)\s*(?:min(?:utos)?|cuadras?|metros?|km)',
        r'(?:cerca|junto|próximo|proximo)\s+(?:de|a|al)',
        r'(?:sobre|frente\s+a|enfrente\s+de)',
        r'(?:a\s+(?:unos|pocos)\s+(?:pasos|metros|minutos))',
    ]
    
    # Buscar referencias a puntos de interés
    for categoria, subcategorias in puntos_interes.items():
        for subcategoria, lugares in subcategorias.items():
            for lugar in lugares:
                for patron_dist in patrones_distancia:
                    patron_completo = f"{patron_dist}.*?{lugar}"
                    if match := re.search(patron_completo, texto):
                        referencia = {
                            "tipo": categoria,
                            "subtipo": subcategoria,
                            "lugar": lugar,
                            "referencia_completa": match.group(0).strip()
                        }
                        # Extraer distancia si está especificada
                        if dist_match := re.search(r'(\d+)\s*(?:min(?:utos)?|cuadras?|metros?|km)', match.group(0)):
                            referencia["distancia"] = dist_match.group(0)
                        referencias.append(referencia)
                        break
                    # También buscar solo el lugar si está mencionado
                    elif lugar in texto:
                        referencias.append({
                            "tipo": categoria,
                            "subtipo": subcategoria,
                            "lugar": lugar,
                            "referencia_completa": f"cerca de {lugar}"
                        })
    
    return referencias

def procesar_propiedad(id_prop: str, datos: Dict) -> Dict:
    """
    Procesa una propiedad individual con la lógica mejorada.
    """
    if not isinstance(datos, dict):
        return None
    
    # Obtener descripción de múltiples campos posibles
    descripcion = ""
    campos_descripcion = ["description", "description_raw", "descripcion", "descripcion_raw", "desc", "texto", "message", "post_text"]
    for campo in campos_descripcion:
        if texto := str(datos.get(campo, "")).strip():
            descripcion = texto
            break
    
    # Si no hay descripción en ningún campo, retornar None
    if not descripcion:
        return None
    
    precio = str(datos.get("precio", "")).strip()
    location = str(datos.get("location", "")).strip()
    ciudad = str(datos.get("ciudad", "")).strip()
    link = str(datos.get("link", "")).strip()
    titulo = str(datos.get("titulo", "")).strip()
    
    # Verificar si es una propiedad
    if not es_propiedad(descripcion, titulo, precio, location):
        return None
    
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
    
    # Extraer mantenimiento
    mantenimiento = extraer_mantenimiento(descripcion)
    
    # Extraer puntos de interés
    puntos_interes = obtener_puntos_interes(descripcion)
    
    # Agregar puntos de interés a la ubicación
    if puntos_interes:
        ubicacion["puntos_interes"] = puntos_interes
    
    return {
        "id": id_prop,
        "link": link,
        "descripcion_original": descripcion,
        "ubicacion": ubicacion,
        "propiedad": {
            "tipo_propiedad": tipo_propiedad,
            "precio": precio,
            "mantenimiento": mantenimiento,
            "tipo_operacion": tipo_operacion,
            "moneda": "MXN"
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
        
        # Eliminar caracteres no alfanuméricos excepto espacios y puntuación básica
        texto = re.sub(r'[^\w\s.,;:()¿?¡!-]', '', texto)
        
        # Normalizar espacios múltiples
        texto = ' '.join(texto.split())
        
        return texto
    
    # Si no hay descripción ni título, no es una propiedad
    if not texto and not titulo:
        return False
    
    # Normalizar todos los textos de entrada
    texto = normalizar_texto(texto)
    titulo = normalizar_texto(titulo)
    precio = normalizar_texto(precio)
    location = normalizar_texto(location)
    
    # Palabras clave que indican una propiedad
    palabras_clave_propiedad = [
        'casa', 'depto', 'departamento', 'terreno', 'lote', 'venta', 'renta',
        'recamara', 'recamaras', 'habitacion', 'habitaciones', 'm2', 'metros',
        'fraccionamiento', 'privada', 'condominio', 'alberca', 'jardin',
        'estacionamiento', 'garage', 'cochera', 'bano', 'banos', 'cocina',
        'sala', 'comedor', 'escrituras', 'infonavit', 'fovissste', 'credito',
        'construccion', 'plusvalia', 'inversion', 'bienes raices', 'inmobiliaria',
        'propiedad', 'inmueble', 'local', 'oficina', 'bodega', 'edificio',
        'duplex', 'pent house', 'penthouse', 'roof garden', 'roofgarden'
    ]
    
    # Palabras que indican que NO es una propiedad
    palabras_no_propiedad = [
        'busco', 'solicito', 'necesito', 'urgente', 'compro', 'alguien vende',
        'alguien renta', 'quien vende', 'quien renta', 'donde rentan', 'donde venden'
    ]
    
    texto_completo = f"{texto} {titulo} {location}"
    
    # Si contiene palabras que indican que NO es una propiedad
    for palabra in palabras_no_propiedad:
        if palabra in texto_completo:
            return False
    
    # Contar palabras clave de propiedad encontradas
    palabras_encontradas = sum(1 for palabra in palabras_clave_propiedad if palabra in texto_completo)
    
    # Si encontramos al menos 2 palabras clave de propiedad
    if palabras_encontradas >= 2:
        return True
    
    # Si tiene dimensiones típicas de una propiedad
    patrones_dimension = [
        r'\d+\s*m2', r'\d+\s*metros?\s*cuadrados?',
        r'terreno\s*(?:de)?\s*\d+',
        r'construccion\s*(?:de)?\s*\d+',
        r'\d+\s*x\s*\d+\s*(?:m2|mts?)?'
    ]
    
    for patron in patrones_dimension:
        if re.search(patron, texto_completo, re.IGNORECASE):
            return True
    
    # Si tiene precio y al menos una palabra clave
    if precio and palabras_encontradas >= 1:
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
        
        # Contadores para campos de descripción
        campos_descripcion = {
            "description": 0,
            "description_raw": 0,
            "descripcion": 0,
            "descripcion_raw": 0,
            "desc": 0,
            "texto": 0,
            "message": 0,
            "post_text": 0
        }
        
        # Procesar propiedades
        propiedades_procesadas = []
        no_propiedades = []
        errores = []
        
        # Contadores para depuración
        total_items = len(propiedades_dict)
        items_sin_descripcion = 0
        items_sin_precio = 0
        
        # Muestra de los primeros items sin descripción
        ejemplos_sin_descripcion = []
        
        for id_prop, datos in propiedades_dict.items():
            try:
                if id_prop != "None":
                    # Obtener descripción de múltiples campos posibles
                    descripcion = ""
                    for campo in campos_descripcion.keys():
                        if texto := str(datos.get(campo, "")).strip():
                            descripcion = texto
                            campos_descripcion[campo] += 1
                            break
                    
                    # Verificar si tiene algún tipo de descripción
                    if not descripcion:
                        items_sin_descripcion += 1
                        if len(ejemplos_sin_descripcion) < 5:
                            ejemplos_sin_descripcion.append({
                                "id": id_prop,
                                "datos": datos
                            })
                    
                    # Verificar precio
                    if not str(datos.get("precio", "")).strip():
                        items_sin_precio += 1
                    
                    # Procesar la propiedad usando la descripción encontrada
                    if es_propiedad(descripcion, str(datos.get("titulo", "")), str(datos.get("precio", "")), str(datos.get("location", ""))):
                        resultado = procesar_propiedad(id_prop, datos)
                        if resultado:
                            propiedades_procesadas.append(resultado)
                    else:
                        no_propiedades.append({
                            "id": id_prop,
                            "link": datos.get("link", ""),
                            "titulo": datos.get("titulo", ""),
                            "descripcion": descripcion,
                            "precio": datos.get("precio", ""),
                            "location": datos.get("location", ""),
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
        
        print(f"\nProcesamiento completado:")
        print(f"- Total de items en repositorio: {total_items}")
        print(f"\nCampos de descripción encontrados:")
        for campo, cantidad in campos_descripcion.items():
            print(f"- {campo}: {cantidad} ({(cantidad/total_items)*100:.1f}%)")
        
        print(f"\nResumen:")
        print(f"- Items sin descripción: {items_sin_descripcion} ({(items_sin_descripcion/total_items)*100:.1f}%)")
        print(f"- Items sin precio: {items_sin_precio} ({(items_sin_precio/total_items)*100:.1f}%)")
        print(f"- Propiedades válidas procesadas: {len(propiedades_procesadas)} ({(len(propiedades_procesadas)/total_items)*100:.1f}%)")
        print(f"- Items que no son propiedades: {len(no_propiedades)} ({(len(no_propiedades)/total_items)*100:.1f}%)")
        print(f"- Errores encontrados: {len(errores)}")
        
        if ejemplos_sin_descripcion:
            print("\nEjemplos de items sin descripción:")
            for ejemplo in ejemplos_sin_descripcion:
                print(f"\nID: {ejemplo['id']}")
                print("Datos disponibles:")
                for k, v in ejemplo['datos'].items():
                    print(f"- {k}: {v}")
        
    except Exception as e:
        print(f"Error durante el procesamiento: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    procesar_archivo() 