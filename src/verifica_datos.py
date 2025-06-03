#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import Dict, List, Any, Tuple
from datetime import datetime

def cargar_json(archivo: str) -> Dict:
    """Carga un archivo JSON."""
    with open(archivo, 'r', encoding='utf-8') as f:
        return json.load(f)

def verificar_precio(precio_estructurado: Dict, precio_original: Any) -> List[str]:
    """Verifica la concordancia del precio."""
    errores = []
    
    if not precio_estructurado:
        errores.append("Precio estructurado no existe")
        return errores
    
    try:
        # Verificar si el precio original es un diccionario
        if isinstance(precio_original, dict):
            valor_original = precio_original.get("valor")
            moneda_original = precio_original.get("moneda")
            
            if valor_original:
                # Convertir valor original a número si es string
                if isinstance(valor_original, str):
                    valor_original = valor_original.replace(',', '').replace('$', '').strip()
                    try:
                        valor_original = float(valor_original)
                    except ValueError:
                        errores.append(f"No se pudo convertir el valor original: {valor_original}")
                        return errores
                
                # Comparar valores
                try:
                    if abs(float(precio_estructurado["valor"]) - float(valor_original)) > 1:
                        errores.append(f"Discrepancia en valor: estructurado={precio_estructurado['valor']}, original={valor_original}")
                except (ValueError, TypeError):
                    errores.append("Error al comparar valores de precio")
                
                # Verificar moneda
                if moneda_original and moneda_original != precio_estructurado.get("moneda"):
                    errores.append(f"Discrepancia en moneda: estructurado={precio_estructurado.get('moneda')}, original={moneda_original}")
        
        # Verificar si el precio original es un string
        elif isinstance(precio_original, str):
            precio_texto = precio_original.lower()
            
            # Verificar coherencia con el tipo de operación
            if "renta" in precio_texto and precio_estructurado.get("periodo") != "mensual":
                errores.append("Texto menciona renta pero no está marcado como mensual")
            elif "venta" in precio_texto and precio_estructurado.get("periodo") == "mensual":
                errores.append("Texto menciona venta pero está marcado como mensual")
            
            # Verificar coherencia con la moneda
            if "usd" in precio_texto or "dolar" in precio_texto:
                if precio_estructurado.get("moneda") != "USD":
                    errores.append("Texto menciona USD pero moneda estructurada es diferente")
    except Exception as e:
        errores.append(f"Error al verificar precio: {str(e)}")
    
    return errores

def verificar_ubicacion(ubicacion_estructurada: Dict, ubicacion_original: Any) -> List[str]:
    """Verifica la concordancia de la ubicación."""
    errores = []
    
    if not ubicacion_estructurada:
        errores.append("Ubicación estructurada no existe")
        return errores
    
    # Verificar si la ubicación original es un diccionario
    if isinstance(ubicacion_original, dict):
        # Verificar ciudad
        ciudad_orig = str(ubicacion_original.get("ciudad", "")).lower()
        ciudad_estr = str(ubicacion_estructurada.get("ciudad", "")).lower()
        if ciudad_orig and ciudad_orig != ciudad_estr:
            errores.append(f"Discrepancia en ciudad: estructurada={ciudad_estr}, original={ciudad_orig}")
        
        # Verificar colonia
        colonia_orig = str(ubicacion_original.get("colonia", "")).lower()
        colonia_estr = str(ubicacion_estructurada.get("colonia", "")).lower()
        if colonia_orig and colonia_orig != colonia_estr:
            errores.append(f"Discrepancia en colonia: estructurada={colonia_estr}, original={colonia_orig}")
        
        # Verificar estado
        estado_orig = str(ubicacion_original.get("estado", "")).lower()
        estado_estr = str(ubicacion_estructurada.get("estado", "")).lower()
        if estado_orig and estado_orig != estado_estr:
            errores.append(f"Discrepancia en estado: estructurado={estado_estr}, original={estado_orig}")
    
    return errores

def verificar_caracteristicas(caract_estructuradas: Dict, caract_originales: Any) -> List[str]:
    """Verifica la concordancia de las características."""
    errores = []
    
    if not caract_estructuradas:
        errores.append("Características estructuradas no existen")
        return errores
    
    if isinstance(caract_originales, dict):
        # Verificar recámaras
        try:
            rec_orig = caract_originales.get("recamaras")
            rec_estr = caract_estructuradas.get("recamaras")
            if rec_orig is not None and rec_estr is not None:
                if float(rec_orig) != float(rec_estr):
                    errores.append(f"Discrepancia en recámaras: estructuradas={rec_estr}, original={rec_orig}")
        except (ValueError, TypeError):
            errores.append("Error al comparar recámaras")
        
        # Verificar baños
        try:
            banos_orig = caract_originales.get("banos")
            banos_estr = caract_estructuradas.get("banos")
            if banos_orig is not None and banos_estr is not None:
                if float(banos_orig) != float(banos_estr):
                    errores.append(f"Discrepancia en baños: estructurados={banos_estr}, original={banos_orig}")
        except (ValueError, TypeError):
            errores.append("Error al comparar baños")
        
        # Verificar superficie
        try:
            sup_orig = caract_originales.get("superficie_m2")
            sup_estr = caract_estructuradas.get("superficie_m2")
            if sup_orig is not None and sup_estr is not None:
                if abs(float(sup_orig) - float(sup_estr)) > 1:
                    errores.append(f"Discrepancia en superficie: estructurada={sup_estr}, original={sup_orig}")
        except (ValueError, TypeError):
            errores.append("Error al comparar superficie")
        
        # Verificar construcción
        try:
            cons_orig = caract_originales.get("construccion_m2")
            cons_estr = caract_estructuradas.get("construccion_m2")
            if cons_orig is not None and cons_estr is not None:
                if abs(float(cons_orig) - float(cons_estr)) > 1:
                    errores.append(f"Discrepancia en construcción: estructurada={cons_estr}, original={cons_orig}")
        except (ValueError, TypeError):
            errores.append("Error al comparar construcción")
    
        cons_orig = caract_originales.get("construccion_m2")
        cons_estr = caract_estructuradas.get("construccion_m2")
        if cons_orig is not None and cons_estr is not None and abs(float(cons_orig) - float(cons_estr)) > 1:
            errores.append(f"Discrepancia en construcción: estructurada={cons_estr}, original={cons_orig}")
    
    return errores

def verificar_tipo_operacion(tipo_estructurado: str, datos_originales: Dict) -> List[str]:
    """Verifica la concordancia del tipo de operación."""
    errores = []
    
    if not tipo_estructurado:
        errores.append("Tipo de operación estructurado no existe")
        return errores
    
    try:
        # Buscar tipo de operación en diferentes campos
        tipo_orig = str(datos_originales.get("tipo_operacion", "")).lower()
        descripcion = str(datos_originales.get("descripcion", "")).lower()
        titulo = str(datos_originales.get("titulo", "")).lower()
        
        # Verificar coherencia
        if tipo_orig and tipo_orig != tipo_estructurado.lower():
            errores.append(f"Tipo de operación original '{tipo_orig}' no coincide con estructurado '{tipo_estructurado}'")
        
        # Verificar menciones en descripción y título
        if tipo_estructurado.lower() == "renta":
            if "venta" in descripcion and "renta" not in descripcion:
                errores.append("Descripción menciona venta pero tipo es renta")
            if "venta" in titulo and "renta" not in titulo:
                errores.append("Título menciona venta pero tipo es renta")
        elif tipo_estructurado.lower() == "venta":
            if "renta" in descripcion and "venta" not in descripcion:
                errores.append("Descripción menciona renta pero tipo es venta")
            if "renta" in titulo and "venta" not in titulo:
                errores.append("Título menciona renta pero tipo es venta")
    except Exception as e:
        errores.append(f"Error al verificar tipo de operación: {str(e)}")
    
    return errores

def verificar_tipo_propiedad(tipo_estructurado: str, datos_originales: Dict) -> List[str]:
    """Verifica la concordancia del tipo de propiedad."""
    errores = []
    
    if not tipo_estructurado:
        errores.append("Tipo de propiedad estructurado no existe")
        return errores
    
    try:
        # Buscar tipo de propiedad en diferentes campos
        tipo_orig = str(datos_originales.get("tipo_propiedad", "")).lower()
        descripcion = str(datos_originales.get("descripcion", "")).lower()
        titulo = str(datos_originales.get("titulo", "")).lower()
        
        # Mapeo de tipos comunes
        mapeo_tipos = {
            "casa": ["casa_sola", "casa_condominio"],
            "departamento": ["departamento"],
            "terreno": ["terreno"],
            "local": ["local_comercial"],
            "oficina": ["oficina"]
        }
        
        # Verificar coherencia
        tipo_encontrado = False
        for tipo_base, variantes in mapeo_tipos.items():
            if tipo_orig and tipo_base in tipo_orig and tipo_estructurado.lower() not in variantes:
                errores.append(f"Tipo original '{tipo_orig}' no coincide con estructurado '{tipo_estructurado}'")
                break
            elif tipo_base in descripcion and tipo_estructurado.lower() not in variantes:
                errores.append(f"Descripción menciona '{tipo_base}' pero tipo es '{tipo_estructurado}'")
                break
            elif tipo_base in titulo and tipo_estructurado.lower() not in variantes:
                errores.append(f"Título menciona '{tipo_base}' pero tipo es '{tipo_estructurado}'")
                break
    except Exception as e:
        errores.append(f"Error al verificar tipo de propiedad: {str(e)}")
    
    return errores

def verificar_propiedad(prop_estructurada: Dict, prop_original: Dict) -> Dict:
    """Verifica la concordancia entre una propiedad estructurada y su original."""
    resultado = {
        "id": prop_estructurada.get("id"),
        "errores": [],
        "campos_verificados": {}
    }
    
    # Verificar precio
    errores_precio = verificar_precio(
        prop_estructurada.get("propiedad", {}).get("precio"),
        prop_original.get("precio")
    )
    if errores_precio:
        resultado["errores"].extend([f"Precio: {e}" for e in errores_precio])
    resultado["campos_verificados"]["precio"] = len(errores_precio) == 0
    
    # Verificar ubicación
    errores_ubicacion = verificar_ubicacion(
        prop_estructurada.get("ubicacion"),
        prop_original.get("ubicacion")
    )
    if errores_ubicacion:
        resultado["errores"].extend([f"Ubicación: {e}" for e in errores_ubicacion])
    resultado["campos_verificados"]["ubicacion"] = len(errores_ubicacion) == 0
    
    # Verificar características
    errores_caract = verificar_caracteristicas(
        prop_estructurada.get("caracteristicas"),
        prop_original.get("caracteristicas")
    )
    if errores_caract:
        resultado["errores"].extend([f"Características: {e}" for e in errores_caract])
    resultado["campos_verificados"]["caracteristicas"] = len(errores_caract) == 0
    
    # Verificar tipo de propiedad
    errores_tipo = verificar_tipo_propiedad(
        prop_estructurada.get("propiedad", {}).get("tipo_propiedad"),
        prop_original
    )
    if errores_tipo:
        resultado["errores"].extend([f"Tipo propiedad: {e}" for e in errores_tipo])
    resultado["campos_verificados"]["tipo_propiedad"] = len(errores_tipo) == 0
    
    # Verificar tipo de operación
    errores_operacion = verificar_tipo_operacion(
        prop_estructurada.get("propiedad", {}).get("tipo_operacion"),
        prop_original
    )
    if errores_operacion:
        resultado["errores"].extend([f"Tipo operación: {e}" for e in errores_operacion])
    resultado["campos_verificados"]["tipo_operacion"] = len(errores_operacion) == 0
    
    return resultado

def main():
    # Cargar archivos
    print("Cargando archivos...")
    estructuradas = cargar_json("resultados/propiedades_estructuradas.json")
    repositorio = cargar_json("resultados/repositorio_propiedades.json")
    
    # Preparar resultados
    resultados = {
        "fecha_verificacion": datetime.now().isoformat(),
        "total_propiedades": len(estructuradas["propiedades"]),
        "propiedades_verificadas": [],
        "estadisticas": {
            "total_errores": 0,
            "errores_por_campo": {
                "precio": 0,
                "ubicacion": 0,
                "caracteristicas": 0,
                "tipo_propiedad": 0,
                "tipo_operacion": 0
            },
            "propiedades_sin_errores": 0
        }
    }
    
    # Verificar cada propiedad
    print("\nVerificando propiedades...")
    for prop in estructuradas["propiedades"]:
        prop_id = prop.get("id")
        if prop_id in repositorio:
            resultado = verificar_propiedad(prop, repositorio[prop_id])
            
            # Actualizar estadísticas
            if resultado["errores"]:
                resultados["estadisticas"]["total_errores"] += len(resultado["errores"])
                for campo, es_valido in resultado["campos_verificados"].items():
                    if not es_valido:
                        resultados["estadisticas"]["errores_por_campo"][campo] += 1
            else:
                resultados["estadisticas"]["propiedades_sin_errores"] += 1
            
            resultados["propiedades_verificadas"].append(resultado)
        else:
            print(f"Advertencia: Propiedad {prop_id} no encontrada en repositorio")
    
    # Guardar resultados
    archivo_resultados = f"resultados/verificacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(archivo_resultados, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    
    # Imprimir resumen
    print("\nResumen de verificación:")
    print(f"Total propiedades verificadas: {resultados['total_propiedades']}")
    print(f"Propiedades sin errores: {resultados['estadisticas']['propiedades_sin_errores']}")
    print(f"Total errores encontrados: {resultados['estadisticas']['total_errores']}")
    print("\nErrores por campo:")
    for campo, cantidad in resultados["estadisticas"]["errores_por_campo"].items():
        print(f"- {campo}: {cantidad}")
    print(f"\nResultados detallados guardados en: {archivo_resultados}")

if __name__ == "__main__":
    main() 