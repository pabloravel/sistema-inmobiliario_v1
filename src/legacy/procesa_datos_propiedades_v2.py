#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
procesa_datos_propiedades_v2.py

Versión 2.0 - Mejoras:
- Corrección de manejo de duplicados por ciudad
- Mejor manejo de errores
- Análisis más detallado de resultados
- Sistema de backup mejorado
"""

import os
import json
import logging
import re
from datetime import datetime
from bs4 import BeautifulSoup
from typing import Dict, List, Union, Tuple, Any, Optional

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constantes
REPO_MASTER = "resultados/repositorio_propiedades.json"
REPO_BACKUP = "resultados/repositorio_propiedades.json.bak"
ARCHIVO_REPOSITORIO = "resultados/repositorio_propiedades.json"
ARCHIVO_SALIDA = "resultados/propiedades_estructuradas.json"
ARCHIVO_LOG_DESCARTADAS = "resultados/propiedades_descartadas.log"

class ProcesadorPropiedades:
    def __init__(self):
        self.propiedades_procesadas = []
        self.propiedades_descartadas = []
        self.estadisticas = {
            "total_procesadas": 0,
            "total_validas": 0,
            "por_tipo": {},
            "por_operacion": {},
            "caracteristicas": {
                "un_nivel": 0,
                "recamara_pb": 0,
                "escrituras": 0,
                "cesion": 0
            }
        }
        
    def procesar_datos_crudos(self, datos: Dict[str, Any]) -> None:
        """Procesa los datos crudos y mantiene estadísticas."""
        if isinstance(datos, dict):
            propiedades = datos.get("propiedades", [])
        else:
            propiedades = datos
            
        total = len(propiedades)
        logger.info(f"Iniciando procesamiento de {total} propiedades...")
        
        for i, propiedad in enumerate(propiedades, 1):
            try:
                self.procesar_propiedad(propiedad)
                if i % 100 == 0:
                    logger.info(f"Procesadas {i}/{total} propiedades")
            except Exception as e:
                logger.error(f"Error procesando propiedad {i}: {str(e)}")
                self.propiedades_descartadas.append({
                    "id": propiedad.get("id", "desconocido"),
                    "razon": f"Error de procesamiento: {str(e)}"
                })
                
        self.guardar_resultados()
        self.guardar_log_descartadas()
        self.mostrar_estadisticas()

    def procesar_propiedad(self, propiedad: Dict[str, Any]) -> None:
        """Procesa una propiedad individual."""
        self.estadisticas["total_procesadas"] += 1
        
        # Validaciones básicas
        if not self.validar_propiedad(propiedad):
            return
            
        # Procesar la propiedad
        propiedad_procesada = propiedad.copy()
        descripcion = propiedad.get("descripcion_original", "") or propiedad.get("descripcion", "")
        
        # Extraer y validar campos principales
        tipo_propiedad = self.extraer_tipo_propiedad(descripcion)
        tipo_operacion = self.extraer_tipo_operacion(descripcion, propiedad.get("precio"))
        caracteristicas = self.extraer_caracteristicas(descripcion)
        
        # Actualizar estadísticas
        if tipo_propiedad:
            self.estadisticas["por_tipo"][tipo_propiedad] = self.estadisticas["por_tipo"].get(tipo_propiedad, 0) + 1
        if tipo_operacion:
            self.estadisticas["por_operacion"][tipo_operacion] = self.estadisticas["por_operacion"].get(tipo_operacion, 0) + 1
            
        # Actualizar contadores específicos
        if caracteristicas.get("un_nivel"):
            self.estadisticas["caracteristicas"]["un_nivel"] += 1
        if caracteristicas.get("recamara_planta_baja"):
            self.estadisticas["caracteristicas"]["recamara_pb"] += 1
        
        # Procesar información legal
        legal = self.extraer_legal(descripcion)
        if legal.get("escrituras"):
            self.estadisticas["caracteristicas"]["escrituras"] += 1
        if legal.get("cesion_derechos"):
            self.estadisticas["caracteristicas"]["cesion"] += 1
        
        # Actualizar la propiedad procesada
        propiedad_procesada.update({
            "tipo_propiedad": tipo_propiedad,
            "tipo_operacion": tipo_operacion,
            "caracteristicas": caracteristicas,
            "legal": legal,
            "precio": self.procesar_precio(propiedad.get("precio", {}))
        })
        
        self.propiedades_procesadas.append(propiedad_procesada)
        self.estadisticas["total_validas"] += 1

    def validar_propiedad(self, propiedad: Dict[str, Any]) -> bool:
        """Valida si una propiedad debe ser incluida."""
        if not propiedad:
            self.propiedades_descartadas.append({
                "id": "desconocido",
                "razon": "Propiedad vacía"
            })
            return False
            
        # Validar que tenga descripción
        if not propiedad.get("descripcion_original") and not propiedad.get("descripcion"):
            self.propiedades_descartadas.append({
                "id": propiedad.get("id", "desconocido"),
                "razon": "Sin descripción"
            })
            return False
            
        return True

    def extraer_tipo_propiedad(self, texto: str) -> Optional[str]:
        """Extrae el tipo de propiedad del texto."""
        if not texto:
            return None
            
        texto = texto.lower()
        
        # Patrones de búsqueda mejorados
        patrones = {
            "casa": [
                r"\bcasa\b(?!\s+(?:club|muestra))",
                r"\bresidencia\b",
                r"\bvilla\b"
            ],
            "departamento": [
                r"\bdepartamento\b",
                r"\bdepto\b",
                r"\bapartamento\b",
                r"\bpent\s*house\b"
            ],
            "terreno": [
                r"\bterreno\b",
                r"\blote\b(?!\s+de\s+\w+)",
                r"\bpredio\b"
            ],
            "local": [
                r"\blocal\s+comercial\b",
                r"\blocal\b(?!\s+(?:idad|mente|izaci[oó]n))",
                r"\bcomercio\b"
            ],
            "oficina": [
                r"\boficina\b",
                r"\bconsultorio\b"
            ],
            "bodega": [
                r"\bbodega\b",
                r"\bnave\s+industrial\b",
                r"\bgalp[oó]n\b"
            ]
        }
        
        for tipo, lista_patrones in patrones.items():
            for patron in lista_patrones:
                if re.search(patron, texto):
                    return tipo
                    
        return None

    def extraer_tipo_operacion(self, texto: str, precio: Any) -> Optional[str]:
        """Extrae el tipo de operación (venta/renta)."""
        if not texto:
            return None
            
        texto = texto.lower()
        
        # Patrones para venta
        if any(patron in texto for patron in [
            "venta", "vendo", "vendemos", "se vende", "precio de venta",
            "oportunidad de compra", "escrituras", "título de propiedad"
        ]):
            return "venta"
            
        # Patrones para renta
        if any(patron in texto for patron in [
            "renta", "rento", "rentamos", "se renta", "precio de renta",
            "mensual", "mensualidad", "arrendamiento", "alquiler"
        ]):
            return "renta"
            
        # Si tiene precio, usar como indicador
        if isinstance(precio, dict):
            valor = precio.get("valor")
            if valor:
                try:
                    valor_num = float(str(valor).replace(",", ""))
                    return "venta" if valor_num > 300000 else "renta"
                except (ValueError, TypeError):
                    pass
                    
        return None

    def extraer_caracteristicas(self, texto: str) -> Dict[str, Any]:
        """Extrae características detalladas de la propiedad."""
        if not texto:
            return {}
            
        texto = texto.lower()
        
        caracteristicas = {
            "recamaras": self.extraer_numero(texto, [
                r"(\d+)\s*rec[aá]maras?",
                r"(\d+)\s*habitaciones?",
                r"(\d+)\s*dormitorios?"
            ]),
            "banos": self.extraer_numero(texto, [
                r"(\d+)\s*baños?(?!\s*y\s*medio)",
                r"(\d+)\s*sanitarios?"
            ]),
            "medio_bano": any(patron in texto for patron in [
                "medio baño", "baño y medio", "1/2 baño"
            ]),
            "niveles": self.extraer_numero(texto, [
                r"(\d+)\s*nivele?s?",
                r"(\d+)\s*pisos?"
            ]),
            "un_nivel": any(patron in texto for patron in [
                "un nivel", "una planta", "planta baja",
                "todo en pb", "sin escaleras"
            ]),
            "recamara_planta_baja": any(patron in texto for patron in [
                "recámara en planta baja",
                "recamara en pb",
                "habitación en planta baja"
            ])
        }
        
        return caracteristicas

    def extraer_legal(self, texto: str) -> Dict[str, bool]:
        """Extrae información legal de la propiedad."""
        if not texto:
            return {}
            
        texto = texto.lower()
        
        return {
            "escrituras": any(patron in texto for patron in [
                "escrituras", "escriturada", "título de propiedad",
                "documentos en regla", "papeles en regla"
            ]),
            "cesion_derechos": any(patron in texto for patron in [
                "cesión de derechos", "cesion de derechos",
                "traspaso", "derechos de posesión"
            ])
        }

    def extraer_numero(self, texto: str, patrones: List[str]) -> Optional[int]:
        """Extrae un número usando una lista de patrones."""
        for patron in patrones:
            if match := re.search(patron, texto):
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None

    def procesar_precio(self, precio: Any) -> Dict[str, Any]:
        """Procesa y valida el precio de la propiedad."""
        if isinstance(precio, dict):
            # Si ya es un diccionario, validar y limpiar
            valor = precio.get("valor", "0")
            # Asegurar que el valor sea string
            return {
                "valor": str(valor),
                "moneda": precio.get("moneda", "MXN"),
                "es_valido": True
            }
        elif isinstance(precio, (int, float)):
            # Si es número, convertir a string
            return {
                "valor": str(int(precio)),
                "moneda": "MXN",
                "es_valido": True
            }
        elif isinstance(precio, str):
            # Si es string, limpiar y validar
            valor = re.sub(r'[^\d.]', '', precio)
            try:
                return {
                    "valor": str(int(float(valor))),
                    "moneda": "MXN",
                    "es_valido": True
                }
            except ValueError:
                pass
                
        return {
            "valor": "0",
            "moneda": "MXN",
            "es_valido": False
        }

    def guardar_resultados(self) -> None:
        """Guarda los resultados procesados."""
        with open(ARCHIVO_SALIDA, 'w', encoding='utf-8') as f:
            json.dump({
                "propiedades": self.propiedades_procesadas,
                "estadisticas": self.estadisticas
            }, f, indent=4, ensure_ascii=False)
        logger.info(f"Resultados guardados en {ARCHIVO_SALIDA}")

    def guardar_log_descartadas(self) -> None:
        """Guarda el log de propiedades descartadas."""
        with open(ARCHIVO_LOG_DESCARTADAS, 'w', encoding='utf-8') as f:
            for prop in self.propiedades_descartadas:
                f.write(f"ID: {prop['id']}, Razón: {prop['razon']}\n")
        logger.info(f"Log de propiedades descartadas guardado en {ARCHIVO_LOG_DESCARTADAS}")

    def mostrar_estadisticas(self) -> None:
        """Muestra las estadísticas del procesamiento."""
        logger.info("\nEstadísticas de procesamiento:")
        logger.info(f"Total propiedades procesadas: {self.estadisticas['total_procesadas']}")
        logger.info(f"Propiedades válidas: {self.estadisticas['total_validas']}")
        logger.info(f"Propiedades descartadas: {len(self.propiedades_descartadas)}")
        logger.info("\nPor tipo de propiedad:")
        for tipo, cantidad in self.estadisticas['por_tipo'].items():
            logger.info(f"- {tipo}: {cantidad}")
        logger.info("\nPor tipo de operación:")
        for op, cantidad in self.estadisticas['por_operacion'].items():
            logger.info(f"- {op}: {cantidad}")
        logger.info("\nCaracterísticas especiales:")
        for caract, cantidad in self.estadisticas['caracteristicas'].items():
            logger.info(f"- {caract}: {cantidad}")

def procesar_datos_crudos(datos_crudos: Dict, ciudad: str = "cuernavaca") -> Dict:
    """Procesa los datos crudos y extrae todos los campos necesarios"""
    # Obtener datos básicos
    titulo = datos_crudos["datos_basicos"]["titulo"]
    descripcion = datos_crudos["datos_basicos"]["descripcion"]
    precio_str = datos_crudos["datos_basicos"]["precio"]
    
    # Crear texto completo para análisis
    texto_completo = f"{titulo}\n{descripcion}".lower()
    
    # Procesar precio
    precio_num, moneda = normalizar_precio(precio_str)
    
    # Extraer todos los campos usando las funciones existentes
    tipo_operacion = extraer_tipo_operacion(texto_completo)
    tipo_propiedad = extraer_tipo_propiedad(texto_completo)
    superficie = extraer_superficie(texto_completo)
    caracteristicas = extraer_caracteristicas(texto_completo)
    amenidades = extraer_amenidades(texto_completo)
    legal = extraer_legal(texto_completo)
    ubicacion = extraer_ubicacion(texto_completo)
    ubicacion["ciudad"] = ciudad  # Asegurar que se guarde la ciudad
    
    # Construir estructura de datos completa
    return {
        "id": datos_crudos["id"],
        "link": datos_crudos["link"],
        "titulo": titulo,
        "descripcion": descripcion,
        "precio": {
            "valor": precio_num,
            "valor_normalizado": precio_num,
            "moneda": moneda,
            "es_valido": precio_num > 0,
            "error": None if precio_num > 0 else "Precio no detectado"
        },
        "tipo_operacion": tipo_operacion,
        "tipo_propiedad": tipo_propiedad,
        "superficie": superficie,
        "caracteristicas": caracteristicas,
        "amenidades": amenidades,
        "estado_legal": legal,
        "ubicacion": ubicacion,
        "metadata": {
            "fecha_extraccion": datos_crudos["metadata"]["fecha_extraccion"],
            "fecha_procesamiento": datetime.now().isoformat(),
            "fuente": "facebook_marketplace",
            "status": "completo"
        }
    }

def analizar_resultados(datos: Dict) -> List[str]:
    """Analiza los resultados y retorna lista de advertencias"""
    advertencias = []
    
    # Verificar campos básicos
    if not datos["titulo"]:
        advertencias.append("❌ Falta título")
    if not datos["descripcion"]:
        advertencias.append("❌ Falta descripción")
    if not datos["precio"]["es_valido"]:
        advertencias.append(f"❌ Error en precio: {datos['precio']['error']}")
    
    # Verificar ubicación
    if not datos["ubicacion"]["colonia"]:
        advertencias.append("⚠️ Falta colonia")
    if not datos["ubicacion"]["referencias"]:
        advertencias.append("⚠️ Sin referencias de ubicación")
    if not datos["ubicacion"]["calle"]:
        advertencias.append("⚠️ Falta calle")
    
    # Verificar características básicas
    if datos["tipo_propiedad"] == "otro":
        advertencias.append("⚠️ Tipo de propiedad no detectado")
    if not datos["tipo_operacion"]:
        advertencias.append("⚠️ Tipo de operación no detectado")
    if not datos["caracteristicas"].get("recamaras"):
        advertencias.append("⚠️ Número de recámaras no detectado")
    if not datos["caracteristicas"].get("banos"):
        advertencias.append("⚠️ Número de baños no detectado")
    if not datos["superficie"].get("terreno") and not datos["superficie"].get("construccion"):
        advertencias.append("⚠️ No se detectó superficie")
    
    return advertencias

def main():
    # 1. Crear backup del repositorio si existe
    if os.path.exists(REPO_MASTER):
        import shutil
        shutil.copy2(REPO_MASTER, REPO_BACKUP)
        print("✓ Backup del repositorio creado")
        
        # Cargar repositorio existente
        with open(REPO_MASTER, "r", encoding="utf-8") as f:
            repositorio = json.load(f)
        print(f"✓ Repositorio cargado con {len(repositorio)} propiedades")
    else:
        repositorio = {}
        print("✓ Nuevo repositorio creado")
    
    # 2. Obtener última carpeta de datos crudos
    carpetas = sorted([d for d in os.listdir("resultados/datos_crudos") 
                      if os.path.isdir(os.path.join("resultados/datos_crudos", d))])
    if not carpetas:
        print("❌ No hay datos crudos para procesar")
        return
    
    ultima_carpeta = os.path.join("resultados/datos_crudos", carpetas[-1])
    print(f"\n📂 Procesando datos de: {ultima_carpeta}")
    
    # 3. Procesar cada archivo
    archivos = [f for f in os.listdir(ultima_carpeta) if f.endswith(".json")]
    
    # Agrupar archivos por ID de propiedad para evitar duplicados
    propiedades = {}
    for archivo in archivos:
        # Manejar ambos formatos de nombre
        nombre = archivo.replace(".json", "")
        if "-" in nombre:
            ciudad, id_prop = nombre.split("-")
        else:
            id_prop = nombre
            ciudad = "cuernavaca"  # Ciudad por defecto
            
        if id_prop not in propiedades:
            propiedades[id_prop] = []
        propiedades[id_prop].append((ciudad, archivo))
    
    total = len(propiedades)
    print(f"📊 Total de propiedades a procesar: {total}")
    print(f"📋 Archivos encontrados: {len(archivos)}")
    print(f"🔄 Propiedades con múltiples versiones: {sum(1 for v in propiedades.values() if len(v) > 1)}")
    
    procesados = 0
    errores = 0
    advertencias_totales = 0
    
    procesador = ProcesadorPropiedades()
    
    for id_prop, versiones in propiedades.items():
        try:
            # Tomar la primera versión (podríamos implementar una lógica más compleja si es necesario)
            ciudad, archivo = versiones[0]
            ruta_archivo = os.path.join(ultima_carpeta, archivo)
            
            # Cargar datos crudos
            with open(ruta_archivo, "r", encoding="utf-8") as f:
                datos_crudos = json.load(f)
            
            # Verificar si los datos son válidos
            if datos_crudos["metadata"]["status"] != "completo":
                print(f"\n⚠️ Saltando {archivo} - Status: {datos_crudos['metadata']['status']}")
                errores += 1
                continue
            
            # Procesar datos
            procesador.procesar_datos_crudos(datos_crudos)
            
            # Actualizar repositorio
            repositorio[datos_crudos["id"]] = datos_crudos
            procesados += 1
            
            # Guardar cada 5 propiedades
            if procesados % 5 == 0:
                with open(REPO_MASTER, "w", encoding="utf-8") as f:
                    json.dump(repositorio, f, ensure_ascii=False, indent=2)
                print(f"\n💾 Guardado intermedio: {procesados}/{total}")
            
            # Si hay más versiones, mostrar advertencia
            if len(versiones) > 1:
                print(f"\n⚠️ Propiedad {id_prop} tiene {len(versiones)} versiones:")
                for c, a in versiones:
                    print(f"  - {c}: {a}")
            
        except Exception as e:
            print(f"\n❌ Error procesando {id_prop}: {str(e)}")
            errores += 1
    
    # 4. Guardar repositorio final
    with open(REPO_MASTER, "w", encoding="utf-8") as f:
        json.dump(repositorio, f, ensure_ascii=False, indent=2)
    
    # 5. Mostrar resumen
    print("\n=== RESUMEN ===")
    print(f"✅ Propiedades procesadas: {procesados}")
    print(f"❌ Errores: {errores}")
    print(f"⚠️  Total advertencias: {advertencias_totales}")
    print(f"📊 Propiedades en repositorio: {len(repositorio)}")
    
    # 6. Análisis de campos
    print("\n=== ANÁLISIS DE CAMPOS ===")
    total_props = len(repositorio)
    analisis = {
        "con_precio_valido": 0,
        "con_colonia": 0,
        "con_calle": 0,
        "con_superficie": 0,
        "con_recamaras": 0,
        "con_banos": 0,
        "tipo_operacion": {},
        "tipo_propiedad": {}
    }
    
    # Contar campos
    for prop in repositorio.values():
        # Precio
        if "precio" in prop and isinstance(prop["precio"], dict):
            if prop["precio"].get("es_valido", False):
                analisis["con_precio_valido"] += 1
        
        # Ubicación
        if "ubicacion" in prop and isinstance(prop["ubicacion"], dict):
            if prop["ubicacion"].get("colonia"):
                analisis["con_colonia"] += 1
            if prop["ubicacion"].get("calle"):
                analisis["con_calle"] += 1
        
        # Superficie
        if "superficie" in prop and isinstance(prop["superficie"], dict):
            if prop["superficie"].get("terreno") or prop["superficie"].get("construccion"):
                analisis["con_superficie"] += 1
        
        # Características
        if "caracteristicas" in prop and isinstance(prop["caracteristicas"], dict):
            if prop["caracteristicas"].get("recamaras"):
                analisis["con_recamaras"] += 1
            if prop["caracteristicas"].get("banos"):
                analisis["con_banos"] += 1
        
        # Tipo operación y propiedad
        tipo_op = prop.get("tipo_operacion", "No especificado")
        tipo_prop = prop.get("tipo_propiedad", "No especificado")
        analisis["tipo_operacion"][tipo_op] = analisis["tipo_operacion"].get(tipo_op, 0) + 1
        analisis["tipo_propiedad"][tipo_prop] = analisis["tipo_propiedad"].get(tipo_prop, 0) + 1
    
    # Mostrar porcentajes
    print(f"Precio válido: {analisis['con_precio_valido']/total_props*100:.1f}%")
    print(f"Con colonia: {analisis['con_colonia']/total_props*100:.1f}%")
    print(f"Con calle: {analisis['con_calle']/total_props*100:.1f}%")
    print(f"Con superficie: {analisis['con_superficie']/total_props*100:.1f}%")
    print(f"Con recámaras: {analisis['con_recamaras']/total_props*100:.1f}%")
    print(f"Con baños: {analisis['con_banos']/total_props*100:.1f}%")
    
    print("\nTipos de operación:")
    for tipo, cantidad in sorted(analisis["tipo_operacion"].items()):
        print(f"  - {tipo}: {cantidad/total_props*100:.1f}%")
    
    print("\nTipos de propiedad:")
    for tipo, cantidad in sorted(analisis["tipo_propiedad"].items()):
        print(f"  - {tipo}: {cantidad/total_props*100:.1f}%")

if __name__ == "__main__":
    main() 