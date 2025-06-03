import json
import re
import traceback
from typing import Dict, Union, List, Any, Tuple

def normalizar_precio(texto: str) -> Tuple[float, str]:
    """
    Normaliza el precio y retorna el valor numérico y la moneda.
    """
    texto = texto.lower().replace(',', '').replace('$', '')
    valor = 0.0
    moneda = 'MXN'
    
    # Extraer números
    numeros = re.findall(r'\d+(?:\.\d+)?', texto)
    if numeros:
        valor = float(numeros[0])
        
        # Ajustar por mil/millón
        if 'mil' in texto:
            valor *= 1000
        elif 'mill' in texto:
            valor *= 1000000
    
    # Detectar moneda
    if 'usd' in texto or 'dolar' in texto or 'dólares' in texto:
        moneda = 'USD'
    
    return valor, moneda

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
    Extrae el tipo de propiedad del texto.
    """
    texto = texto.lower()
    
    tipos_propiedad = {
        "casa": [
            r"\bcasa(?:\s+en)?(?:\s+venta|renta)?\b",
            r"\bresidencia\b",
            r"\bchalet\b",
            r"\bvilla\b"
        ],
        "departamento": [
            r"\b(?:departamento|depto|dpto)(?:\s+en)?(?:\s+venta|renta)?\b",
            r"\bapartamento\b",
            r"\bflat\b",
            r"\bpent\s*house\b"
        ],
        "terreno": [
            r"\bterreno(?:\s+en)?(?:\s+venta)?\b",
            r"\blote\b",
            r"\bpredio\b",
            r"\bparcela\b"
        ],
        "local": [
            r"\blocal(?:\s+comercial)?\b",
            r"\bcomercio\b",
            r"\btienda\b",
            r"\boficina\b"
        ],
        "bodega": [
            r"\bbodega\b",
            r"\balmacén\b",
            r"\bgalera\b",
            r"\bnave\s+industrial\b"
        ],
        "edificio": [
            r"\bedificio(?:\s+completo)?\b",
            r"\binmueble(?:\s+completo)?\b",
            r"\bcomplejo\b"
        ]
    }
    
    # Buscar tipo de propiedad
    for tipo, patrones in tipos_propiedad.items():
        for patron in patrones:
            if re.search(patron, texto):
                return tipo
    
    return ""

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

def extraer_caracteristicas(texto: str) -> Dict[str, Union[str, int, float]]:
    """
    Extrae características de la propiedad como metros cuadrados, número de habitaciones, baños, etc.
    """
    caracteristicas = {
        "metros_totales": "",
        "metros_construidos": "",
        "habitaciones": "",
        "baños": "",
        "estacionamientos": "",
        "niveles": "",
        "edad": "",
        "orientacion": "",
        "estado_conservacion": ""
    }
    
    texto = texto.lower()
    
    # Patrones para metros cuadrados
    patrones_m2 = [
        r'(\d+(?:,\d+)?)\s*(?:m2|m²|metros\s*cuadrados?|mts2)',
        r'superficie\s*(?:de|:)?\s*(\d+(?:,\d+)?)',
        r'terreno\s*(?:de|:)?\s*(\d+(?:,\d+)?)'
    ]
    
    # Patrones para construcción
    patrones_construccion = [
        r'construccion\s*(?:de|:)?\s*(\d+(?:,\d+)?)',
        r'construidos?\s*(?:de|:)?\s*(\d+(?:,\d+)?)',
        r'(\d+(?:,\d+)?)\s*m2\s*(?:de)?\s*construccion'
    ]
    
    # Patrones para habitaciones
    patrones_habitaciones = [
        r'(\d+)\s*(?:habitacion|recamara|dormitorio|cuarto|alcoba)s?',
        r'(\d+)\s*(?:hab|rec)\b'
    ]
    
    # Patrones para baños
    patrones_baños = [
        r'(\d+(?:\.\d+)?)\s*(?:baño|wc|sanitario)s?(?:\s*completos?)?',
        r'(\d+(?:\.\d+)?)\s*(?:medio)s?\s*baño'
    ]
    
    # Patrones para estacionamientos
    patrones_estacionamiento = [
        r'(\d+)\s*(?:estacionamiento|cochera|garage|lugar|cajon)s?(?:\s*de\s*auto)?',
        r'estacionamiento\s*para\s*(\d+)'
    ]
    
    # Patrones para niveles
    patrones_niveles = [
        r'(\d+)\s*(?:nivel|piso|planta)s?',
        r'(\d+)\s*(?:story|floor)s?'
    ]
    
    # Patrones para edad
    patrones_edad = [
        r'(\d+)\s*(?:año)s?\s*(?:de\s*antiguedad|de\s*edad)',
        r'(?:construi(?:do|da))\s*(?:en|hace)\s*(\d+)',
        r'(?:edad|antiguedad):\s*(\d+)'
    ]
    
    # Buscar metros totales
    for patron in patrones_m2:
        if match := re.search(patron, texto):
            try:
                metros = float(match.group(1).replace(',', ''))
                if 20 <= metros <= 10000:  # Rango razonable
                    caracteristicas["metros_totales"] = metros
                    break
            except ValueError:
                continue
    
    # Buscar metros construidos
    for patron in patrones_construccion:
        if match := re.search(patron, texto):
            try:
                metros = float(match.group(1).replace(',', ''))
                if 20 <= metros <= 5000:  # Rango razonable
                    caracteristicas["metros_construidos"] = metros
                    break
            except ValueError:
                continue
    
    # Buscar habitaciones
    for patron in patrones_habitaciones:
        if match := re.search(patron, texto):
            try:
                habitaciones = int(match.group(1))
                if 1 <= habitaciones <= 10:  # Rango razonable
                    caracteristicas["habitaciones"] = habitaciones
                    break
            except ValueError:
                continue
    
    # Buscar baños
    for patron in patrones_baños:
        if match := re.search(patron, texto):
            try:
                baños = float(match.group(1))
                if 1 <= baños <= 10:  # Rango razonable
                    caracteristicas["baños"] = baños
                    break
            except ValueError:
                continue
    
    # Buscar estacionamientos
    for patron in patrones_estacionamiento:
        if match := re.search(patron, texto):
            try:
                estacionamientos = int(match.group(1))
                if 1 <= estacionamientos <= 10:  # Rango razonable
                    caracteristicas["estacionamientos"] = estacionamientos
                    break
            except ValueError:
                continue
    
    # Buscar niveles
    for patron in patrones_niveles:
        if match := re.search(patron, texto):
            try:
                niveles = int(match.group(1))
                if 1 <= niveles <= 50:  # Rango razonable
                    caracteristicas["niveles"] = niveles
                    break
            except ValueError:
                continue
    
    # Buscar edad
    for patron in patrones_edad:
        if match := re.search(patron, texto):
            try:
                edad = int(match.group(1))
                if 0 <= edad <= 100:  # Rango razonable
                    caracteristicas["edad"] = edad
                    break
            except ValueError:
                continue
    
    # Detectar orientación
    orientaciones = {
        'norte': r'\b(?:orientacion|vista)\s*(?:al)?\s*norte\b',
        'sur': r'\b(?:orientacion|vista)\s*(?:al)?\s*sur\b',
        'este': r'\b(?:orientacion|vista)\s*(?:al)?\s*este\b',
        'oeste': r'\b(?:orientacion|vista)\s*(?:al)?\s*oeste\b'
    }
    
    for orientacion, patron in orientaciones.items():
        if re.search(patron, texto):
            caracteristicas["orientacion"] = orientacion
            break
    
    # Detectar estado de conservación
    estados = {
        'excelente': r'\b(?:excelente|impecable|como\s*nuevo)\b',
        'bueno': r'\b(?:buen|bueno|bien\s*conservado)\b',
        'regular': r'\b(?:regular|para\s*remodelar)\b',
        'malo': r'\b(?:mal|malo|necesita\s*reparacion)\b'
    }
    
    for estado, patron in estados.items():
        if re.search(patron, texto):
            caracteristicas["estado_conservacion"] = estado
            break
    
    return caracteristicas

def extraer_amenidades(texto: str) -> List[str]:
    """
    Extrae amenidades y características adicionales de la propiedad.
    """
    texto = texto.lower()
    amenidades_detectadas = set()
    
    amenidades = {
        "seguridad": [
            r"seguridad\s+24\s*(?:hrs?|horas)",
            r"vigilancia",
            r"cámaras?(?:\s+de\s+seguridad)?",
            r"acceso\s+controlado",
            r"caseta\s+de\s+vigilancia"
        ],
        "areas_comunes": [
            r"(?:área|area)s?\s+(?:verde|común|comun)s?",
            r"jardín(?:es)?(?:\s+común(?:es)?)?",
            r"salón(?:es)?\s+(?:de\s+)?(?:fiestas?|usos?\s+múltiples?)",
            r"alberca|piscina",
            r"gimnasio|gym",
            r"juegos\s+infantiles",
            r"terraza(?:\s+común)?",
            r"roof\s*garden"
        ],
        "instalaciones": [
            r"aire\s+acondicionado",
            r"calefacción",
            r"cisterna",
            r"tanque(?:\s+de)?(?:\s+agua)?",
            r"instalaciones?\s+(?:eléctrica|hidráulica|gas)",
            r"paneles?\s+solares",
            r"sistema\s+(?:hidroneumático|de\s+riego)"
        ],
        "acabados": [
            r"piso(?:s)?\s+(?:de\s+)?(?:mármol|madera|cerámico|porcelanato)",
            r"ventanas?\s+(?:de\s+)?(?:aluminio|pvc)",
            r"cancel(?:es)?\s+(?:de\s+)?(?:aluminio|templado)",
            r"closets?\s+vestidor(?:es)?",
            r"cocina\s+integral",
            r"muebles\s+empotrados"
        ],
        "servicios": [
            r"internet(?:\s+de\s+alta\s+velocidad)?",
            r"tv(?:\s+por\s+cable|\s+satelital)?",
            r"línea(?:\s+telefónica)?",
            r"gas\s+(?:natural|estacionario)",
            r"todos\s+los\s+servicios"
        ]
    }
    
    for categoria, patrones in amenidades.items():
        for patron in patrones:
            if re.search(patron, texto):
                amenidades_detectadas.add(categoria)
    
    return sorted(list(amenidades_detectadas))

def extraer_legal(texto: str) -> Dict[str, bool]:
    """
    Extrae información legal y documentación de la propiedad.
    """
    texto = texto.lower()
    legal = {
        "escrituras": False,
        "predial": False,
        "agua": False,
        "luz": False,
        "sin_adeudos": False,
        "titulo_propiedad": False
    }
    
    patrones = {
        "escrituras": [
            r"escrituras?\s+(?:en\s+)?(?:regla|orden)",
            r"documentación\s+en\s+regla",
            r"papeles?\s+en\s+(?:regla|orden)"
        ],
        "predial": [
            r"predial\s+(?:al\s+)?(?:corriente|pagado|día)",
            r"impuestos?\s+(?:al\s+)?(?:corriente|pagado|día)"
        ],
        "agua": [
            r"(?:recibo|pago)\s+de\s+agua\s+(?:al\s+)?(?:corriente|pagado|día)",
            r"servicios?\s+de\s+agua\s+(?:pagado|incluido)"
        ],
        "luz": [
            r"(?:recibo|pago)\s+de\s+luz\s+(?:al\s+)?(?:corriente|pagado|día)",
            r"servicios?\s+de\s+luz\s+(?:pagado|incluido)"
        ],
        "sin_adeudos": [
            r"sin\s+adeudos",
            r"libre\s+de\s+gravamen",
            r"al\s+corriente\s+(?:en\s+)?(?:pagos|servicios)"
        ],
        "titulo_propiedad": [
            r"título\s+de\s+propiedad",
            r"documentos?\s+(?:de\s+)?propiedad",
            r"acreditación\s+de\s+propiedad"
        ]
    }
    
    for campo, lista_patrones in patrones.items():
        for patron in lista_patrones:
            if re.search(patron, texto):
                legal[campo] = True
                break
    
    return legal

def extraer_mantenimiento(texto: str) -> Dict[str, Union[float, bool]]:
    """
    Extrae información sobre mantenimiento y cuotas.
    """
    texto = texto.lower()
    mantenimiento = {
        "cuota_mensual": 0.0,
        "incluye_servicios": False,
        "incluye_seguridad": False,
        "incluye_limpieza": False
    }
    
    # Buscar cuota de mantenimiento
    patrones_cuota = [
        r"mantenimiento(?:\s+mensual)?\s*(?:de|por)?\s*\$?\s*([\d,\.]+)",
        r"cuota(?:\s+de)?\s*mantenimiento\s*(?:de|por)?\s*\$?\s*([\d,\.]+)",
        r"\$\s*([\d,\.]+)\s*(?:de|por)?\s*mantenimiento(?:\s+mensual)?"
    ]
    
    for patron in patrones_cuota:
        if match := re.search(patron, texto):
            try:
                valor = float(match.group(1).replace(',', ''))
                if 100 <= valor <= 20000:  # Rango razonable para cuota mensual
                    mantenimiento["cuota_mensual"] = valor
                    break
            except ValueError:
                continue
    
    # Buscar servicios incluidos
    if re.search(r"incluye\s+(?:todos\s+los\s+)?servicios", texto):
        mantenimiento["incluye_servicios"] = True
    
    if re.search(r"incluye\s+(?:seguridad|vigilancia)", texto):
        mantenimiento["incluye_seguridad"] = True
    
    if re.search(r"incluye\s+(?:limpieza|mantenimiento)", texto):
        mantenimiento["incluye_limpieza"] = True
    
    return mantenimiento

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
    # Repositorio completo de colonias conocidas
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
        'ahuatepec': ('Ahuatepec', 'Cuernavaca'),
        'santa maria': ('Santa Maria', 'Cuernavaca'),
        'santa maría': ('Santa Maria', 'Cuernavaca'),
        'chamilpa': ('Chamilpa', 'Cuernavaca'),
        'chipitlan': ('Chipitlan', 'Cuernavaca'),
        'palmira': ('Palmira', 'Cuernavaca'),
        'bellavista': ('Bellavista', 'Cuernavaca'),
        'acapantzingo': ('Acapantzingo', 'Cuernavaca'),
        'antonio barona': ('Antonio Barona', 'Cuernavaca'),
        'centro': ('Centro', 'Cuernavaca'),
        'jardín juárez': ('Jardin Juarez', 'Cuernavaca'),
        'jardin juarez': ('Jardin Juarez', 'Cuernavaca'),
        'guerrero': ('Guerrero', 'Cuernavaca'),
        'chapultepec': ('Chapultepec', 'Cuernavaca'),
        'provincias': ('Provincias', 'Cuernavaca'),
        'lomas de la selva': ('Lomas De La Selva', 'Cuernavaca'),
        'la selva': ('La Selva', 'Cuernavaca'),
        'san anton': ('San Anton', 'Cuernavaca'),
        'san jerónimo': ('San Jeronimo', 'Cuernavaca'),
        'san jeronimo': ('San Jeronimo', 'Cuernavaca'),
        'las aguilas': ('Las Aguilas', 'Cuernavaca'),
        'las águilas': ('Las Aguilas', 'Cuernavaca'),
        'campo verde': ('Campo Verde', 'Cuernavaca'),
        'tulipanes': ('Tulipanes', 'Cuernavaca'),
        'satelite': ('Satelite', 'Cuernavaca'),
        'satélite': ('Satelite', 'Cuernavaca'),
        
        # Nuevas colonias de Cuernavaca
        'lomas de ahuatlan': ('Lomas de Ahuatlan', 'Cuernavaca'),
        'jardines de reforma': ('Jardines de Reforma', 'Cuernavaca'),
        'san miguel acapantzingo': ('San Miguel Acapantzingo', 'Cuernavaca'),
        'san cristobal': ('San Cristobal', 'Cuernavaca'),
        'maravillas': ('Maravillas', 'Cuernavaca'),
        'lomas de cortés norte': ('Lomas de Cortes Norte', 'Cuernavaca'),
        'lomas de cortés sur': ('Lomas de Cortes Sur', 'Cuernavaca'),
        'jardines de cuernavaca': ('Jardines de Cuernavaca', 'Cuernavaca'),
        'la pradera': ('La Pradera', 'Cuernavaca'),
        'la herradura': ('La Herradura', 'Cuernavaca'),
        'lomas de la herradura': ('Lomas de la Herradura', 'Cuernavaca'),
        
        # Jiutepec
        'las fincas': ('Las Fincas', 'Jiutepec'),
        'tejalpa': ('Tejalpa', 'Jiutepec'),
        'lomas del pedregal': ('Lomas Del Pedregal', 'Jiutepec'),
        'pedregal': ('Pedregal', 'Jiutepec'),
        'civac': ('Civac', 'Jiutepec'),
        'ciudad industrial': ('Civac', 'Jiutepec'),
        'progreso': ('Progreso', 'Jiutepec'),
        'atlacomulco': ('Atlacomulco', 'Jiutepec'),
        'las fuentes': ('Las Fuentes', 'Jiutepec'),
        'la joya': ('La Joya', 'Jiutepec'),
        'independencia': ('Independencia', 'Jiutepec'),
        'centro jiutepec': ('Centro', 'Jiutepec'),
        'calera chica': ('Calera Chica', 'Jiutepec'),
        'la calera': ('La Calera', 'Jiutepec'),
        'jardines de jiutepec': ('Jardines De Jiutepec', 'Jiutepec'),
        'el paraiso': ('El Paraiso', 'Jiutepec'),
        'el paraíso': ('El Paraiso', 'Jiutepec'),
        'la mora': ('La Mora', 'Jiutepec'),
        'los arcos': ('Los Arcos', 'Jiutepec'),
        'el eden': ('El Eden', 'Jiutepec'),
        'el edén': ('El Eden', 'Jiutepec'),
        
        # Temixco
        'burgos': ('Burgos', 'Temixco'),
        'burgos bugambilias': ('Burgos Bugambilias', 'Temixco'),
        'lomas de cuernavaca': ('Lomas De Cuernavaca', 'Temixco'),
        'acatlipa': ('Acatlipa', 'Temixco'),
        'alta palmira': ('Alta Palmira', 'Temixco'),
        'azteca': ('Azteca', 'Temixco'),
        'centro temixco': ('Centro', 'Temixco'),
        'lomas del carril': ('Lomas Del Carril', 'Temixco'),
        'campo verde': ('Campo Verde', 'Temixco'),
        'los presidentes': ('Los Presidentes', 'Temixco'),
        'las animas': ('Las Animas', 'Temixco'),
        'las ánimas': ('Las Animas', 'Temixco'),
        'rubén jaramillo': ('Ruben Jaramillo', 'Temixco'),
        'ruben jaramillo': ('Ruben Jaramillo', 'Temixco'),
        'miguel hidalgo': ('Miguel Hidalgo', 'Temixco'),
        
        # Emiliano Zapata
        'san francisco': ('San Francisco', 'Emiliano Zapata'),
        'residencial encinos': ('Residencial Encinos', 'Emiliano Zapata'),
        'tezoyuca': ('Tezoyuca', 'Emiliano Zapata'),
        'paraiso country club': ('Paraiso Country Club', 'Emiliano Zapata'),
        'paraíso country club': ('Paraiso Country Club', 'Emiliano Zapata'),
        'club de golf': ('Club De Golf', 'Emiliano Zapata'),
        'centro zapata': ('Centro', 'Emiliano Zapata'),
        'el calvario': ('El Calvario', 'Emiliano Zapata'),
        'tepetzingo': ('Tepetzingo', 'Emiliano Zapata'),
        'las garzas': ('Las Garzas', 'Emiliano Zapata'),
        'las palmas': ('Las Palmas', 'Emiliano Zapata'),
        
        # Xochitepec
        'real del puente': ('Real Del Puente', 'Xochitepec'),
        'alpuyeca': ('Alpuyeca', 'Xochitepec'),
        'centro xochitepec': ('Centro', 'Xochitepec'),
        'las flores': ('Las Flores', 'Xochitepec'),
        'las rosas': ('Las Rosas', 'Xochitepec'),
        'las palmas': ('Las Palmas', 'Xochitepec'),
        'la cruz': ('La Cruz', 'Xochitepec'),
        'miguel hidalgo': ('Miguel Hidalgo', 'Xochitepec'),
        'loma bonita': ('Loma Bonita', 'Xochitepec'),
        
        # Yautepec
        'centro yautepec': ('Centro', 'Yautepec'),
        'oaxtepec': ('Oaxtepec', 'Yautepec'),
        'cocoyoc': ('Cocoyoc', 'Yautepec'),
        'itzamatitlan': ('Itzamatitlan', 'Yautepec'),
        'itzamatitlán': ('Itzamatitlan', 'Yautepec'),
        'los arcos': ('Los Arcos', 'Yautepec'),
        'jacarandas': ('Jacarandas', 'Yautepec'),
        
        # Tepoztlán
        'centro tepoztlan': ('Centro', 'Tepoztlan'),
        'santo domingo': ('Santo Domingo', 'Tepoztlan'),
        'santa catarina': ('Santa Catarina', 'Tepoztlan'),
        'amatlán': ('Amatlan', 'Tepoztlan'),
        'amatlan': ('Amatlan', 'Tepoztlan'),
        'santiago tepetlapa': ('Santiago Tepetlapa', 'Tepoztlan')
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

def extraer_ubicacion(texto: str) -> Dict[str, str]:
    """
    Extrae información de ubicación del texto, incluyendo ciudad, colonia, calle y referencias.
    """
    ubicacion = {
        "ciudad": "",
        "colonia": "",
        "calle": "",
        "referencias": "",
        "confianza_ciudad": 0.0
    }
    
    texto = texto.lower()
    
    # Ciudades conocidas con sus variantes y puntos de referencia
    ciudades = {
        "cuernavaca": {
            "nombres": [
                r"\bcuernavaca\b",
                r"\bcuerna\b",
                r"\bmorelos\b"
            ],
            "colonias": [
                "acapantzingo", "ahuatepec", "alameda", "altavista", "bellavista",
                "buenavista", "centro", "chapultepec", "delicias", "flores magón",
                "gualupita", "jacarandas", "la pradera", "las palmas", "lomas de cortés",
                "lomas de la selva", "ocotepec", "palmira", "reforma", "san antón",
                "san cristóbal", "santa maría", "tlaltenango", "vista hermosa"
            ],
            "referencias": [
                r"\bpalacio de cortés\b", r"\bcatedral\b", r"\bzócalo\b",
                r"\bjardin borda\b", r"\bplaza galerias\b", r"\bforum\b",
                r"\bavenida plan de ayala\b", r"\bavenida universidad\b",
                r"\bautopista del sol\b", r"\btepoztlán\b"
            ]
        },
        "jiutepec": {
            "nombres": [
                r"\bjiutepec\b",
                r"\bmorelos\b"
            ],
            "colonias": [
                "centro", "civac", "las fincas", "morelos", "progreso",
                "tejalpa", "tlahuapan", "vicente estrada cajigal"
            ],
            "referencias": [
                r"\bcivac\b", r"\bparque industrial\b", r"\bplaza cedros\b",
                r"\bavenida tejalpa\b", r"\bhacienda de cortés\b"
            ]
        },
        "temixco": {
            "nombres": [
                r"\btemixco\b",
                r"\bmorelos\b"
            ],
            "colonias": [
                "acatlipa", "azteca", "centro", "lomas del carril",
                "miguel hidalgo", "rubén jaramillo"
            ],
            "referencias": [
                r"\bex hacienda temixco\b", r"\bbalneario ex hacienda\b",
                r"\bpuente temixco\b", r"\bcarretera temixco\b"
            ]
        }
    }
    
    # Buscar ciudad con sistema de puntuación
    max_puntuacion = 0
    ciudad_detectada = ""
    
    for ciudad, datos in ciudades.items():
        puntuacion = 0
        evidencias = []
        
        # Buscar menciones directas de la ciudad
        for patron in datos["nombres"]:
            if re.search(patron, texto):
                puntuacion += 0.6
                evidencias.append(f"Mención directa: {patron}")
                break
        
        # Buscar colonias conocidas
        for colonia in datos["colonias"]:
            if colonia in texto:
                puntuacion += 0.4
                evidencias.append(f"Colonia conocida: {colonia}")
                ubicacion["colonia"] = colonia.title()
                break
        
        # Buscar referencias específicas
        for referencia in datos["referencias"]:
            if re.search(referencia, texto):
                puntuacion += 0.3
                evidencias.append(f"Referencia: {referencia}")
                if not ubicacion["referencias"]:
                    ubicacion["referencias"] = referencia
                break
        
        if puntuacion > max_puntuacion:
            max_puntuacion = puntuacion
            ciudad_detectada = ciudad
            ubicacion["confianza_ciudad"] = puntuacion
    
    if max_puntuacion >= 0.6:  # Umbral mínimo de confianza
        ubicacion["ciudad"] = ciudad_detectada.title()
    
    # Buscar calle
    patrones_calle = [
        r"(?:calle|av\.|avenida|boulevard|blvd\.|camino|carretera)\s+([a-zá-úñ\s]+(?:\s+#?\d+)?)",
        r"(?:ubicad[oa]|localizad[oa])\s+en\s+([a-zá-úñ\s]+(?:\s+#?\d+)?)",
        r"sobre\s+([a-zá-úñ\s]+(?:\s+#?\d+)?)"
    ]
    
    for patron in patrones_calle:
        if match := re.search(patron, texto):
            calle = match.group(1).strip()
            if 3 <= len(calle) <= 50:  # Validar longitud razonable
                ubicacion["calle"] = calle.title()
                break
    
    return ubicacion

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
    ubicacion = extraer_ubicacion(descripcion)
    
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
        traceback.print_exc()

def procesar_propiedades(repositorio_path: str = "resultados/repositorio_propiedades.json") -> None:
    """
    Procesa el repositorio de propiedades y extrae información estructurada.
    """
    try:
        # Cargar repositorio
        with open(repositorio_path, 'r', encoding='utf-8') as f:
            repositorio = json.load(f)
        
        # Verificar la estructura del repositorio
        if not isinstance(repositorio, dict):
            print("Error: El repositorio debe ser un diccionario")
            return
        
        propiedades_procesadas = []
        total_items = len(repositorio)
        items_sin_descripcion = 0
        items_sin_precio = 0
        items_no_propiedades = 0
        errores = 0
        
        # Estadísticas por ciudad y tipo de operación
        stats_ciudad = {}
        stats_operacion = {}
        
        # Procesar cada propiedad
        for id_propiedad, datos in repositorio.items():
            try:
                # Verificar que tengamos una descripción
                if not datos.get('descripcion'):
                    items_sin_descripcion += 1
                    continue
                
                descripcion = datos['descripcion']
                
                # Extraer información
                ubicacion = extraer_ubicacion(descripcion)
                precios = extraer_precios(descripcion)
                tipo_propiedad = extraer_tipo_propiedad(descripcion)
                caracteristicas = extraer_caracteristicas(descripcion)
                
                # Validar información mínima
                if not precios.get('precio_venta') and not precios.get('precio_renta'):
                    items_sin_precio += 1
                    continue
                
                if not tipo_propiedad or not ubicacion.get('ciudad'):
                    items_no_propiedades += 1
                    continue
                
                # Crear objeto de propiedad procesada
                propiedad = {
                    'id': id_propiedad,
                    'tipo_propiedad': tipo_propiedad,
                    'ubicacion': ubicacion,
                    'precios': precios,
                    'caracteristicas': caracteristicas,
                    'url': datos.get('url', ''),
                    'fecha_extraccion': datos.get('fecha_extraccion', '')
                }
                
                # Actualizar estadísticas
                ciudad = ubicacion.get('ciudad', 'No especificada')
                stats_ciudad[ciudad] = stats_ciudad.get(ciudad, 0) + 1
                
                tipo_op = precios.get('tipo_operacion', 'No especificado')
                stats_operacion[tipo_op] = stats_operacion.get(tipo_op, 0) + 1
                
                propiedades_procesadas.append(propiedad)
                
            except Exception as e:
                print(f"Error procesando item {id_propiedad}: {str(e)}")
                errores += 1
                continue
        
        # Guardar resultados
        with open('resultados/propiedades_procesadas.json', 'w', encoding='utf-8') as f:
            json.dump(propiedades_procesadas, f, ensure_ascii=False, indent=2)
        
        # Imprimir estadísticas
        print("\nProcesamiento completado:")
        print(f"- Total de items en repositorio: {total_items}")
        print(f"- Items sin descripción: {items_sin_descripcion}")
        print(f"- Items sin precio: {items_sin_precio}")
        print(f"- Propiedades válidas procesadas: {len(propiedades_procesadas)}")
        print(f"- Items que no son propiedades: {items_no_propiedades}")
        print(f"- Errores encontrados: {errores}")
        
        print("\nDistribución por ciudad:")
        for ciudad, cantidad in sorted(stats_ciudad.items(), key=lambda x: x[1], reverse=True):
            print(f"- {ciudad}: {cantidad} ({(cantidad/len(propiedades_procesadas)*100):.1f}%)")
        
        print("\nDistribución por tipo de operación:")
        for tipo, cantidad in sorted(stats_operacion.items(), key=lambda x: x[1], reverse=True):
            print(f"- {tipo}: {cantidad} ({(cantidad/len(propiedades_procesadas)*100):.1f}%)")
            
    except Exception as e:
        print(f"Error general: {str(e)}")
        traceback.print_exc()

def extraer_precios(texto: str) -> Dict[str, Union[str, float]]:
    """
    Extrae diferentes tipos de precios y costos del texto.
    """
    precios = {
        "precio_venta": "",
        "precio_renta": "",
        "precio_mantenimiento": "",
        "precio_m2": "",
        "tipo_operacion": "No especificado",
        "rango_precio": {
            "min": "",
            "max": ""
        }
    }
    
    texto = texto.lower()
    
    # Detectar tipo de operación primero
    if any(term in texto for term in [
        "venta", "vendo", "vendemos", "se vende", "precio de venta",
        "compra", "adquiere", "precio total"
    ]):
        precios["tipo_operacion"] = "venta"
    elif any(term in texto for term in [
        "renta", "arriendo", "alquiler", "se renta", "rento",
        "mensual", "al mes", "por mes"
    ]):
        precios["tipo_operacion"] = "renta"
    
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
                        precios["tipo_operacion"] = "venta"
                    elif tipo == "renta" and 3_000 <= valor <= 150_000:
                        precios["precio_renta"] = f"${valor:,.2f}"
                        precios["tipo_operacion"] = "renta"
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

if __name__ == "__main__":
    procesar_propiedades() 