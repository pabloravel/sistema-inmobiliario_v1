#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple, Union
from pathlib import Path

# Constantes para validación
RANGOS_PRECIO = {
    "venta": {
        "min": 100_000,  # 100 mil pesos
        "max": 50_000_000,  # 50 millones
        "sospechoso_bajo": {
            "casa": 800_000,  # 800 mil para casas
            "departamento": 600_000,  # 600 mil para departamentos
            "terreno": 300_000,  # 300 mil para terrenos
            "local": 500_000,  # 500 mil para locales
            "oficina": 700_000,  # 700 mil para oficinas
            "otro": 100_000  # 100 mil para otros
        },
        "sospechoso_alto": {
            "casa": 15_000_000,  # 15 millones para casas
            "departamento": 10_000_000,  # 10 millones para departamentos
            "terreno": 8_000_000,  # 8 millones para terrenos
            "local": 12_000_000,  # 12 millones para locales
            "oficina": 10_000_000,  # 10 millones para oficinas
            "otro": 5_000_000  # 5 millones para otros
        }
    },
    "renta": {
        "min": 1_000,  # mil pesos
        "max": 500_000,  # 500 mil pesos
        "sospechoso_bajo": {
            "casa": 5_000,  # 5 mil para casas
            "departamento": 4_000,  # 4 mil para departamentos
            "terreno": 3_000,  # 3 mil para terrenos
            "local": 4_000,  # 4 mil para locales
            "oficina": 5_000,  # 5 mil para oficinas
            "otro": 2_000  # 2 mil para otros
        },
        "sospechoso_alto": {
            "casa": 80_000,  # 80 mil para casas
            "departamento": 60_000,  # 60 mil para departamentos
            "terreno": 40_000,  # 40 mil para terrenos
            "local": 100_000,  # 100 mil para locales
            "oficina": 120_000,  # 120 mil para oficinas
            "otro": 50_000  # 50 mil para otros
        }
    }
}

RANGOS_SUPERFICIE = {
    "terreno": {
        "min": 50,  # metros cuadrados
        "max": 10_000,
        "sospechoso_bajo": {
            "casa": 90,  # 90m² para casas
            "departamento": 40,  # 40m² para departamentos
            "terreno": 100,  # 100m² para terrenos
            "local": 30,  # 30m² para locales
            "oficina": 40,  # 40m² para oficinas
            "otro": 30  # 30m² para otros
        },
        "sospechoso_alto": {
            "casa": 2_000,  # 2000m² para casas
            "departamento": 500,  # 500m² para departamentos
            "terreno": 5_000,  # 5000m² para terrenos
            "local": 1_000,  # 1000m² para locales
            "oficina": 800,  # 800m² para oficinas
            "otro": 1_000  # 1000m² para otros
        }
    },
    "construccion": {
        "min": 30,
        "max": 5_000,
        "sospechoso_bajo": {
            "casa": 50,  # 50m² para casas
            "departamento": 35,  # 35m² para departamentos
            "local": 25,  # 25m² para locales
            "oficina": 30,  # 30m² para oficinas
            "otro": 20  # 20m² para otros
        },
        "sospechoso_alto": {
            "casa": 1_000,  # 1000m² para casas
            "departamento": 400,  # 400m² para departamentos
            "local": 500,  # 500m² para locales
            "oficina": 600,  # 600m² para oficinas
            "otro": 300  # 300m² para otros
        }
    }
}

# Estructura base de una propiedad
ESTRUCTURA_PROPIEDAD = {
    "id": "",
    "url": "",
    "titulo": "",
    "descripcion": {
        "texto_original": "",
        "texto_limpio": ""
    },
    "ubicacion": {
        "ciudad": "",
        "colonia": "",
        "calle": "",
        "estado": "Morelos",
        "referencias": [],
        "coordenadas": {
            "latitud": None,
            "longitud": None
        }
    },
    "caracteristicas": {
        "tipo_propiedad": "",
        "tipo_operacion": "",
        "recamaras": 0,
        "banos": 0,
        "medios_banos": 0,
        "estacionamientos": 0,
        "niveles": 0,
        "superficie_terreno": 0,
        "superficie_construccion": 0,
        "antiguedad": None,
        "estado_conservacion": "No especificado",
        "amueblado": False
    },
    "precios": {
        "valor": 0.0,
        "moneda": "MXN",
        "tipo": "",
        "texto_original": "",
        "mantenimiento": 0.0,
        "incluye_mantenimiento": False
    },
    "amenidades": [],
    "estado_legal": {
        "escrituras": False,
        "predial": False,
        "servicios_pagados": False,
        "libre_gravamen": False,
        "cesion_derechos": False
    },
    "vendedor": {
        "nombre": "",
        "tipo": "desconocido",  # particular, inmobiliaria
        "perfil": ""
    },
    "metadata": {
        "fecha_extraccion": "",
        "ultima_actualizacion": "",
        "fuente": "facebook_marketplace",
        "status_extraccion": "pendiente",
        "errores": []
    }
}

def normalizar_precio(precio: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza el formato del precio"""
    precio_norm = {
        "valor": 0,
        "valor_normalizado": 0.0,
        "moneda": "MXN",
        "es_valido": False,
        "error": None
    }
    
    # Si ya es un diccionario con la estructura correcta
    if isinstance(precio, dict):
        if precio.get("es_valido") and precio.get("valor_normalizado", 0) > 0:
            return precio
        valor_raw = precio.get("valor", "")
    else:
        valor_raw = str(precio)
    
    if not valor_raw:
        precio_norm["error"] = "Precio vacío"
        return precio_norm
    
    # Convertir a string y limpiar
    valor_str = str(valor_raw).lower().strip()
    valor_str = valor_str.replace("$", "").replace("mxn", "").replace("mx", "")
    valor_str = valor_str.replace("pesos", "").replace(" ", "")
    
    # Patrones de precio
    patrones = [
        # Millones
        (r'(\d+(?:[.,]\d+)?)\s*millones?', lambda x: float(x.replace(",",".")) * 1_000_000),
        # M o MM
        (r'(\d+(?:[.,]\d+)?)\s*mm?', lambda x: float(x.replace(",",".")) * 1_000_000),
        # K o mil
        (r'(\d+(?:[.,]\d+)?)\s*k', lambda x: float(x.replace(",",".")) * 1_000),
        (r'(\d+(?:[.,]\d+)?)\s*mil', lambda x: float(x.replace(",",".")) * 1_000),
        # Número normal con punto decimal
        (r'(\d+\.\d+)', float),
        # Número normal con coma decimal
        (r'(\d+,\d+)', lambda x: float(x.replace(",","."))),
        # Entero
        (r'(\d+)', int)
    ]
    
    # Intentar extraer valor numérico
    valor = None
    for patron, conversion in patrones:
        if match := re.search(patron, valor_str):
            try:
                valor = conversion(match.group(1))
                break
            except:
                continue
    
    if valor is None:
        precio_norm["error"] = "No se pudo extraer un valor numérico"
        return precio_norm
    
    # Validar rangos según tipo de operación
    precio_norm["valor"] = valor
    precio_norm["valor_normalizado"] = valor
    
    # Determinar tipo de operación por el monto
    if valor >= 100_000:  # 100 mil o más
        # Probablemente venta
        if valor < RANGOS_PRECIO["venta"]["min"]:
            precio_norm["error"] = f"Precio de venta sospechosamente bajo: ${valor:,.2f}"
        elif valor > RANGOS_PRECIO["venta"]["max"]:
            precio_norm["error"] = f"Precio de venta sospechosamente alto: ${valor:,.2f}"
        else:
            precio_norm["es_valido"] = True
    else:
        # Probablemente renta
        if valor < RANGOS_PRECIO["renta"]["min"]:
            precio_norm["error"] = f"Precio de renta sospechosamente bajo: ${valor:,.2f}"
        elif valor > RANGOS_PRECIO["renta"]["max"]:
            precio_norm["error"] = f"Precio de renta sospechosamente alto: ${valor:,.2f}"
        else:
            precio_norm["es_valido"] = True
    
    return precio_norm

def normalizar_ubicacion(ubicacion: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza el formato de ubicación"""
    if not isinstance(ubicacion, dict):
        ubicacion = {}
    
    return {
        "ciudad": ubicacion.get("ciudad", "").strip(),
        "colonia": ubicacion.get("colonia", "").strip(),
        "calle": ubicacion.get("calle", "").strip(),
        "estado": ubicacion.get("estado", "Morelos").strip(),
        "referencias": ubicacion.get("referencias", []),
        "coordenadas": {
            "latitud": ubicacion.get("coordenadas", {}).get("latitud"),
            "longitud": ubicacion.get("coordenadas", {}).get("longitud")
        }
    }

def normalizar_caracteristicas(caract: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza las características de la propiedad"""
    if not isinstance(caract, dict):
        caract = {}
    
    # Convertir valores a tipos correctos
    return {
        "tipo_propiedad": str(caract.get("tipo_propiedad", "")),
        "tipo_operacion": str(caract.get("tipo_operacion", "")),
        "recamaras": int(caract.get("recamaras", 0) or 0),
        "banos": float(caract.get("banos", 0) or 0),
        "medios_banos": float(caract.get("medios_banos", 0) or 0),
        "estacionamientos": int(caract.get("estacionamientos", 0) or 0),
        "niveles": int(caract.get("niveles", 0) or 0),
        "superficie_terreno": int(caract.get("superficie_terreno", 0) or 0),
        "superficie_construccion": int(caract.get("superficie_construccion", 0) or 0),
        "antiguedad": str(caract.get("antiguedad", "")),
        "estado_conservacion": str(caract.get("estado_conservacion", "No especificado")),
        "amueblado": bool(caract.get("amueblado", False))
    }

def normalizar_amenidades(amenidades: Any) -> List[str]:
    """Normaliza las amenidades a una lista de strings"""
    if isinstance(amenidades, dict):
        # Convertir de formato booleano a lista
        return [k for k, v in amenidades.items() if v is True]
    elif isinstance(amenidades, list):
        return [str(a).strip() for a in amenidades if a]
    return []

def normalizar_estado_legal(legal: Dict[str, Any]) -> Dict[str, bool]:
    """Normaliza el estado legal de la propiedad"""
    if not isinstance(legal, dict):
        legal = {}
    
    return {
        "escrituras": bool(legal.get("escrituras", False)),
        "predial": bool(legal.get("predial", False)),
        "servicios_pagados": bool(legal.get("servicios_pagados", False)),
        "libre_gravamen": bool(legal.get("libre_gravamen", False)),
        "cesion_derechos": bool(legal.get("cesion_derechos", False))
    }

def normalizar_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza la metadata de la propiedad"""
    if not isinstance(metadata, dict):
        metadata = {}
    
    vendedor = metadata.get("vendedor", {})
    if not isinstance(vendedor, dict):
        vendedor = {}
    
    return {
        "vendedor": {
            "nombre": str(vendedor.get("nombre", "")),
            "perfil": str(vendedor.get("perfil", "")),
            "tipo": str(vendedor.get("tipo", "desconocido"))
        },
        "estado_listado": str(metadata.get("estado_listado", "disponible")),
        "ultima_actualizacion": str(metadata.get("ultima_actualizacion", datetime.now().isoformat())),
        "fecha_extraccion": str(metadata.get("fecha_extraccion", datetime.now().isoformat())),
        "fuente": str(metadata.get("fuente", "facebook_marketplace")),
        "status_extraccion": str(metadata.get("status_extraccion", "pendiente")),
        "errores": list(map(str, metadata.get("errores", [])))
    }

def normalizar_descripcion(descripcion: Any) -> Dict[str, str]:
    """Normaliza el formato de la descripción"""
    if isinstance(descripcion, dict):
        return {
            "texto_original": str(descripcion.get("texto_original", "")),
            "texto_limpio": str(descripcion.get("texto_limpio", ""))
        }
    elif isinstance(descripcion, str):
        return {
            "texto_original": descripcion,
            "texto_limpio": re.sub(r'\s+', ' ', descripcion).strip()
        }
    return {
        "texto_original": "",
        "texto_limpio": ""
    }

def extraer_info_descripcion(texto: str) -> Dict[str, Any]:
    """Extrae información relevante de la descripción"""
    info = {
        "tipo_operacion": "",
        "tipo_propiedad": "",
        "metros_terreno": 0,
        "metros_construccion": 0,
        "recamaras": 0,
        "banos": 0,
        "estacionamiento": 0,
        "niveles": 0,
        "amenidades": [],
        "estado_legal": {
            "escrituras": False,
            "cesion_derechos": False,
            "creditos": False,
            "constancia_posesion": False
        }
    }
    
    if not texto:
        return info
    
    texto = texto.lower()
    
    # 1. Detectar tipo de operación
    if any(x in texto for x in ["venta", "vendo", "se vende", "en venta"]):
        info["tipo_operacion"] = "venta"
    elif any(x in texto for x in ["renta", "rento", "se renta", "en renta", "alquiler", "alquilo"]):
        info["tipo_operacion"] = "renta"
    
    # 2. Detectar tipo de propiedad
    tipos_prop = {
        "casa": ["casa", "residencia", "chalet"],
        "departamento": ["departamento", "depto", "dpto", "apartamento", "apto"],
        "terreno": ["terreno", "lote", "predio"],
        "local": ["local", "comercial", "negocio"],
        "oficina": ["oficina", "despacho"],
        "bodega": ["bodega", "almacén", "nave industrial"]
    }
    
    for tipo, palabras in tipos_prop.items():
        if any(palabra in texto for palabra in palabras):
            info["tipo_propiedad"] = tipo
            break
    
    # 3. Extraer superficies
    # Patrones para metros cuadrados
    patrones_m2 = [
        # Terreno
        (r'terreno\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)', "metros_terreno"),
        (r'(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)\s*(?:de\s*)?terreno', "metros_terreno"),
        # Construcción
        (r'construccion\s*(?:de\s*)?(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)', "metros_construccion"),
        (r'(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)\s*(?:de\s*)?construccion', "metros_construccion"),
        # General (asignar a terreno si no hay otro)
        (r'(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metros?(?:\s*cuadrados?)?)', "metros_terreno")
    ]
    
    for patron, campo in patrones_m2:
        if match := re.search(patron, texto):
            valor = float(match.group(1).replace(",", "."))
            if valor > 0:
                info[campo] = valor
    
    # 4. Extraer características
    # Recámaras
    patrones_rec = [
        r'(\d+)\s*(?:recamaras?|recámaras?|habitaciones?|cuartos?|dormitorios?)',
        r'(?:recamaras?|recámaras?|habitaciones?|cuartos?|dormitorios?)\s*(\d+)'
    ]
    for patron in patrones_rec:
        if match := re.search(patron, texto):
            info["recamaras"] = int(match.group(1))
            break
    
    # Baños
    patrones_banos = [
        r'(\d+)\s*(?:baños?|sanitarios?|wc)',
        r'(?:baños?|sanitarios?|wc)\s*(\d+)'
    ]
    for patron in patrones_banos:
        if match := re.search(patron, texto):
            info["banos"] = int(match.group(1))
            break
    
    # Estacionamiento
    patrones_est = [
        r'(\d+)\s*(?:cajones?|lugares?|espacios?)\s*(?:de\s*)?estacionamiento',
        r'estacionamiento\s*(?:para|de)?\s*(\d+)\s*(?:autos?|coches?|carros?)',
        r'(\d+)\s*(?:autos?|coches?|carros?)\s*(?:de\s*)?estacionamiento'
    ]
    for patron in patrones_est:
        if match := re.search(patron, texto):
            info["estacionamiento"] = int(match.group(1))
            break
    
    # Niveles
    patrones_niv = [
        r'(\d+)\s*(?:pisos?|niveles?|plantas?)',
        r'(?:pisos?|niveles?|plantas?)\s*(\d+)'
    ]
    for patron in patrones_niv:
        if match := re.search(patron, texto):
            info["niveles"] = int(match.group(1))
            break
    
    # 5. Detectar amenidades
    amenidades_buscar = {
        "alberca": ["alberca", "piscina"],
        "jardin": ["jardin", "jardín", "área verde"],
        "seguridad": ["seguridad", "vigilancia", "privada"],
        "gimnasio": ["gimnasio", "gym"],
        "estacionamiento_techado": ["estacionamiento techado", "cochera techada"],
        "aire_acondicionado": ["aire acondicionado", "clima"],
        "amueblado": ["amueblado", "equipado"],
        "terraza": ["terraza", "balcón"],
        "area_lavado": ["área de lavado", "lavandería"],
        "bodega": ["bodega", "storage"]
    }
    
    for amenidad, palabras in amenidades_buscar.items():
        if any(palabra in texto for palabra in palabras):
            info["amenidades"].append(amenidad)
    
    # 6. Detectar estado legal
    if any(x in texto for x in ["escrituras", "escriturado"]):
        info["estado_legal"]["escrituras"] = True
    if any(x in texto for x in ["cesión", "cesion", "derechos"]):
        info["estado_legal"]["cesion_derechos"] = True
    if any(x in texto for x in ["crédito", "credito", "infonavit", "fovissste"]):
        info["estado_legal"]["creditos"] = True
    if any(x in texto for x in ["posesión", "posesion", "constancia"]):
        info["estado_legal"]["constancia_posesion"] = True
    
    return info

def extraer_ubicacion(texto: str) -> Dict[str, Any]:
    """Extrae información de ubicación del texto"""
    info = {
        "colonia": "",
        "referencias": []
    }
    
    if not texto:
        return info
    
    texto = texto.lower()
    
    # Detectar colonia
    patrones_col = [
        r'(?:colonia|col\.|fraccionamiento|fracc\.|unidad\s+hab\.|residencial)\s+([a-zñáéíóúü\s]+)',
        r'en\s+(?:la\s+)?([a-zñáéíóúü\s]+?)(?:\s+(?:cerca|junto|frente))?'
    ]
    
    for patron in patrones_col:
        if match := re.search(patron, texto):
            colonia = match.group(1).strip()
            if len(colonia) > 3:  # Evitar matches muy cortos
                info["colonia"] = colonia
                break
    
    # Detectar referencias
    referencias_buscar = [
        r'cerca\s+de\s+([^,\.]+)',
        r'junto\s+a\s+([^,\.]+)',
        r'frente\s+a\s+([^,\.]+)',
        r'a\s+(?:un|dos|tres|cuatro|cinco)\s+(?:minutos?|cuadras?)\s+de\s+([^,\.]+)'
    ]
    
    for patron in referencias_buscar:
        if matches := re.finditer(patron, texto):
            for match in matches:
                referencia = match.group(1).strip()
                if len(referencia) > 3:  # Evitar referencias muy cortas
                    info["referencias"].append(referencia)
    
    return info

def validar_y_corregir_propiedad(propiedad: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Valida y corrige una propiedad, retorna (propiedad_corregida, errores)"""
    errores = []
    advertencias = []
    
    # 1. Validar campos requeridos
    campos_requeridos = ["id", "link", "titulo", "precio"]
    for campo in campos_requeridos:
        if not propiedad.get(campo):
            errores.append(f"Falta el campo requerido: {campo}")
    
    # Si faltan campos críticos, retornar temprano
    if errores:
        propiedad["metadata"]["errores"] = errores
        propiedad["metadata"]["advertencias"] = advertencias
        propiedad["metadata"]["status"] = "error"
        return propiedad, errores
    
    # 2. Normalizar precio
    precio_norm = normalizar_precio(propiedad["precio"])
    propiedad["precio"] = precio_norm
    if not precio_norm["es_valido"]:
        errores.append(f"Precio no válido: {precio_norm['error']}")
    
    # 3. Extraer tipo de operación y propiedad de la descripción
    info_descripcion = extraer_info_descripcion(propiedad["descripcion"])
    
    # 4. Validar y corregir tipo de operación
    tipo_op = info_descripcion.get("tipo_operacion", "").lower()
    if tipo_op in ["venta", "renta"]:
        propiedad["caracteristicas"]["tipo_operacion"] = tipo_op
    else:
        # Intentar inferir del precio
        if precio_norm["es_valido"]:
            if precio_norm["valor_normalizado"] >= 1_000_000:  # 1 millón o más
                propiedad["caracteristicas"]["tipo_operacion"] = "venta"
            elif precio_norm["valor_normalizado"] <= 100_000:  # 100 mil o menos
                propiedad["caracteristicas"]["tipo_operacion"] = "renta"
            else:
                advertencias.append("No se pudo determinar el tipo de operación")
    
    # 5. Validar y corregir tipo de propiedad
    tipo_prop = info_descripcion.get("tipo_propiedad", "").lower()
    tipos_validos = ["casa", "departamento", "terreno", "local", "oficina", "bodega"]
    if tipo_prop in tipos_validos:
        propiedad["caracteristicas"]["tipo_propiedad"] = tipo_prop
    else:
        # Buscar en título y descripción
        texto_completo = f"{propiedad['titulo']} {propiedad['descripcion']}".lower()
        for tipo in tipos_validos:
            if tipo in texto_completo:
                propiedad["caracteristicas"]["tipo_propiedad"] = tipo
                break
        else:
            advertencias.append("No se pudo determinar el tipo de propiedad")
    
    # 6. Validar y corregir superficies
    if info_descripcion.get("metros_terreno"):
        propiedad["caracteristicas"]["metros_terreno"] = info_descripcion["metros_terreno"]
    if info_descripcion.get("metros_construccion"):
        propiedad["caracteristicas"]["metros_construccion"] = info_descripcion["metros_construccion"]
    
    # Validar rangos de superficie según tipo de propiedad
    tipo_prop = propiedad["caracteristicas"]["tipo_propiedad"]
    m2_terreno = propiedad["caracteristicas"]["metros_terreno"]
    m2_construccion = propiedad["caracteristicas"]["metros_construccion"]
    
    if tipo_prop == "casa":
        if m2_terreno > 0 and m2_terreno < 50:
            advertencias.append(f"Superficie de terreno sospechosamente baja para una casa: {m2_terreno}m²")
        if m2_construccion > 0 and m2_construccion < 30:
            advertencias.append(f"Superficie de construcción sospechosamente baja para una casa: {m2_construccion}m²")
    elif tipo_prop == "departamento":
        if m2_construccion > 0 and m2_construccion < 25:
            advertencias.append(f"Superficie sospechosamente baja para un departamento: {m2_construccion}m²")
    elif tipo_prop == "terreno":
        if m2_terreno > 0 and m2_terreno < 100:
            advertencias.append(f"Superficie sospechosamente baja para un terreno: {m2_terreno}m²")
    
    # 7. Validar y corregir ubicación
    if not propiedad["ubicacion"]["ciudad"]:
        propiedad["ubicacion"]["ciudad"] = "cuernavaca"  # Ciudad por defecto
    
    # Extraer colonia y referencias de la descripción
    info_ubicacion = extraer_ubicacion(propiedad["descripcion"])
    if info_ubicacion.get("colonia"):
        propiedad["ubicacion"]["colonia"] = info_ubicacion["colonia"]
    if info_ubicacion.get("referencias"):
        propiedad["ubicacion"]["referencias"] = info_ubicacion["referencias"]
    
    # 8. Validar y corregir características adicionales
    if info_descripcion.get("recamaras"):
        propiedad["caracteristicas"]["recamaras"] = info_descripcion["recamaras"]
    if info_descripcion.get("banos"):
        propiedad["caracteristicas"]["banos"] = info_descripcion["banos"]
    if info_descripcion.get("estacionamiento"):
        propiedad["caracteristicas"]["estacionamiento"] = info_descripcion["estacionamiento"]
    if info_descripcion.get("niveles"):
        propiedad["caracteristicas"]["niveles"] = info_descripcion["niveles"]
    
    # 9. Validar y corregir amenidades
    if info_descripcion.get("amenidades"):
        propiedad["amenidades"] = info_descripcion["amenidades"]
    
    # 10. Validar y corregir estado legal
    if info_descripcion.get("estado_legal"):
        propiedad["estado_legal"].update(info_descripcion["estado_legal"])
    
    # 11. Actualizar metadata
    propiedad["metadata"]["errores"] = errores
    propiedad["metadata"]["advertencias"] = advertencias
    propiedad["metadata"]["status"] = "error" if errores else "validado"
    propiedad["metadata"]["ultima_actualizacion"] = datetime.now().isoformat()
    
    return propiedad, errores

def procesar_repositorio():
    """Procesa y corrige todo el repositorio de propiedades"""
    print("\n=== INICIO DE PROCESAMIENTO ===")
    
    # 1. Cargar links
    try:
        with open("resultados/links/repositorio_unico.json", "r", encoding="utf-8") as f:
            links_raw = json.load(f)
            
        # Normalizar formato de links
        links = []
        BASE_URL = "https://www.facebook.com"
        for link in links_raw:
            if isinstance(link, str):
                url = BASE_URL + link if link.startswith("/") else link
                pid = link.rstrip("/").split("/")[-1]
                links.append({
                    "id": pid,
                    "link": url,
                    "ciudad": "cuernavaca"  # Ciudad por defecto
                })
            elif isinstance(link, dict):
                url = link.get("link", "")
                url = BASE_URL + url if url.startswith("/") else url
                links.append({
                    "id": link.get("id", url.rstrip("/").split("/")[-1]),
                    "link": url,
                    "ciudad": link.get("ciudad", "cuernavaca").lower()
                })
        
        print(f"📊 Total de links cargados: {len(links)}")
    except Exception as e:
        print(f"❌ Error cargando links: {str(e)}")
        return
    
    # 2. Cargar repositorio actual
    try:
        with open("resultados/repositorio_propiedades.json", "r", encoding="utf-8") as f:
            repositorio = json.load(f)
        print(f"📊 Total de propiedades en repositorio: {len(repositorio)}")
    except:
        print("💾 Creando nuevo repositorio")
        repositorio = {}
    
    # 3. Crear backup
    backup_path = "resultados/repositorio_propiedades.bak.json"
    print(f"💾 Creando backup en {backup_path}")
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(repositorio, f, indent=2, ensure_ascii=False)
    
    # 4. Procesar cada propiedad
    stats = {
        "total": len(links),
        "procesadas": 0,
        "corregidas": 0,
        "errores": 0,
        "por_tipo_operacion": {},
        "por_tipo_propiedad": {},
        "errores_comunes": {}
    }
    
    for item in links:
        pid = item["id"]
        print(f"\nProcesando propiedad {pid}...")
        
        # Crear estructura base
        propiedad = {
            "id": pid,
            "link": item["link"],
            "titulo": "",
            "descripcion": "",
            "precio": {
                "valor": 0,
                "valor_normalizado": 0.0,
                "moneda": "MXN",
                "es_valido": False,
                "error": None
            },
            "ubicacion": {
                "ciudad": item["ciudad"],
                "colonia": "",
                "calle": "",
                "referencias": [],
                "coordenadas": {
                    "latitud": None,
                    "longitud": None
                }
            },
            "caracteristicas": {
                "tipo_propiedad": "otro",
                "tipo_operacion": "",
                "recamaras": 0,
                "banos": 0,
                "estacionamiento": 0,
                "metros_terreno": 0,
                "metros_construccion": 0,
                "niveles": 0,
                "antiguedad": None,
                "estado_conservacion": "No especificado"
            },
            "amenidades": [],
            "estado_legal": {
                "escrituras": False,
                "cesion_derechos": False,
                "creditos": False,
                "constancia_posesion": False
            },
            "vendedor": {
                "nombre": "",
                "tipo": "particular",
                "telefono": "",
                "correo": ""
            },
            "imagenes": {
                "portada": "",
                "galeria": []
            },
            "metadata": {
                "fecha_extraccion": datetime.now().isoformat(),
                "ultima_actualizacion": datetime.now().isoformat(),
                "fuente": "facebook_marketplace",
                "status": "pendiente",
                "errores": [],
                "advertencias": []
            }
        }
        
        # Validar y corregir
        propiedad_corregida, errores = validar_y_corregir_propiedad(propiedad)
        
        # Actualizar estadísticas
        stats["procesadas"] += 1
        if errores:
            stats["errores"] += 1
            print("❌ Errores encontrados:")
            for error in errores:
                print(f"   - {error}")
                stats["errores_comunes"][error] = stats["errores_comunes"].get(error, 0) + 1
        else:
            stats["corregidas"] += 1
            tipo_op = propiedad_corregida["caracteristicas"]["tipo_operacion"]
            tipo_prop = propiedad_corregida["caracteristicas"]["tipo_propiedad"]
            stats["por_tipo_operacion"][tipo_op] = stats["por_tipo_operacion"].get(tipo_op, 0) + 1
            stats["por_tipo_propiedad"][tipo_prop] = stats["por_tipo_propiedad"].get(tipo_prop, 0) + 1
        
        # Actualizar repositorio
        repositorio[pid] = propiedad_corregida
        
        # Guardar progreso cada 10 propiedades
        if stats["procesadas"] % 10 == 0:
            with open("resultados/repositorio_propiedades.json", "w", encoding="utf-8") as f:
                json.dump(repositorio, f, indent=2, ensure_ascii=False)
    
    # 5. Guardar repositorio final
    print("\n💾 Guardando repositorio corregido en resultados/repositorio_propiedades.json")
    with open("resultados/repositorio_propiedades.json", "w", encoding="utf-8") as f:
        json.dump(repositorio, f, indent=2, ensure_ascii=False)
    
    # 6. Guardar estadísticas
    with open("resultados/stats_correccion.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    
    # 7. Mostrar resumen
    print("\n=== RESUMEN DE CORRECCIONES ===")
    print(f"✓ Total de propiedades: {stats['total']}")
    print(f"✓ Propiedades corregidas: {stats['corregidas']} ({stats['corregidas']/stats['total']*100:.1f}%)")
    print(f"❌ Propiedades con errores: {stats['errores']}")
    
    print("\nPor tipo de operación:")
    for tipo, cantidad in stats["por_tipo_operacion"].items():
        print(f"  - {tipo}: {cantidad}/{stats['total']} ({cantidad/stats['total']*100:.1f}%)")
    
    print("\nPor tipo de propiedad:")
    for tipo, cantidad in stats["por_tipo_propiedad"].items():
        print(f"  - {tipo}: {cantidad}/{stats['total']} ({cantidad/stats['total']*100:.1f}%)")
    
    print("\nErrores más comunes:")
    for error, cantidad in sorted(stats["errores_comunes"].items(), key=lambda x: x[1], reverse=True):
        print(f"  - {error}: {cantidad} ({cantidad/stats['total']*100:.2f}%)")
    
    print("\n✓ Proceso completado. Estadísticas guardadas en stats_correccion.json")

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
    Extrae información de superficie de terreno y construcción del texto.
    Maneja diferentes unidades y formatos.
    """
    def convertir_a_m2(valor: float, unidad: str) -> int:
        """Convierte diferentes unidades a metros cuadrados"""
        unidad = unidad.lower().strip()
        if 'hectarea' in unidad or 'ha' in unidad:
            return int(valor * 10000)
        elif 'acre' in unidad:
            return int(valor * 4046.86)
        elif 'vara' in unidad:
            return int(valor * 0.698737)
        return int(valor)

    def extraer_numero(texto: str, patron: str) -> Tuple[float, str]:
        """Extrae un número y su unidad usando un patrón"""
        if match := re.search(patron, texto, re.I):
            try:
                numero = match.group(1).replace(',', '').replace(' ', '')
                if '.' in numero:
                    valor = float(numero)
                else:
                    valor = float(numero)
                unidad = match.group(2) if len(match.groups()) > 1 else 'm2'
                return valor, unidad
            except ValueError:
                pass
        return 0.0, ''

    texto = texto.lower()
    
    # Patrones mejorados para diferentes formatos y unidades
    patrones_terreno = [
        # Formatos específicos de terreno
        r'terreno\s*(?:de|con)?\s*(\d+[\d.,]*)\s*(m2|metros?|m²|hectareas?|ha|acres?|varas?)',
        r'(\d+[\d.,]*)\s*(m2|metros?|m²|hectareas?|ha|acres?|varas?)\s*(?:de)?\s*terreno',
        r'superficie\s*(?:de|del)?\s*terreno\s*(?:de|con)?\s*(\d+[\d.,]*)\s*(m2|metros?|m²|hectareas?|ha|acres?|varas?)',
        r'lote\s*(?:de|con)?\s*(\d+[\d.,]*)\s*(m2|metros?|m²|hectareas?|ha|acres?|varas?)',
        # Formatos generales que mencionan terreno
        r'(\d+[\d.,]*)\s*(m2|metros?|m²|hectareas?|ha|acres?|varas?)\s*(?:de)?\s*(?:terreno|lote|predio)',
    ]
    
    patrones_construccion = [
        # Formatos específicos de construcción
        r'construcci[óo]n\s*(?:de|con)?\s*(\d+[\d.,]*)\s*(m2|metros?|m²)',
        r'(\d+[\d.,]*)\s*(m2|metros?|m²)\s*(?:de)?\s*construcci[óo]n',
        r'superficie\s*(?:de)?\s*construcci[óo]n\s*(?:de|con)?\s*(\d+[\d.,]*)\s*(m2|metros?|m²)',
        r'construidos?\s*(?:de|con)?\s*(\d+[\d.,]*)\s*(m2|metros?|m²)',
        # Formatos generales que mencionan construcción
        r'(\d+[\d.,]*)\s*(m2|metros?|m²)\s*(?:de)?\s*(?:construidos?|construcci[óo]n)',
    ]
    
    # Extraer valores
    terreno = construccion = 0
    unidad_terreno = unidad_construccion = ''
    
    # Buscar terreno
    for patron in patrones_terreno:
        valor, unidad = extraer_numero(texto, patron)
        if valor > 0:
            terreno = convertir_a_m2(valor, unidad)
            unidad_terreno = unidad
            break
    
    # Buscar construcción
    for patron in patrones_construccion:
        valor, unidad = extraer_numero(texto, patron)
        if valor > 0:
            construccion = convertir_a_m2(valor, unidad)
            unidad_construccion = unidad
            break
    
    # Si solo hay un número con m2 y no se especifica si es terreno o construcción
    if terreno == 0 and construccion == 0:
        patron_general = r'(\d+[\d.,]*)\s*(m2|metros?|m²)'
        valor, unidad = extraer_numero(texto, patron_general)
        if valor > 0:
            # Si el valor es grande, probablemente es terreno
            if valor > 500:
                terreno = convertir_a_m2(valor, unidad)
            else:
                construccion = convertir_a_m2(valor, unidad)
    
    # Validaciones y correcciones
    if terreno > 0 and construccion > 0:
        # Si la construcción es mayor que el terreno, probablemente están invertidos
        if construccion > terreno and construccion > RANGOS_SUPERFICIE["construccion"]["max"]:
            terreno, construccion = construccion, terreno
    
    # Validar rangos
    if terreno > 0:
        if terreno < RANGOS_SUPERFICIE["terreno"]["min"]:
            terreno *= 100  # Convertir de otras unidades
        elif terreno > RANGOS_SUPERFICIE["terreno"]["max"]:
            terreno /= 100
    
    if construccion > 0:
        if construccion < RANGOS_SUPERFICIE["construccion"]["min"]:
            construccion *= 100
        elif construccion > RANGOS_SUPERFICIE["construccion"]["max"]:
            construccion /= 100
    
    return {
        "superficie_m2": int(terreno),
        "construccion_m2": int(construccion),
        "unidad_terreno": unidad_terreno,
        "unidad_construccion": unidad_construccion
    }

def extraer_amenidades(texto: str) -> Dict[str, bool]:
    """
    Extrae amenidades con patrones mejorados.
    """
    texto = texto.lower()
    
    amenidades = {
        "alberca": [r'\balberca\b', r'\bpiscina\b'],
        "jardin": [r'\bjard[ií]n\b', r'\b[aá]rea verde\b'],
        "terraza": [r'\bterraza\b', r'\bbalc[oó]n\b'],
        "estacionamiento": [r'\bestacionamiento\b', r'\bcochera\b', r'\bgarage?\b'],
        "seguridad": [r'\bseguridad\b', r'\bvigilancia\b', r'24/7', r'\bc[aá]maras\b'],
        "gimnasio": [r'\bgimnasio\b', r'\bgym\b'],
        "area_comun": [r'\b[aá]rea(?:s)? com[uú]n(?:es)?\b', r'\bsal[oó]n(?:es)?\b'],
        "juegos_infantiles": [r'\bjuegos infantiles\b', r'\b[aá]rea infantil\b'],
        "elevador": [r'\belevador\b', r'\bascensor\b'],
        "roof_garden": [r'\broof\s*garden\b', r'\bsky\s*garden\b'],
        "bodega": [r'\bbodega\b', r'\bstorage\b'],
        "cuarto_servicio": [r'\bcuarto de servicio\b', r'\bhabitaci[oó]n de servicio\b'],
        "cisterna": [r'\bcisterna\b', r'\btanque de agua\b'],
        "aire_acondicionado": [r'\baire acondicionado\b', r'\ba/?c\b', r'\bclima\b']
    }
    
    resultado = {}
    for amenidad, patrones in amenidades.items():
        resultado[amenidad] = any(re.search(patron, texto) for patron in patrones)
    
    return resultado

def extraer_legal(texto: str) -> Dict[str, bool]:
    """
    Extrae información legal de la propiedad.
    """
    texto = texto.lower()
    
    return {
        "escrituras": any(p in texto for p in [
            "escrituras", "escriturada", "título de propiedad"
        ]),
        "predial": any(p in texto for p in [
            "predial al día", "predial pagado", "predial corriente"
        ]),
        "servicios_pagados": any(p in texto for p in [
            "servicios al día", "servicios pagados", "servicios incluidos"
        ]),
        "libre_gravamen": any(p in texto for p in [
            "libre de gravamen", "sin gravamen", "limpio de gravamen"
        ]),
        "cesion_derechos": any(p in texto for p in [
            "cesión de derechos", "cesion de derechos", "traspaso"
        ])
    }

if __name__ == "__main__":
    procesar_repositorio() 