#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from collections import Counter
import statistics

def normalizar_texto(texto):
    """
    Normaliza un texto eliminando caracteres especiales y convirtiendo a minúsculas.
    """
    if not texto or not isinstance(texto, str):
        return ""
    
    # Convertir a minúsculas y quitar espacios extras
    texto = texto.lower().strip()
    
    # Reemplazar caracteres especiales
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ü': 'u', 'ñ': 'n', 'à': 'a', 'è': 'e', 'ì': 'i',
        'ò': 'o', 'ù': 'u', 'ä': 'a', 'ë': 'e', 'ï': 'i',
        'ö': 'o', 'ü': 'u'
    }
    
    for old, new in replacements.items():
        texto = texto.replace(old, new)
    
    return texto

def analizar_calidad_campos(archivo):
    with open(archivo, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    propiedades = data.get('propiedades', [])
    total = len(propiedades)
    if total == 0:
        print("No hay propiedades para analizar")
        return
    
    print(f"\n=== ANÁLISIS DE CALIDAD DE DATOS ({total} propiedades) ===\n")
    
    # Contadores para campos principales
    tipos_operacion = Counter()
    precios_validos = 0
    precios = []
    ubicaciones_completas = 0
    caracteristicas_completas = 0
    
    # Contadores para características
    recamaras = []
    banos = []
    medio_banos = []
    superficie = []
    construccion = []
    estacionamientos = []
    niveles = []
    amenidades = Counter()
    seguridad = Counter()
    estados_conservacion = Counter()
    orientaciones = Counter()
    
    for prop in propiedades:
        # Tipo de operación
        tipo_op = prop.get('tipo_operacion', '')
        tipos_operacion[tipo_op] += 1
        
        # Precio
        if prop.get('precio_num', 0) > 0:
            precios_validos += 1
            precios.append(prop['precio_num'])
        
        # Ubicación
        ubicacion = prop.get('ubicacion', {})
        if ubicacion.get('colonia') or ubicacion.get('zona'):
            ubicaciones_completas += 1
            
        # Características
        caract = prop.get('caracteristicas', {})
        if any([caract.get('recamaras'), caract.get('banos'), 
                caract.get('superficie_m2'), caract.get('construccion_m2')]):
            caracteristicas_completas += 1
            
        if caract.get('recamaras'):
            recamaras.append(caract['recamaras'])
        if caract.get('banos'):
            banos.append(caract['banos'])
        if caract.get('medio_bano'):
            medio_banos.append(caract['medio_bano'])
        if caract.get('superficie_m2'):
            superficie.append(caract['superficie_m2'])
        if caract.get('construccion_m2'):
            construccion.append(caract['construccion_m2'])
        if caract.get('estacionamientos'):
            estacionamientos.append(caract['estacionamientos'])
        if caract.get('niveles'):
            niveles.append(caract['niveles'])
            
        # Amenidades y seguridad
        for amenidad in caract.get('amenidades', []):
            amenidad_norm = normalizar_texto(amenidad)
            amenidades[amenidad_norm] += 1
        for elemento in caract.get('seguridad', []):
            elemento_norm = normalizar_texto(elemento)
            seguridad[elemento_norm] += 1
            
        # Estado de conservación y orientación
        if estado := caract.get('estado_conservacion'):
            estados_conservacion[estado] += 1
        if orientacion := caract.get('orientacion'):
            orientaciones[orientacion] += 1
    
    # Imprimir resultados
    print("1. TIPOS DE OPERACIÓN:")
    for tipo, count in tipos_operacion.most_common():
        print(f"   {tipo}: {count} ({count/total*100:.1f}%)")
    
    print("\n2. PRECIOS:")
    print(f"   Propiedades con precio válido: {precios_validos} ({precios_validos/total*100:.1f}%)")
    if precios:
        print(f"   Precio promedio: ${statistics.mean(precios):,.2f}")
        print(f"   Precio mediana: ${statistics.median(precios):,.2f}")
        print(f"   Precio mínimo: ${min(precios):,.2f}")
        print(f"   Precio máximo: ${max(precios):,.2f}")
    
    print("\n3. UBICACIÓN:")
    print(f"   Propiedades con ubicación identificada: {ubicaciones_completas} ({ubicaciones_completas/total*100:.1f}%)")
    
    print("\n4. CARACTERÍSTICAS BÁSICAS:")
    print(f"   Propiedades con características: {caracteristicas_completas} ({caracteristicas_completas/total*100:.1f}%)")
    print(f"   - Con recámaras: {len(recamaras)} ({len(recamaras)/total*100:.1f}%)")
    if recamaras:
        print(f"     Promedio de recámaras: {statistics.mean(recamaras):.1f}")
    print(f"   - Con baños completos: {len(banos)} ({len(banos)/total*100:.1f}%)")
    if banos:
        print(f"     Promedio de baños: {statistics.mean(banos):.1f}")
    print(f"   - Con medio baño: {len(medio_banos)} ({len(medio_banos)/total*100:.1f}%)")
    print(f"   - Con superficie: {len(superficie)} ({len(superficie)/total*100:.1f}%)")
    if superficie:
        print(f"     Superficie promedio: {statistics.mean(superficie):.1f} m²")
    print(f"   - Con construcción: {len(construccion)} ({len(construccion)/total*100:.1f}%)")
    if construccion:
        print(f"     Construcción promedio: {statistics.mean(construccion):.1f} m²")
    print(f"   - Con estacionamientos: {len(estacionamientos)} ({len(estacionamientos)/total*100:.1f}%)")
    if estacionamientos:
        print(f"     Promedio de estacionamientos: {statistics.mean(estacionamientos):.1f}")
    print(f"   - Con niveles: {len(niveles)} ({len(niveles)/total*100:.1f}%)")
    if niveles:
        print(f"     Promedio de niveles: {statistics.mean(niveles):.1f}")
    
    # Analizar amenidades
    print("\n5. AMENIDADES MÁS COMUNES:")
    amenidades_count = {}
    for prop in propiedades:
        if "caracteristicas" in prop and "amenidades" in prop["caracteristicas"]:
            for amenidad in prop["caracteristicas"]["amenidades"]:
                amenidad_norm = normalizar_texto(amenidad)
                amenidades_count[amenidad_norm] = amenidades_count.get(amenidad_norm, 0) + 1
    
    # Ordenar por frecuencia y mostrar las 10 más comunes
    amenidades_sorted = sorted(amenidades_count.items(), key=lambda x: x[1], reverse=True)
    for amenidad, count in amenidades_sorted[:10]:
        porcentaje = (count / total) * 100
        print(f"   {amenidad}: {count} ({porcentaje:.1f}%)")
    
    # Analizar elementos de seguridad
    print("\n6. ELEMENTOS DE SEGURIDAD:")
    seguridad_count = {}
    for prop in propiedades:
        if "caracteristicas" in prop and "seguridad" in prop["caracteristicas"]:
            for elemento in prop["caracteristicas"]["seguridad"]:
                elemento_norm = normalizar_texto(elemento)
                seguridad_count[elemento_norm] = seguridad_count.get(elemento_norm, 0) + 1
    
    # Ordenar por frecuencia y mostrar todos
    seguridad_sorted = sorted(seguridad_count.items(), key=lambda x: x[1], reverse=True)
    for elemento, count in seguridad_sorted:
        porcentaje = (count / total) * 100
        print(f"   {elemento}: {count} ({porcentaje:.1f}%)")
    
    if estados_conservacion:
        print("\n7. ESTADOS DE CONSERVACIÓN:")
        for estado, count in estados_conservacion.most_common():
            print(f"   {estado}: {count} ({count/total*100:.1f}%)")
    
    if orientaciones:
        print("\n8. ORIENTACIONES:")
        for orientacion, count in orientaciones.most_common():
            print(f"   {orientacion}: {count} ({count/total*100:.1f}%)")

if __name__ == '__main__':
    analizar_calidad_campos('resultados/propiedades_estructuradas.json') 