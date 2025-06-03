#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Catálogo de ciudades principales de Morelos
CIUDADES = {
    'cuernavaca': ['cuernavaca', 'cuerna', 'cuernavaca morelos'],
    'jiutepec': ['jiutepec', 'jiute', 'civac'],
    'temixco': ['temixco'],
    'emiliano zapata': ['emiliano zapata', 'zapata'],
    'xochitepec': ['xochitepec', 'xochi'],
    'yautepec': ['yautepec'],
    'tepoztlan': ['tepoztlan', 'tepoztlán', 'tepoz'],
    'cuautla': ['cuautla', 'cuautla morelos'],
    'jojutla': ['jojutla'],
    'zacatepec': ['zacatepec']
}

# Colonias principales por ciudad
COLONIAS = {
    'cuernavaca': [
        'acapantzingo', 'ahuatepec', 'alameda', 'altavista', 'analco', 'antonio barona', 'atlacomulco',
        'bellavista', 'benito juarez', 'buenavista', 'burgos', 'cantarranas', 'carolina',
        'centro', 'chapultepec', 'chipitlan', 'delicias', 'flores magon', 'gualupita',
        'jardines de cuernavaca', 'la pradera', 'la selva', 'las palmas',
        'lomas de cortés', 'lomas de la selva', 'lomas de tzompantle', 'los volcanes',
        'maravillas', 'miraval', 'ocotepec', 'palmira', 'rancho cortes', 'reforma',
        'san anton', 'san cristobal', 'san jeronimo', 'san miguel acapantzingo',
        'santa maria ahuacatitlan', 'tabachines', 'tetela del monte', 'tlaltenango',
        'vista hermosa', 'jardines de reforma', 'lomas de atzingo', 'las quintas'
    ],
    'jiutepec': [
        'civac', 'tejalpa', 'las fincas', 'calera chica', 'jardines de la hacienda',
        'insurgentes', 'la joya', 'morelos', 'otilio montaño', 'progreso', 'san jose',
        'tlahuapan', 'vicente guerrero', 'jardines de jiutepec', 'las aguilas'
    ],
    'temixco': [
        'acatlipa', 'azteca', 'burgos', 'las rosas', 'lomas del carril',
        'miguel hidalgo', 'morelos', 'rubén jaramillo', 'santa ursula'
    ]
}

# Puntos de referencia conocidos por ciudad
REFERENCIAS = {
    'cuernavaca': [
        'galeria', 'plaza cuernavaca', 'walmart', 'costco', 'sams club', 'mega comercial',
        'hospital henri dunant', 'hospital morelos', 'imss', 'issste', 'tec de monterrey',
        'universidad autonoma', 'uaem', 'forum', 'averanda', 'palacio de gobierno',
        'jardín morelos', 'jardín juarez', 'catedral', 'zócalo', 'plaza de armas',
        'jardín borda', 'casino de la selva', 'autopista del sol'
    ],
    'jiutepec': [
        'civac', 'parque industrial', 'nissan', 'unilever', 'baxter',
        'plaza jiutepec', 'tecnologico', 'ayuntamiento', 'centro comercial',
        'explanada jiutepec'
    ]
}

# Palabras clave que indican ubicación
KEYWORDS_UBICACION = [
    'ubicado en', 'ubicada en', 'localizado en', 'localizada en',
    'se encuentra en', 'situada en', 'situado en', 'dentro de',
    'en la zona de', 'en zona', 'cerca de', 'próximo a', 'proximo a',
    'a unos minutos de', 'a pasos de', 'junto a', 'frente a',
    'atrás de', 'atras de', 'a espaldas de', 'sobre', 'por la zona de'
]

# Palabras clave que indican características de la zona
KEYWORDS_ZONA = [
    'zona residencial', 'zona comercial', 'zona escolar', 'zona centro',
    'zona dorada', 'zona norte', 'zona sur', 'zona oriente', 'zona poniente',
    'fraccionamiento', 'privada', 'condominio', 'unidad habitacional',
    'colonia', 'barrio', 'pueblo', 'centro', 'periferia'
]

def normalizar_texto(texto):
    """Normaliza un texto para búsqueda en catálogos"""
    import re
    if not texto:
        return ""
    # Convertir a minúsculas y eliminar acentos
    texto = texto.lower()
    texto = re.sub(r'[áä]', 'a', texto)
    texto = re.sub(r'[éë]', 'e', texto)
    texto = re.sub(r'[íï]', 'i', texto)
    texto = re.sub(r'[óö]', 'o', texto)
    texto = re.sub(r'[úü]', 'u', texto)
    texto = re.sub(r'ñ', 'n', texto)
    # Eliminar caracteres especiales y espacios múltiples
    texto = re.sub(r'[^\w\s]', ' ', texto)
    texto = ' '.join(texto.split())
    return texto

def encontrar_ciudad(texto):
    """Encuentra la ciudad en el texto usando el catálogo"""
    texto = normalizar_texto(texto)
    for ciudad, variantes in CIUDADES.items():
        if any(v in texto for v in variantes):
            return ciudad
    return "cuernavaca"  # Por defecto

def encontrar_colonia(texto, ciudad="cuernavaca"):
    """Encuentra la colonia en el texto usando el catálogo"""
    texto = normalizar_texto(texto)
    # Primero buscar en las colonias de la ciudad específica
    if ciudad in COLONIAS:
        for colonia in COLONIAS[ciudad]:
            if colonia in texto:
                return colonia
    # Si no se encuentra, buscar en todas las colonias
    for colonias in COLONIAS.values():
        for colonia in colonias:
            if colonia in texto:
                return colonia
    return ""

def encontrar_referencias(texto, ciudad="cuernavaca"):
    """Encuentra puntos de referencia en el texto"""
    texto = normalizar_texto(texto)
    referencias = []
    
    # Buscar referencias del catálogo
    if ciudad in REFERENCIAS:
        for ref in REFERENCIAS[ciudad]:
            if ref in texto:
                referencias.append(ref)
    
    # Buscar patrones de referencia con palabras clave
    for keyword in KEYWORDS_UBICACION:
        if keyword in texto:
            idx = texto.find(keyword) + len(keyword)
            frase = texto[idx:idx+50].strip()  # Tomar 50 caracteres después
            if frase:
                referencias.append(f"{keyword} {frase}")
    
    return referencias 