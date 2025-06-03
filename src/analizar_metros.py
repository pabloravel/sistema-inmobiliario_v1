import json
from collections import defaultdict

def analizar_superficies():
    # Leer el archivo de propiedades estructuradas
    with open('resultados/propiedades_estructuradas.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    propiedades = data['propiedades']
    total = len(propiedades)
    
    # Contadores
    con_superficie = 0
    con_construccion = 0
    
    # Rangos para análisis
    rangos_superficie = defaultdict(int)
    rangos_construccion = defaultdict(int)
    
    # Ejemplos de propiedades sin superficie detectada
    ejemplos_sin_superficie = []
    ejemplos_sin_construccion = []
    
    for prop in propiedades:
        # Obtener valores de superficie y construcción
        superficie = prop['descripcion']['caracteristicas'].get('superficie_m2', 0)
        construccion = prop['descripcion']['caracteristicas'].get('construccion_m2', 0)
        
        # Contar propiedades con superficie y construcción
        if superficie > 0:
            con_superficie += 1
            # Categorizar por rangos
            if superficie <= 100:
                rangos_superficie['0-100'] += 1
            elif superficie <= 200:
                rangos_superficie['101-200'] += 1
            elif superficie <= 500:
                rangos_superficie['201-500'] += 1
            elif superficie <= 1000:
                rangos_superficie['501-1000'] += 1
            else:
                rangos_superficie['1000+'] += 1
        else:
            if len(ejemplos_sin_superficie) < 5:
                ejemplos_sin_superficie.append({
                    'id': prop['id'],
                    'descripcion': prop['descripcion_original'],
                    'tipo': prop['propiedad']['tipo_propiedad']
                })
        
        if construccion > 0:
            con_construccion += 1
            # Categorizar por rangos
            if construccion <= 100:
                rangos_construccion['0-100'] += 1
            elif construccion <= 200:
                rangos_construccion['101-200'] += 1
            elif construccion <= 300:
                rangos_construccion['201-300'] += 1
            elif construccion <= 500:
                rangos_construccion['301-500'] += 1
            else:
                rangos_construccion['500+'] += 1
        else:
            if len(ejemplos_sin_construccion) < 5:
                ejemplos_sin_construccion.append({
                    'id': prop['id'],
                    'descripcion': prop['descripcion_original'],
                    'tipo': prop['propiedad']['tipo_propiedad']
                })
    
    # Imprimir resultados
    print(f"\nAnálisis de Superficies:")
    print(f"Total de propiedades: {total}")
    print(f"Con superficie detectada: {con_superficie} ({(con_superficie/total)*100:.1f}%)")
    print(f"Con metros de construcción: {con_construccion} ({(con_construccion/total)*100:.1f}%)")
    
    print("\nDistribución de superficies de terreno:")
    for rango, cantidad in sorted(rangos_superficie.items()):
        print(f"- {rango} m²: {cantidad} ({(cantidad/con_superficie)*100:.1f}%)")
    
    print("\nDistribución de superficies de construcción:")
    for rango, cantidad in sorted(rangos_construccion.items()):
        print(f"- {rango} m²: {cantidad} ({(cantidad/con_construccion)*100:.1f}%)")
    
    print("\nEjemplos de propiedades sin superficie detectada:")
    for i, ejemplo in enumerate(ejemplos_sin_superficie, 1):
        print(f"\nEjemplo {i}:")
        print(f"ID: {ejemplo['id']}")
        print(f"Tipo: {ejemplo['tipo']}")
        print(f"Descripción: {ejemplo['descripcion'][:200]}...")
    
    print("\nEjemplos de propiedades sin construcción detectada:")
    for i, ejemplo in enumerate(ejemplos_sin_construccion, 1):
        print(f"\nEjemplo {i}:")
        print(f"ID: {ejemplo['id']}")
        print(f"Tipo: {ejemplo['tipo']}")
        print(f"Descripción: {ejemplo['descripcion'][:200]}...")

if __name__ == "__main__":
    analizar_superficies() 