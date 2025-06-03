import json
import collections
from typing import Dict, List

def analizar_ciudades():
    with open('resultados/propiedades_estructuradas.json') as f:
        data = json.load(f)

    ciudades = collections.defaultdict(int)
    sin_ciudad = 0
    total = len(data['propiedades'])
    ejemplos_sin_ciudad = []
    ejemplos_por_ciudad = {}

    for prop in data['propiedades']:
        ciudad = prop['ubicacion'].get('ciudad', '')
        if ciudad:
            ciudades[ciudad] += 1
            if ciudad not in ejemplos_por_ciudad:
                ejemplos_por_ciudad[ciudad] = {
                    'id': prop['id'],
                    'descripcion': prop['descripcion_original'][:200] + '...',
                    'ubicacion': prop['ubicacion']
                }
        else:
            sin_ciudad += 1
            if len(ejemplos_sin_ciudad) < 3:
                ejemplos_sin_ciudad.append({
                    'id': prop['id'],
                    'descripcion': prop['descripcion_original'][:200] + '...',
                    'ubicacion': prop['ubicacion']
                })

    print(f'\nTotal de propiedades: {total}')
    print(f'Sin ciudad detectada: {sin_ciudad} ({sin_ciudad/total*100:.1f}%)\n')
    
    print('Distribución de ciudades:')
    for ciudad, count in sorted(ciudades.items(), key=lambda x: x[1], reverse=True):
        print(f'{ciudad}: {count} ({count/total*100:.1f}%)')

    print('\nEjemplos de propiedades sin ciudad detectada:')
    for ejemplo in ejemplos_sin_ciudad:
        print(f"\nID: {ejemplo['id']}")
        print(f"Descripción: {ejemplo['descripcion']}")
        print(f"Ubicación: {ejemplo['ubicacion']}")

    print('\nEjemplos por ciudad:')
    for ciudad in sorted(ejemplos_por_ciudad.keys()):
        ejemplo = ejemplos_por_ciudad[ciudad]
        print(f"\nCiudad: {ciudad}")
        print(f"ID: {ejemplo['id']}")
        print(f"Descripción: {ejemplo['descripcion']}")
        print(f"Ubicación: {ejemplo['ubicacion']}")

if __name__ == '__main__':
    analizar_ciudades() 