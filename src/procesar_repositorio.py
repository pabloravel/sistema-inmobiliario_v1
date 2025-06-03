#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
from datetime import datetime
from mejoras_extraccion import ExtractorMejorado, procesar_repositorio

def main():
    # Crear directorios necesarios
    directorios = [
        'resultados',
        'resultados/procesadas',
        'resultados/errores',
        'catalogos'
    ]
    
    for directorio in directorios:
        os.makedirs(directorio, exist_ok=True)
    
    # Configurar rutas
    fecha = datetime.now().strftime('%Y-%m-%d')
    ruta_entrada = 'resultados/repositorio_propiedades.json'
    ruta_salida = f'resultados/procesadas/propiedades_procesadas_{fecha}.json'
    ruta_errores = f'resultados/errores/errores_procesamiento_{fecha}.json'
    
    print("\nIniciando procesamiento del repositorio...")
    print(f"- Archivo de entrada: {ruta_entrada}")
    print(f"- Archivo de salida: {ruta_salida}")
    
    try:
        # Procesar repositorio
        procesar_repositorio(ruta_entrada, ruta_salida)
        
    except FileNotFoundError:
        print("\n❌ Error: No se encontró el archivo de entrada")
        print(f"   Asegúrate de que exista el archivo: {ruta_entrada}")
        
    except json.JSONDecodeError:
        print("\n❌ Error: El archivo de entrada no es un JSON válido")
        print("   Verifica el formato del archivo")
        
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        
    else:
        print("\n✅ Procesamiento completado exitosamente")
        print(f"   Los resultados se guardaron en: {ruta_salida}")

if __name__ == "__main__":
    main() 