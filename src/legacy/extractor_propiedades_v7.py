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
    texto = texto.replace('metros cuadrados', 'm2')  # Normalizar metros cuadrados
    texto = texto.replace('metros2', 'm2')  # Normalizar metros cuadrados
    texto = texto.replace('m²', 'm2')  # Normalizar metros cuadrados
    texto = texto.replace('terreno:', 'terreno ')  # Normalizar dos puntos
    texto = texto.replace('construccion:', 'construccion ')  # Normalizar dos puntos
    texto = texto.replace('superficie:', 'superficie ')  # Normalizar dos puntos
    texto = texto.replace('  ', ' ')  # Normalizar espacios dobles
    texto = texto.replace('✅', '')  # Eliminar emojis comunes
    texto = texto.replace('🏠', '')
    texto = texto.replace('📏', '')
    texto = texto.replace('•', '')
    texto = texto.replace('-', ' ')  # Convertir guiones en espacios
    
    # Patrones para superficie total mejorados
    superficie_patterns = [
        # Patrones de superficie explícita
        r'superficie:?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)',
        r'superficie\s*(?:del?\s*)?(?:terreno|lote):?\s*(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)\s*(?:de\s*)?(?:terreno|superficie|lote)',
        r'terreno:?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)',
        r'lote\s*(?:de)?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)',
        
        # Patrones de dimensiones (frente x fondo)
        r'(\d+(?:\.\d+)?)\s*(?:m|metros?)?\s*(?:de\s*)?frente\s*(?:por|x|\*)\s*(\d+(?:\.\d+)?)\s*(?:m|metros?)?\s*(?:de\s*)?fondo',
        r'(\d+(?:\.\d+)?)\s*(?:por|x|\*)\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)?',
        r'frente\s*(?:de)?\s*(\d+(?:\.\d+)?)\s*(?:por|x|\*)\s*(\d+(?:\.\d+)?)\s*(?:de\s*fondo)?',
        
        # Patrones simples de metros
        r'(\d+(?:\.\d+)?)\s*m2\b',
        r'(\d+(?:\.\d+)?)\s*metros?\s*cuadrados?',
        r'(\d+(?:\.\d+)?)\s*m²',
        
        # Patrones específicos de área
        r'área\s*(?:de|del?)?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?)',
        r'area\s*(?:de|del?)?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?)',
        
        # Patrones de medidas sueltas
        r'mide\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?)',
        r'son\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?)',
        
        # Patrones con emojis y símbolos
        r'📏\s*(?:sup|superficie)?:?\s*(\d+(?:\.\d+)?)',
        r'🏗️\s*(?:terreno|superficie):?\s*(\d+(?:\.\d+)?)',
        r'🔍\s*(?:terreno|superficie):?\s*(\d+(?:\.\d+)?)',
        
        # Patrones de números seguidos de unidades
        r'\b(\d+(?:\.\d+)?)\s*m(?:ts?)?2?\b',
        r'\b(\d+(?:\.\d+)?)\s*metros?\b',
        
        # Patrones con bullets o viñetas
        r'(?:•|-|✅)\s*(\d+(?:\.\d+)?)\s*(?:m2|metros?(?:\s*cuadrados?)?)',
        
        # Patrones con errores comunes
        r'(\d+(?:\.\d+)?)\s*(?:mts2|mt2|m2s)',
        r'(\d+(?:\.\d+)?)\s*(?:metros|mts)(?:\s*2)?',
        
        # Patrones de dimensiones con variaciones
        r'(\d+(?:\.\d+)?)\s*(?:de\s*)?frente\s*(?:y|con)\s*(\d+(?:\.\d+)?)\s*(?:de\s*)?fondo',
        r'(\d+(?:\.\d+)?)\s*(?:m|mts?|metros?)?\s*x\s*(\d+(?:\.\d+)?)',
        
        # Patrones con medidas en la misma línea
        r'terreno\s*(?:de)?\s*(\d+(?:\.\d+)?)\s*(?:y|con)?\s*construccion',
        r'(\d+(?:\.\d+)?)\s*(?:m2|mts2?|metros?)\s*(?:y|con)?\s*construccion'
    ]
    
    construccion_patterns = [
        # Patrones explícitos de construcción
        r'(?:área|area|superficie)\s*(?:de\s*)?construida:?\s*(\d+(?:\.\d+)?)',
        r'(?:área|area|superficie)\s*(?:de\s*)?construcción:?\s*(\d+(?:\.\d+)?)',
        r'construcción:?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?)',
        r'(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?)\s*(?:de)?\s*construcción',
        
        # Patrones de metros construidos
        r'(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?)\s*construidos?',
        r'construidos?:?\s*(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?)',
        
        # Patrones simples de construcción
        r'construccion\s*(?:de)?\s*(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*de\s*construccion',
        
        # Patrones específicos
        r'\b(\d+(?:\.\d+)?)\s*(?:m2|m²|metros?)\s*(?:de)?\s*(?:const|construcción)',
        r'const(?:ruidos?)?:?\s*(\d+(?:\.\d+)?)',
        r'área\s*construida:?\s*(\d+(?:\.\d+)?)',
        r'area\s*construida:?\s*(\d+(?:\.\d+)?)',
        
        # Patrones con emojis y símbolos
        r'🏗️\s*(?:construcción|const):?\s*(\d+(?:\.\d+)?)',
        r'🔨\s*(?:construcción|const):?\s*(\d+(?:\.\d+)?)',
        r'📏\s*(?:construcción|const):?\s*(\d+(?:\.\d+)?)',
        
        # Patrones con bullets o viñetas
        r'(?:•|-|✅)\s*(\d+(?:\.\d+)?)\s*(?:m2|metros?(?:\s*cuadrados?)?)\s*(?:de)?\s*(?:const|construccion)',
        
        # Patrones con errores comunes
        r'(\d+(?:\.\d+)?)\s*(?:mts2|mt2|m2s)\s*(?:de)?\s*(?:const|construccion)',
        r'(\d+(?:\.\d+)?)\s*(?:metros|mts)(?:\s*2)?\s*(?:de)?\s*(?:const|construccion)',
        
        # Patrones con medidas en la misma línea
        r'terreno\s*(?:de)?\s*\d+(?:\.\d+)?\s*(?:y|con)?\s*construccion\s*(?:de)?\s*(\d+(?:\.\d+)?)',
        r'\d+(?:\.\d+)?\s*(?:m2|mts2?|metros?)\s*(?:y|con)?\s*(\d+(?:\.\d+)?)\s*(?:de)?\s*construccion'
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
        numeros = re.findall(r'\b(\d+(?:\.\d+)?)\s*(?:m2|mts2?|metros?(?:\s*cuadrados?)?)\b', texto)
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
    # Repositorio expandido de colonias conocidas
    colonias_conocidas = {
        # Colonias existentes
        'lomas de cortes': ('Lomas De Cortes', 'Cuernavaca'),
        
        # Nuevas colonias
        'lomas de ahuatlan': ('Lomas de Ahuatlan', 'Cuernavaca'),
        'jardines de reforma': ('Jardines de Reforma', 'Cuernavaca'),
        'san miguel acapantzingo': ('San Miguel Acapantzingo', 'Cuernavaca'),
        'lomas de la selva': ('Lomas de la Selva', 'Cuernavaca'),
        'san cristobal': ('San Cristobal', 'Cuernavaca'),
        'maravillas': ('Maravillas', 'Cuernavaca'),
        'lomas de cortés norte': ('Lomas de Cortes Norte', 'Cuernavaca'),
        'lomas de cortés sur': ('Lomas de Cortes Sur', 'Cuernavaca'),
        'jardines de cuernavaca': ('Jardines de Cuernavaca', 'Cuernavaca'),
        'rancho cortés': ('Rancho Cortes', 'Cuernavaca'),
        'la pradera': ('La Pradera', 'Cuernavaca'),
        'la herradura': ('La Herradura', 'Cuernavaca'),
        'lomas de la herradura': ('Lomas de la Herradura', 'Cuernavaca'),
        
        # Nuevas colonias en Jiutepec
        'jardines de jiutepec': ('Jardines de Jiutepec', 'Jiutepec'),
        'centro jiutepec': ('Centro', 'Jiutepec'),
        'la joya': ('La Joya', 'Jiutepec'),
        'las fuentes': ('Las Fuentes', 'Jiutepec'),
        
        # Nuevas colonias en Temixco
        'burgos de temixco': ('Burgos', 'Temixco'),
        'lomas de cuernavaca': ('Lomas de Cuernavaca', 'Temixco'),
        'centro temixco': ('Centro', 'Temixco')
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
        # Cuernavaca
        'oxxo del capiri': ('El Capiri', 'Cuernavaca'),
        'oxxo capiri': ('El Capiri', 'Cuernavaca'),
        'capiri': ('El Capiri', 'Cuernavaca'),
        'el capiri': ('El Capiri', 'Cuernavaca'),
        'plaza capiri': ('El Capiri', 'Cuernavaca'),
        'galerias cuernavaca': ('Vista Hermosa', 'Cuernavaca'),
        'galerías cuernavaca': ('Vista Hermosa', 'Cuernavaca'),
        'averanda': ('Vista Hermosa', 'Cuernavaca'),
        'forum': ('Vista Hermosa', 'Cuernavaca'),
        'plaza cuernavaca': ('Vista Hermosa', 'Cuernavaca'),
        'walmart vista hermosa': ('Vista Hermosa', 'Cuernavaca'),
        'sams vista hermosa': ('Vista Hermosa', 'Cuernavaca'),
        'costco': ('Vista Hermosa', 'Cuernavaca'),
        'hospital henri dunant': ('Vista Hermosa', 'Cuernavaca'),
        'hospital morelos': ('Vista Hermosa', 'Cuernavaca'),
        'hospital san diego': ('Vista Hermosa', 'Cuernavaca'),
        'imss plan de ayala': ('Plan De Ayala', 'Cuernavaca'),
        'issste': ('Chapultepec', 'Cuernavaca'),
        'cruz roja': ('Centro', 'Cuernavaca'),
        'hospital inovamed': ('Reforma', 'Cuernavaca'),
        'hospital medsur': ('Reforma', 'Cuernavaca'),
        
        # Jiutepec
        'plaza civac': ('Civac', 'Jiutepec'),
        'parque industrial': ('Civac', 'Jiutepec'),
        'ciudad industrial': ('Civac', 'Jiutepec'),
        'industrial civac': ('Civac', 'Jiutepec'),
        'zona industrial': ('Civac', 'Jiutepec'),
        
        # Temixco
        'plaza solidaridad': ('Centro', 'Temixco'),
        'mercado solidaridad': ('Centro', 'Temixco'),
        'burgos': ('Burgos', 'Temixco'),
        
        # Emiliano Zapata
        'tezoyuca': ('Tezoyuca', 'Emiliano Zapata'),
        'club de golf': ('Paraiso Country Club', 'Emiliano Zapata'),
        'country club': ('Paraiso Country Club', 'Emiliano Zapata'),
        
        # Xochitepec
        'real del puente': ('Real Del Puente', 'Xochitepec'),
        'alpuyeca': ('Alpuyeca', 'Xochitepec')
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
    """
    texto_completo = f"{texto} {location} {ciudad}".lower()
    
    ubicacion = {
        "colonia": "",
        "calle": "",
        "estado": "",
        "ciudad": "",
        "zona": "",
        "ubicacion_referencia": "",
        "puntos_interes": []
    }
    
    # Detectar zona con patrones mejorados
    ubicacion["zona"] = obtener_zona_conocida(texto_completo)
    
    # Diccionario de ciudades de Morelos
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
        'tepoztlán': 'Tepoztlan',
        'zapata': 'Emiliano Zapata',
        'civac': 'Jiutepec',
        'tezoyuca': 'Emiliano Zapata',
        'tejalpa': 'Jiutepec',
        'progreso': 'Jiutepec',
        'atlacomulco': 'Jiutepec',
        'las fuentes': 'Jiutepec',
        'la joya': 'Jiutepec',
        'burgos': 'Temixco',
        'acatlipa': 'Temixco',
        'alta palmira': 'Temixco',
        'azteca': 'Temixco',
        'centro temixco': 'Temixco',
        'tezoyuca': 'Emiliano Zapata',
        'paraiso country club': 'Emiliano Zapata',
        'club de golf': 'Emiliano Zapata',
        'xochitepec centro': 'Xochitepec',
        'real del puente': 'Xochitepec',
        'alpuyeca': 'Xochitepec',
        'oaxtepec': 'Yautepec',
        'cocoyoc': 'Yautepec',
        'itzamatitlan': 'Yautepec',
        'itzamatitlán': 'Yautepec'
    }
    
    # Patrones mejorados para detectar ciudad
    patrones_ciudad = [
        # Patrones existentes
        r'(?:municipio|en)\s+(?:de\s+)?([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        r'ubicad[oa]\s+en\s+([a-zá-úñ\s]+?)(?:,|\.|$|\s+mor)',
        
        # Nuevos patrones
        r'(?:cerca|junto|próximo)\s+(?:a|de|al)\s+(?:centro\s+de\s+)?([a-zá-úñ\s]+?)(?:,|\.|$)',
        r'(?:en\s+la\s+zona\s+(?:de|del)\s+)?([a-zá-úñ\s]+?)(?:,|\.|$)',
        r'(?:ubicad[oa]\s+en\s+el\s+)?([a-zá-úñ\s]+?)(?:,|\.|$)',
        r'(?:sobre|frente\s+a)\s+(?:la\s+)?(?:avenida|calle)\s+[^,]+?,\s*([a-zá-úñ\s]+?)(?:,|\.|$)',
        r'(?:a\s+(?:unos|pocos)\s+minutos\s+de)\s+([a-zá-úñ\s]+?)(?:,|\.|$)'
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
    
    # Si se encontró una ciudad válida, asignarla
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
    
    # Patrones para referencias de ubicación mejorados
    patrones_referencia = [
        r'(?:a|en)\s+(?:\d+\s+)?(?:min(?:utos)?|cuadras?|pasos?|metros?|km)\s+(?:de|del|dela|a)\s+([^,\.\n]+)',
        r'(?:cerca|junto|próximo|proximo)\s+(?:de|a|al)\s+([^,\.\n]+)',
        r'(?:sobre|frente\s+a|enfrente\s+de|atrás\s+de|atras\s+de|a\s+espaldas\s+de)\s+([^,\.\n]+)',
        r'(?:esquina\s+con|cruce\s+con|entre)\s+([^,\.\n]+)',
        r'(?:a\s+la\s+altura\s+de)\s+([^,\.\n]+)',
        r'(?:en\s+la\s+zona\s+de)\s+([^,\.\n]+)',
        r'(?:zona|área|area)\s+(?:de|del|dela)\s+([^,\.\n]+)',
        # Nuevos patrones para referencias
        r'(?:ubicad[oa]\s+(?:en|sobre))\s+([^,\.\n]+)',
        r'(?:a\s+unos\s+pasos\s+de)\s+([^,\.\n]+)',
        r'(?:con\s+acceso\s+a)\s+([^,\.\n]+)',
        r'(?:cercano\s+a)\s+([^,\.\n]+)',
        r'(?:en\s+el\s+corazón\s+de)\s+([^,\.\n]+)',
        r'(?:dentro\s+de)\s+([^,\.\n]+)',
        r'(?:a\s+la\s+entrada\s+de)\s+([^,\.\n]+)',
        r'(?:salida\s+a)\s+([^,\.\n]+)'
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
    
    # Si se encontró una zona conocida pero no ciudad, inferir la ciudad
    if ubicacion["zona"] and not ubicacion["ciudad"]:
        zonas_por_ciudad = {
            "Zona Dorada": "Cuernavaca",
            "Zona Norte": "Cuernavaca",
            "Zona Sur": "Cuernavaca",
            "Zona Centro": "Cuernavaca",
            "Zona Este": "Cuernavaca",
            "Zona Oeste": "Cuernavaca"
        }
        if ubicacion["zona"] in zonas_por_ciudad:
            ubicacion["ciudad"] = zonas_por_ciudad[ubicacion["zona"]]
            ubicacion["estado"] = "Morelos"
    
    # Obtener puntos de interés
    ubicacion["puntos_interes"] = obtener_puntos_interes(texto_completo)
    
    # Si no se encontró ciudad pero hay puntos de interés, usar el primero que tenga ciudad asociada
    if not ubicacion["ciudad"] and ubicacion["puntos_interes"]:
        lugares_conocidos = {
            'galerías': 'Cuernavaca',
            'galerias': 'Cuernavaca',
            'averanda': 'Cuernavaca',
            'forum': 'Cuernavaca',
            'plaza cuernavaca': 'Cuernavaca',
            'walmart vista hermosa': 'Cuernavaca',
            'sams': 'Cuernavaca',
            'costco': 'Cuernavaca',
            'hospital henri dunant': 'Cuernavaca',
            'hospital morelos': 'Cuernavaca',
            'hospital san diego': 'Cuernavaca',
            'imss': 'Cuernavaca',
            'issste': 'Cuernavaca',
            'cruz roja': 'Cuernavaca',
            'civac': 'Jiutepec',
            'parque industrial': 'Jiutepec',
            'ciudad industrial': 'Jiutepec',
            'plaza solidaridad': 'Temixco',
            'burgos': 'Temixco',
            'club de golf': 'Emiliano Zapata',
            'country club': 'Emiliano Zapata',
            'real del puente': 'Xochitepec'
        }
        
        for punto in ubicacion["puntos_interes"]:
            lugar = punto["lugar"].lower()
            if lugar in lugares_conocidos:
                ubicacion["ciudad"] = lugares_conocidos[lugar]
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
            r'(?:cuota|pago|costo)\s*(?:de\s*)?mantenimiento\s*:?\s*\$?\s*([\d,\.]+)',
            r'mantenimiento\s*(?:mensual|anual)?\s*:?\s*\$?\s*([\d,\.]+)',
            r'incluye\s*mantenimiento\s*de\s*\$?\s*([\d,\.]+)'
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
            "venta": (6_000_000, 60_000_000),
            "renta": (20_000, 200_000)
        },
        "Zona Norte": {
            "venta": (3_000_000, 30_000_000),
            "renta": (12_000, 120_000)
        },
        "Zona Sur": {
            "venta": (2_000_000, 20_000_000),
            "renta": (8_000, 80_000)
        },
        "Zona Centro": {
            "venta": (3_500_000, 35_000_000),
            "renta": (15_000, 150_000)
        },
        "Zona Este": {
            "venta": (2_500_000, 25_000_000),
            "renta": (10_000, 100_000)
        },
        "Zona Oeste": {
            "venta": (2_800_000, 28_000_000),
            "renta": (12_000, 120_000)
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
    
    # Puntos de interés expandidos
    puntos_interes = {
        "comercial": {
            "centros_comerciales": [
                # Existentes
                "galerías", "galerias", "averanda",
                
                # Nuevos
                "plaza diana", "plaza capiri", "plaza cuernavaca",
                "forum cuernavaca", "city market", "superama",
                "plaza degollado", "plaza san diego"
            ],
            "mercados": [
                "mercado adolfo lópez mateos", "mercado alta vista",
                "mercado central", "mercado lagunilla",
                "mercado carolina", "mercado amatitlan"
            ]
        },
        "salud": {
            "hospitales": [
                # Existentes
                "hospital henri dunant", "hospital morelos",
                
                # Nuevos
                "hospital inovamed", "hospital medsur",
                "hospital parres", "clinica del imss",
                "issste chipitlan", "cruz roja morelos"
            ]
        },
        "educativo": {
            "universidades": [
                "uaem", "tec de monterrey", "uninter",
                "universidad latina", "universidad americana",
                "universidad lasalle", "universidad del valle",
                "upemor", "universidad politecnica"
            ]
        }
    }
    
    # Diccionario para almacenar referencias únicas
    referencias_unicas = {}
    
    # Patrones de distancia mejorados
    patrones_distancia = [
        r'(?:a|en)\s+(\d+)\s*(?:min(?:utos)?|cuadras?|metros?|km)',
        r'(?:cerca|junto|próximo|proximo)\s+(?:de|a|al)',
        r'(?:sobre|frente\s+a|enfrente\s+de)',
        r'(?:a\s+(?:unos|pocos)\s+(?:pasos|metros|minutos))',
        r'(?:a\s+(?:unos?|dos|tres|cuatro|cinco)\s+(?:min(?:utos)?|cuadras?))',
    ]
    
    # Buscar referencias a puntos de interés
    for categoria, subcategorias in puntos_interes.items():
        for subcategoria, lugares in subcategorias.items():
            for lugar in lugares:
                # Clave única para cada lugar
                lugar_key = f"{categoria}:{subcategoria}:{lugar}"
                
                # Si ya encontramos este lugar, continuamos
                if lugar_key in referencias_unicas:
                    continue
                
                mejor_referencia = None
                mejor_distancia = None
                
                # Buscar la mejor referencia para este lugar
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
                            
                            # Si encontramos una referencia con distancia, la usamos
                            mejor_referencia = referencia
                            mejor_distancia = dist_match.group(0)
                            break
                        else:
                            # Si no tiene distancia, solo la guardamos si no tenemos una mejor
                            if not mejor_referencia:
                                mejor_referencia = referencia
                
                # Si no encontramos referencia con patrón pero el lugar está mencionado
                if not mejor_referencia and lugar in texto:
                    mejor_referencia = {
                        "tipo": categoria,
                        "subtipo": subcategoria,
                        "lugar": lugar,
                        "referencia_completa": f"cerca de {lugar}"
                    }
                
                # Guardar la mejor referencia encontrada
                if mejor_referencia:
                    referencias_unicas[lugar_key] = mejor_referencia
    
    # Convertir el diccionario de referencias únicas a lista
    return list(referencias_unicas.values())

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