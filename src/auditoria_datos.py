#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from collections import Counter
import statistics

def get_safe(dict_obj, *keys, default=None):
    """Obtiene un valor de un diccionario anidado de forma segura"""
    try:
        result = dict_obj
        for key in keys:
            result = result[key] if isinstance(result, dict) else default
        return result
    except:
        return default

def analizar_datos(datos):
    # Asegurar que tenemos una lista de propiedades
    if isinstance(datos, dict) and 'propiedades' in datos:
        propiedades = datos['propiedades']
    elif isinstance(datos, list):
        propiedades = datos
    else:
        propiedades = [datos]
    
    total_propiedades = len(propiedades)
    print(f"\nTotal de propiedades analizadas: {total_propiedades}")
    
    # Contadores para análisis
    campos_vacios = Counter()
    tipos_propiedad = Counter()
    tipos_operacion = Counter()
    rangos_precio = Counter()
    colonias = Counter()
    
    # Estadísticas numéricas
    recamaras = []
    banos = []
    superficie = []
    construccion = []
    
    for prop in propiedades:
        # Verificar campos vacíos
        if not get_safe(prop, 'descripcion'):
            campos_vacios['descripcion'] += 1
        if not get_safe(prop, 'ubicacion', 'colonia'):
            campos_vacios['colonia'] += 1
        if not get_safe(prop, 'ubicacion', 'referencias'):
            campos_vacios['referencias'] += 1
            
        # Contar tipos de propiedad y operación
        tipo_prop = get_safe(prop, 'propiedad', 'tipo_propiedad', default='No especificado')
        tipos_propiedad[tipo_prop] += 1
        
        tipo_op = get_safe(prop, 'propiedad', 'tipo_operacion', default='No especificado')
        tipos_operacion[tipo_op] += 1
        
        # Analizar precios
        precio = get_safe(prop, 'propiedad', 'precio', default='0')
        try:
            precio_num = float(str(precio).replace('$', '').replace(',', ''))
            if precio_num <= 500000:
                rangos_precio['< 500k'] += 1
            elif precio_num <= 1000000:
                rangos_precio['500k-1M'] += 1
            elif precio_num <= 2000000:
                rangos_precio['1M-2M'] += 1
            else:
                rangos_precio['> 2M'] += 1
        except:
            rangos_precio['Error precio'] += 1
        
        # Contar colonias
        colonia = get_safe(prop, 'ubicacion', 'colonia')
        if colonia:
            colonias[colonia] += 1
            
        # Recolectar estadísticas numéricas
        caract = get_safe(prop, 'descripcion_detallada', 'caracteristicas', default={})
        if isinstance(caract, dict):
            if caract.get('recamaras'):
                recamaras.append(float(caract['recamaras']))
            if caract.get('banos'):
                banos.append(float(caract['banos']))
            if caract.get('superficie_m2'):
                superficie.append(float(caract['superficie_m2']))
            if caract.get('construccion_m2'):
                construccion.append(float(caract['construccion_m2']))
    
    # Imprimir resultados
    print("\n=== CAMPOS VACÍOS ===")
    for campo, cantidad in campos_vacios.most_common():
        porcentaje = (cantidad / total_propiedades) * 100
        print(f"{campo}: {cantidad} ({porcentaje:.1f}%)")
    
    print("\n=== TIPOS DE PROPIEDAD ===")
    for tipo, cantidad in tipos_propiedad.most_common():
        porcentaje = (cantidad / total_propiedades) * 100
        print(f"{tipo}: {cantidad} ({porcentaje:.1f}%)")
    
    print("\n=== TIPOS DE OPERACIÓN ===")
    for tipo, cantidad in tipos_operacion.most_common():
        porcentaje = (cantidad / total_propiedades) * 100
        print(f"{tipo}: {cantidad} ({porcentaje:.1f}%)")
    
    print("\n=== RANGOS DE PRECIO ===")
    for rango, cantidad in rangos_precio.most_common():
        porcentaje = (cantidad / total_propiedades) * 100
        print(f"{rango}: {cantidad} ({porcentaje:.1f}%)")
    
    print("\n=== ESTADÍSTICAS NUMÉRICAS ===")
    def print_stats(nombre, datos):
        if datos:
            print(f"{nombre}:")
            print(f"  - Promedio: {statistics.mean(datos):.1f}")
            print(f"  - Mediana: {statistics.median(datos):.1f}")
            print(f"  - Mín: {min(datos):.1f}")
            print(f"  - Máx: {max(datos):.1f}")
            print(f"  - Total con datos: {len(datos)} ({len(datos)/total_propiedades*100:.1f}%)")
    
    print_stats("Recámaras", recamaras)
    print_stats("Baños", banos)
    print_stats("Superficie (m²)", superficie)
    print_stats("Construcción (m²)", construccion)
    
    print("\n=== TOP 10 COLONIAS ===")
    for colonia, cantidad in colonias.most_common(10):
        porcentaje = (cantidad / total_propiedades) * 100
        print(f"{colonia}: {cantidad} ({porcentaje:.1f}%)")

if __name__ == "__main__":
    with open("resultados/propiedades_estructuradas.json", "r", encoding="utf-8") as f:
        datos = json.load(f)
    analizar_datos(datos) 