import json
import re
from collections import defaultdict
from typing import Dict, Any, List
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def normalizar_precio(texto: str) -> float:
    """Normaliza un precio en formato string a float."""
    if not texto:
        return 0.0
    
    # Limpiar el texto
    texto = texto.lower().strip()
    texto = texto.replace('$', '').replace('mxn', '').replace('mnx', '').replace('mx', '')
    texto = texto.replace(' ', '')
    
    # Convertir millones
    if 'mill' in texto:
        texto = texto.replace('millones', '').replace('millon', '').replace('mill', '')
        try:
            # Reemplazar puntos por nada (son separadores de miles)
            numero = float(texto.replace('.', '').replace(',', '.'))
            return numero * 1_000_000
        except:
            return 0.0
    
    # Convertir miles
    if 'mil' in texto:
        texto = texto.replace('mil', '')
        try:
            numero = float(texto.replace('.', '').replace(',', '.'))
            return numero * 1_000
        except:
            return 0.0
    
    # Convertir número normal
    try:
        # Reemplazar puntos por nada (son separadores de miles)
        return float(texto.replace('.', '').replace(',', '.'))
    except:
        return 0.0

def cargar_datos(archivo: str) -> List[Dict[str, Any]]:
    """Carga los datos del archivo JSON."""
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            if isinstance(datos, dict):
                # Si es un diccionario, extraer las propiedades
                if "propiedades" in datos:
                    return datos["propiedades"]
                return list(datos.values())
            return datos
    except Exception as e:
        logger.error(f"Error cargando archivo {archivo}: {e}")
        return []

def analizar_tipos_propiedad(propiedades: List[Dict[str, Any]]) -> Dict[str, int]:
    """Analiza la distribución de tipos de propiedad."""
    tipos = defaultdict(int)
    
    for i, prop in enumerate(propiedades):
        tipo = None
        
        # Buscar el tipo de propiedad en la estructura correcta
        if "propiedad" in prop and isinstance(prop["propiedad"], dict):
            tipo = prop["propiedad"].get("tipo_propiedad")
        
        # Si no se encuentra o es nulo, intentar extraer de la descripción
        if not tipo or not isinstance(tipo, str):
            descripcion = prop.get("descripcion_original", "").lower()
            # Palabras clave para identificar tipos de propiedad
            if "casa" in descripcion:
                tipo = "casa"
            elif "depart" in descripcion or "dpto" in descripcion:
                tipo = "departamento"
            elif "terreno" in descripcion or "lote" in descripcion:
                tipo = "terreno"
            elif "local" in descripcion:
                tipo = "local"
            elif "oficina" in descripcion:
                tipo = "oficina"
            elif "bodega" in descripcion:
                tipo = "bodega"
        
        if not tipo:
            tipos["No especificado"] += 1
            # Loggear los primeros 5 casos sin tipo para análisis
            if i < 5:
                logger.debug(f"Propiedad sin tipo encontrado (índice {i}):")
                logger.debug(json.dumps(prop, indent=2, ensure_ascii=False))
        else:
            # Normalizar el tipo (convertir a título y eliminar espacios extra)
            tipo = tipo.strip().title()
            tipos[tipo] += 1
    
    return dict(tipos)

def analizar_precios(propiedades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analiza las estadísticas de precios usando el texto original sin modificar."""
    precios = []
    
    for prop in propiedades:
        precio = None
        
        # Intentar obtener el precio del formato antiguo
        if "precios" in prop and isinstance(prop["precios"], dict):
            if "valor" in prop["precios"]:
                precio = prop["precios"]["valor"]
        
        # Intentar obtener el precio del formato nuevo
        elif "precio" in prop and isinstance(prop["precio"], dict):
            if "texto_original" in prop["precio"]:
                precio = prop["precio"]["texto_original"]
            elif "valor" in prop["precio"]:
                precio = prop["precio"]["valor"]
        
        if precio is not None:
            precios.append(str(precio))
    
    return {
        "precios_originales": precios,
        "total_propiedades": len(precios)
    }

def analizar_caracteristicas(propiedades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analiza las características principales de las propiedades."""
    stats = {
        "recamaras": defaultdict(int),
        "banos": defaultdict(int),
        "estacionamientos": defaultdict(int),
        "superficie_m2": [],
        "construccion_m2": []
    }
    
    for prop in propiedades:
        caract = prop.get("caracteristicas", {})
        
        # Recámaras
        rec = caract.get("recamaras")
        if isinstance(rec, (int, float)) and rec > 0:
            stats["recamaras"][rec] += 1
            
        # Baños (sumar baños completos y medios baños)
        banos = caract.get("banos", 0)
        medio_bano = caract.get("medio_bano", 0)
        total_banos = (banos if isinstance(banos, (int, float)) else 0) + (0.5 * medio_bano if isinstance(medio_bano, (int, float)) else 0)
        if total_banos > 0:
            stats["banos"][total_banos] += 1
            
        # Estacionamientos
        est = caract.get("estacionamientos")
        if isinstance(est, (int, float)) and est > 0:
            stats["estacionamientos"][est] += 1
            
        # Superficie
        sup = caract.get("superficie_m2")
        if isinstance(sup, (int, float)) and sup > 0:
            stats["superficie_m2"].append(sup)
            
        # Construcción
        con = caract.get("construccion_m2")
        if isinstance(con, (int, float)) and con > 0:
            stats["construccion_m2"].append(con)
    
    # Calcular promedios para superficies
    if stats["superficie_m2"]:
        stats["superficie_m2"] = {
            "min": min(stats["superficie_m2"]),
            "max": max(stats["superficie_m2"]),
            "promedio": sum(stats["superficie_m2"]) / len(stats["superficie_m2"]),
            "total_con_datos": len(stats["superficie_m2"])
        }
    else:
        stats["superficie_m2"] = {
            "min": 0, "max": 0, "promedio": 0, "total_con_datos": 0
        }
        
    if stats["construccion_m2"]:
        stats["construccion_m2"] = {
            "min": min(stats["construccion_m2"]),
            "max": max(stats["construccion_m2"]),
            "promedio": sum(stats["construccion_m2"]) / len(stats["construccion_m2"]),
            "total_con_datos": len(stats["construccion_m2"])
        }
    else:
        stats["construccion_m2"] = {
            "min": 0, "max": 0, "promedio": 0, "total_con_datos": 0
        }
    
    return dict(stats)

def analizar_distribucion():
    # Cargar datos
    with open('resultados/propiedades_estructuradas.json', 'r') as f:
        datos = json.load(f)

    # Inicializar contadores
    conteo_operaciones = defaultdict(int)
    conteo_precios = {
        "1M+": {"venta": 0, "renta": 0, "desconocido": 0},
        "300k-1M": {"venta": 0, "renta": 0, "desconocido": 0},
        "<300k": {"venta": 0, "renta": 0, "desconocido": 0}
    }

    # Analizar cada propiedad
    for prop in datos["propiedades"]:
        tipo_op = prop["propiedad"]["tipo_operacion"]
        precio_info = prop["propiedad"]["precio"]
        
        # Contar por tipo de operación
        conteo_operaciones[tipo_op] += 1
        
        # Contar por rango de precio
        if precio_info and precio_info.get("valor"):
            precio = float(precio_info["valor"])
            if precio > 1_000_000:
                conteo_precios["1M+"][tipo_op] += 1
            elif precio > 300_000:
                conteo_precios["300k-1M"][tipo_op] += 1
            else:
                conteo_precios["<300k"][tipo_op] += 1

    # Imprimir resultados
    print("\nDistribución por tipo de operación:")
    print("-" * 40)
    total = sum(conteo_operaciones.values())
    for tipo, cantidad in conteo_operaciones.items():
        porcentaje = (cantidad / total) * 100
        print(f"{tipo}: {cantidad} ({porcentaje:.1f}%)")

    print("\nDistribución por rango de precios:")
    print("-" * 40)
    for rango, tipos in conteo_precios.items():
        print(f"\nRango {rango}:")
        subtotal = sum(tipos.values())
        for tipo, cantidad in tipos.items():
            porcentaje = (cantidad / subtotal * 100) if subtotal > 0 else 0
            print(f"  {tipo}: {cantidad} ({porcentaje:.1f}%)")

def main():
    # Configurar logging para ver mensajes de debug
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Cargar datos
    propiedades = cargar_datos("resultados/propiedades_estructuradas.json")
    total_propiedades = len(propiedades)
    
    logger.info(f"Total de propiedades: {total_propiedades}")
    
    # Analizar tipos de propiedad
    tipos = analizar_tipos_propiedad(propiedades)
    logger.info("\nDistribución por tipo de propiedad:")
    for tipo, cantidad in tipos.items():
        logger.info(f"{tipo}: {cantidad} ({(cantidad/total_propiedades*100):.1f}%)")
    
    # Analizar precios
    precios = analizar_precios(propiedades)
    logger.info("\nEstadísticas de precios:")
    logger.info(f"Total de propiedades con precio: {precios['total_propiedades']}")
    logger.info("\nPrimeros 20 precios (sin modificar):")
    for precio in precios['precios_originales'][:20]:
        logger.info(f"Precio original: {precio}")
    
    # Analizar características
    caract = analizar_caracteristicas(propiedades)
    
    logger.info("\nDistribución de recámaras:")
    for rec, cant in sorted(caract["recamaras"].items()):
        logger.info(f"{rec} recámara(s): {cant} ({(cant/total_propiedades*100):.1f}%)")
        
    logger.info("\nDistribución de baños:")
    for ban, cant in sorted(caract["banos"].items()):
        logger.info(f"{ban} baño(s): {cant} ({(cant/total_propiedades*100):.1f}%)")
        
    logger.info("\nDistribución de estacionamientos:")
    for est, cant in sorted(caract["estacionamientos"].items()):
        logger.info(f"{est} estacionamiento(s): {cant} ({(cant/total_propiedades*100):.1f}%)")
        
    logger.info("\nEstadísticas de superficie:")
    logger.info(f"Mínima: {caract['superficie_m2']['min']} m²")
    logger.info(f"Máxima: {caract['superficie_m2']['max']} m²")
    logger.info(f"Promedio: {caract['superficie_m2']['promedio']:.1f} m²")
    logger.info(f"Total con datos: {caract['superficie_m2']['total_con_datos']} ({(caract['superficie_m2']['total_con_datos']/total_propiedades*100):.1f}%)")
    
    logger.info("\nEstadísticas de construcción:")
    logger.info(f"Mínima: {caract['construccion_m2']['min']} m²")
    logger.info(f"Máxima: {caract['construccion_m2']['max']} m²")
    logger.info(f"Promedio: {caract['construccion_m2']['promedio']:.1f} m²")
    logger.info(f"Total con datos: {caract['construccion_m2']['total_con_datos']} ({(caract['construccion_m2']['total_con_datos']/total_propiedades*100):.1f}%)")

    # Analizar distribución de operaciones y precios
    analizar_distribucion()

if __name__ == "__main__":
    main() 