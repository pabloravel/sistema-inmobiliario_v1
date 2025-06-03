import json
from collections import Counter
from typing import Dict, List, Tuple
import re

def cargar_datos() -> Tuple[List[Dict], Dict[str, int]]:
    """
    Carga los datos procesados y retorna las propiedades y estadísticas básicas.
    """
    with open('resultados/propiedades_estructuradas.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        propiedades = data["propiedades"]
    
    # Conteo de ciudades
    ciudades = Counter([p["ubicacion"]["ciudad"] for p in propiedades])
    
    return propiedades, dict(ciudades)

def analizar_confianza_ciudad(propiedad: Dict) -> Tuple[str, float, List[str]]:
    """
    Analiza la confianza en la extracción de la ciudad para una propiedad.
    Retorna: (ciudad, puntuación_confianza, evidencias)
    """
    ciudad = propiedad["ubicacion"]["ciudad"]
    evidencias = []
    puntuacion = 0.0
    
    # Si no hay ciudad asignada
    if not ciudad:
        return "", 0.0, ["No se detectó ciudad"]
    
    # 1. Verificar si hay mención directa de la ciudad en la descripción
    descripcion = propiedad["descripcion_original"].lower()
    if ciudad.lower() in descripcion:
        puntuacion += 1.0
        evidencias.append(f"Mención directa de {ciudad} en descripción")
    
    # 2. Verificar si hay una colonia conocida que corresponde a la ciudad
    colonia = propiedad["ubicacion"]["colonia"]
    if colonia:
        puntuacion += 0.8
        evidencias.append(f"Colonia detectada: {colonia}")
    
    # 3. Verificar puntos de interés
    puntos_interes = propiedad["ubicacion"]["puntos_interes"]
    if puntos_interes:
        puntuacion += 0.6
        evidencias.append(f"Puntos de interés detectados: {len(puntos_interes)}")
    
    # 4. Verificar zona
    zona = propiedad["ubicacion"]["zona"]
    if zona:
        puntuacion += 0.7
        evidencias.append(f"Zona detectada: {zona}")
    
    # 5. Verificar referencias de ubicación
    ubicacion_ref = propiedad["ubicacion"]["ubicacion_referencia"]
    if ubicacion_ref:
        puntuacion += 0.5
        evidencias.append(f"Referencias de ubicación detectadas")
    
    # Normalizar puntuación a un máximo de 1.0
    puntuacion = min(puntuacion, 1.0)
    
    return ciudad, puntuacion, evidencias

def identificar_casos_sospechosos(propiedades: List[Dict]) -> List[Dict]:
    """
    Identifica propiedades con posibles errores en la extracción de ciudad.
    """
    casos_sospechosos = []
    
    for prop in propiedades:
        ciudad, confianza, evidencias = analizar_confianza_ciudad(prop)
        
        # Criterios para marcar como sospechoso
        if confianza < 0.6:
            casos_sospechosos.append({
                "id": prop["id"],
                "link": prop["link"],
                "ciudad_detectada": ciudad,
                "confianza": confianza,
                "evidencias": evidencias,
                "descripcion": prop["descripcion_original"][:200] + "...",  # Primeros 200 caracteres
                "ubicacion": prop["ubicacion"]
            })
    
    return casos_sospechosos

def generar_reporte_auditoria():
    """
    Genera un reporte detallado de la auditoría de ubicaciones.
    """
    print("Iniciando auditoría de ubicaciones...")
    
    # Cargar datos
    propiedades, conteo_ciudades = cargar_datos()
    
    print("\n1. Distribución de propiedades por ciudad:")
    print("-" * 50)
    total_props = len(propiedades)
    for ciudad, cantidad in sorted(conteo_ciudades.items(), key=lambda x: x[1], reverse=True):
        porcentaje = (cantidad / total_props) * 100
        print(f"{ciudad or 'Sin ciudad':<20} {cantidad:>5} ({porcentaje:>5.1f}%)")
    
    # Análisis de confianza
    print("\n2. Análisis de confianza en la extracción:")
    print("-" * 50)
    confianzas = []
    for prop in propiedades:
        _, confianza, _ = analizar_confianza_ciudad(prop)
        confianzas.append(confianza)
    
    confianza_promedio = sum(confianzas) / len(confianzas)
    confianza_alta = len([c for c in confianzas if c >= 0.8])
    confianza_media = len([c for c in confianzas if 0.6 <= c < 0.8])
    confianza_baja = len([c for c in confianzas if c < 0.6])
    
    print(f"Confianza promedio: {confianza_promedio:.2f}")
    print(f"Propiedades con confianza alta (>=0.8): {confianza_alta} ({confianza_alta/total_props*100:.1f}%)")
    print(f"Propiedades con confianza media (0.6-0.8): {confianza_media} ({confianza_media/total_props*100:.1f}%)")
    print(f"Propiedades con confianza baja (<0.6): {confianza_baja} ({confianza_baja/total_props*100:.1f}%)")
    
    # Identificar casos sospechosos
    casos_sospechosos = identificar_casos_sospechosos(propiedades)
    
    print("\n3. Casos sospechosos identificados:")
    print("-" * 50)
    print(f"Total de casos sospechosos: {len(casos_sospechosos)}")
    
    # Guardar casos sospechosos para revisión manual
    with open('resultados/auditoria_ubicaciones.json', 'w', encoding='utf-8') as f:
        json.dump({
            "resumen": {
                "total_propiedades": total_props,
                "distribucion_ciudades": conteo_ciudades,
                "confianza_promedio": confianza_promedio,
                "confianza_alta": confianza_alta,
                "confianza_media": confianza_media,
                "confianza_baja": confianza_baja
            },
            "casos_sospechosos": casos_sospechosos
        }, f, ensure_ascii=False, indent=2)
    
    print("\nReporte completo guardado en 'resultados/auditoria_ubicaciones.json'")

if __name__ == "__main__":
    generar_reporte_auditoria() 