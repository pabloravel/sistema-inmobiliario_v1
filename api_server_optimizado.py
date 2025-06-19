#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor Inmobiliario AWS con Frontend Embebido
Versión completa con interfaz web integrada
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SERVIDOR API OPTIMIZADO PARA SISTEMA INMOBILIARIO
================================================

🏠 SISTEMA INMOBILIARIO COMPLETO v2.1.0
📅 Fecha: Junio 2025
👨‍💻 Desarrollado para: Agencia Inmobiliaria Cuernavaca

CARACTERÍSTICAS VERSIÓN 2.1.0:
- ✅ Catálogo de 4,270 propiedades estructuradas
- ✅ Sistema colaborativo con equipos y usuarios
- ✅ Gestión completa de contactos de vendedores
- ✅ Integración WhatsApp Business API
- ✅ Filtros avanzados por 32+ características
- ✅ API REST completa con autenticación JWT
- ✅ Sistema de prevención de corrupciones
- ✅ Dashboard en tiempo real
- ✅ Paginación eficiente y cache optimizado

HISTORIAL DE VERSIONES:
- v2.1.0: Sistema completo con WhatsApp + Versionado
- v2.0.0: Sistema colaborativo + Contactos + WhatsApp
- v1.2.0: Filtros avanzados + Características reales
- v1.1.0: Sistema de contactos independiente
- v1.0.0: API básica con catálogo de propiedades

TECNOLOGÍAS:
- Backend: Flask + SQLite
- Frontend: HTML5 + CSS3 + JavaScript
- Base de datos: SQLite (contactos + colaborativa)
- Integración: WhatsApp Business API
- Autenticación: JWT + Sessions

"""

import json
import gzip
import logging
import re
import threading
from flask import Flask, request, jsonify, Response, send_file, redirect
from flask_cors import CORS
from functools import lru_cache
from typing import Dict, List, Optional
import os
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path
import hashlib
import secrets
import jwt

# Cargar variables de entorno desde archivo .env
def cargar_env():
    try:
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()
            print("✅ Variables de entorno cargadas desde .env")
    except Exception as e:
        print(f"⚠️ Error cargando .env: {e}")

# Cargar variables de entorno al inicio
cargar_env()

# ============================================================================
# CONFIGURACIÓN Y METADATOS DEL SISTEMA
# ============================================================================

# Información de versión
VERSION_INFO = {
    "version": "2.5.0",
    "nombre": "Sistema Inmobiliario Completo",
    "fecha_release": "2025-06-08",
    "build": "2025.06.08.001",
    "autor": "Asistente IA Especializado",
    "cliente": "Agencia Inmobiliaria Cuernavaca",
    "descripcion": "Sistema completo con WhatsApp Business personalizado y colaboración",
    "changelog": [
        {
            "version": "2.5.0",
            "fecha": "2025-06-08",
            "cambios": [
                "✅ Sistema completo de gestión de usuarios implementado",
                "✅ Panel de administración funcional",
                "✅ Gestión de perfiles de usuario",
                "✅ Cambio de contraseñas seguro",
                "✅ Control de permisos por rol",
                "📱 Integración completa de WhatsApp Business API",
                "📱 Configuración visual de WhatsApp en Panel Admin",
                "📱 Envío automático de propiedades por WhatsApp",
                "📱 Fallback a WhatsApp Web cuando API no está configurada",
                "📱 Formateo inteligente de mensajes con imágenes",
                "🔧 Sincronización frontend-backend completa",
                "🔧 Mejoras en manejo de características como lista vs diccionario"
            ]
        },
        {
            "version": "2.1.1",
            "fecha": "2025-06-07",
            "cambios": [
                "✅ Mensajes WhatsApp personalizados con datos del asesor",
                "✅ Eliminado link al anuncio original y vendedor Facebook",
                "✅ Campo de información del asesor (logueado o manual)",
                "✅ Mensaje opcional personalizable para asesores",
                "🔧 Integración con sistema de autenticación"
            ]
        },
        {
            "version": "2.1.0",
            "fecha": "2025-06-07",
            "cambios": [
                "✅ Sistema de versionado implementado",
                "✅ Integración WhatsApp Business API completa",
                "✅ Envío de propiedades individuales y masivas",
                "✅ Formateo inteligente de mensajes",
                "✅ Modo simulación para desarrollo",
                "🔧 Endpoints de configuración WhatsApp"
            ]
        },
        {
            "version": "2.0.0", 
            "fecha": "2025-06-06",
            "cambios": [
                "✅ Sistema colaborativo con equipos",
                "✅ Autenticación JWT",
                "✅ Favoritos compartidos",
                "✅ Notificaciones en tiempo real",
                "✅ Gestión completa de contactos",
                "✅ Base de datos SQLite colaborativa"
            ]
        },
        {
            "version": "1.2.0",
            "fecha": "2025-06-05", 
            "cambios": [
                "✅ Filtros por 32+ características reales",
                "✅ Extracción inteligente de amenidades",
                "✅ Búsqueda por texto optimizada",
                "✅ Ordenamiento por precio",
                "🔧 Optimización de índices"
            ]
        },
        {
            "version": "1.1.0",
            "fecha": "2025-06-04",
            "cambios": [
                "✅ Sistema de contactos independiente",
                "✅ Base de datos SQLite para vendedores",
                "✅ Asociación propiedades-contactos",
                "✅ Historial de interacciones",
                "🔧 API CRUD completa"
            ]
        },
        {
            "version": "1.0.0",
            "fecha": "2025-06-03",
            "cambios": [
                "✅ API REST básica",
                "✅ Catálogo de 4,270 propiedades",
                "✅ Filtros por ciudad/tipo/precio",
                "✅ Paginación eficiente",
                "✅ Frontend básico funcionando"
            ]
        }
    ]
}

# Importar sistema de prevención
try:
    from sistema_prevencion_corrupciones import PreventorCorrupciones
    SISTEMA_PREVENCION_DISPONIBLE = True
except ImportError:
    SISTEMA_PREVENCION_DISPONIBLE = False

# Importar integración de WhatsApp
try:
    from whatsapp_integration import (
        WhatsAppAPI, 
        enviar_propiedad_por_whatsapp, 
        enviar_multiples_propiedades,
        verificar_configuracion as verificar_config_whatsapp,
        test_whatsapp
    )
    WHATSAPP_DISPONIBLE = True
except ImportError as e:
    print(f"⚠️ WhatsApp no disponible: {e}")
    WHATSAPP_DISPONIBLE = False



# Configuración
app = Flask(__name__)
CORS(app)

# Cache en memoria (para desarrollo, en producción usar Redis)
CACHE = {}
CACHE_TTL = {}
CACHE_DURATION = 300  # 5 minutos

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PropiedadesManager:
    def __init__(self, archivo_json: str):
        """Inicializa el gestor de propiedades."""
        self.archivo_json = archivo_json
        self.propiedades = []
        self.indices = {
            'ciudad': {},
            'tipo_propiedad': {},
            'tipo_operacion': {},
            'precio_rango': {}
        }
        self.cargar_datos()
        self.crear_indices()
    
    def cargar_datos(self):
        """Carga propiedades desde JSON."""
        try:
            logger.info(f"Cargando propiedades desde: {self.archivo_json}")
            with open(self.archivo_json, 'r', encoding='utf-8') as f:
                datos = json.load(f)
                # Verificar si es directamente una lista o tiene estructura {"propiedades": [...]}
                if isinstance(datos, list):
                    self.propiedades = datos
                elif isinstance(datos, dict):
                    # Si es un diccionario con IDs como claves, convertir a lista
                    if 'propiedades' in datos:
                        self.propiedades = datos['propiedades']
                    else:
                        # Es un diccionario con propiedades como valores
                        self.propiedades = list(datos.values())
                else:
                    self.propiedades = []
            logger.info(f"Cargadas {len(self.propiedades)} propiedades")
        except Exception as e:
            logger.error(f"Error cargando propiedades: {e}")
            self.propiedades = []
    
    def crear_indices(self):
        """Crea índices para búsquedas rápidas."""
        logger.info("Creando índices...")
        
        for i, prop in enumerate(self.propiedades):
            # Índice por ciudad - nuevo formato
            ciudad = prop.get('datos_originales', {}).get('ubicacion', {}).get('ciudad', 'Sin ciudad')
            if ciudad not in self.indices['ciudad']:
                self.indices['ciudad'][ciudad] = []
            self.indices['ciudad'][ciudad].append(i)
            
            # Índice por tipo de propiedad - extraer de descripción
            tipo_prop = 'Sin tipo'  # Default
            descripcion_original = prop.get('datos_originales', {}).get('descripcion', '').lower()
            
            # Determinar tipo de propiedad basado en descripción
            if any(palabra in descripcion_original for palabra in ['casa', 'residencia', 'chalet']):
                tipo_prop = 'Casa'
            elif any(palabra in descripcion_original for palabra in ['departamento', 'depto', 'apartamento']):
                tipo_prop = 'Departamento'
            elif any(palabra in descripcion_original for palabra in ['terreno', 'lote']):
                tipo_prop = 'Terreno'
            elif any(palabra in descripcion_original for palabra in ['local', 'comercial', 'oficina']):
                tipo_prop = 'Comercial'
            
            if tipo_prop not in self.indices['tipo_propiedad']:
                self.indices['tipo_propiedad'][tipo_prop] = []
            self.indices['tipo_propiedad'][tipo_prop].append(i)
            
            # Índice por tipo de operación - nuevo formato
            tipo_op = prop.get('tipo_operacion', 'Sin operación')
            if tipo_op not in self.indices['tipo_operacion']:
                self.indices['tipo_operacion'][tipo_op] = []
            self.indices['tipo_operacion'][tipo_op].append(i)
            
            # Índice por rango de precios - nuevo formato
            precio = 0
            precio_raw = prop.get('datos_originales', {}).get('precio', '0')
            
            # Manejar diferentes tipos de precio
            if isinstance(precio_raw, str) and precio_raw:
                # Limpiar el precio (remover $, comas, espacios, etc.)
                precio_limpio = precio_raw.replace('$', '').replace(',', '').replace(' ', '').replace('.', '')
                # Manejar formatos como "6980000" o "6.980.000"
                try:
                    precio = float(precio_limpio)
                except ValueError:
                    # Si falla, intentar extraer números usando regex
                    numeros = re.findall(r'\d+', precio_raw)
                    if numeros:
                        precio_limpio = ''.join(numeros)
                        try:
                            precio = float(precio_limpio)
                        except ValueError:
                            precio = 0
                    else:
                        precio = 0
            elif isinstance(precio_raw, (int, float)):
                precio = float(precio_raw)
            elif isinstance(precio_raw, dict):
                # Si es un diccionario, intentar extraer el valor
                precio = precio_raw.get('valor', 0)
                if isinstance(precio, str):
                    try:
                        precio = float(precio.replace('$', '').replace(',', ''))
                    except (ValueError, AttributeError):
                        precio = 0
                elif precio is None:
                    precio = 0
            
            # Asegurar que precio no sea None
            if precio is None:
                precio = 0
            
            rango = self.obtener_rango_precio(precio)
            if rango not in self.indices['precio_rango']:
                self.indices['precio_rango'][rango] = []
            self.indices['precio_rango'][rango].append(i)
        
        logger.info("Índices creados exitosamente")
    
    def obtener_rango_precio(self, precio: float) -> str:
        """Obtiene el rango de precio de una propiedad."""
        if precio < 500000:
            return "0-500k"
        elif precio < 1000000:
            return "500k-1M"
        elif precio < 2000000:
            return "1M-2M"
        elif precio < 5000000:
            return "2M-5M"
        else:
            return "5M+"
    
    def filtrar_propiedades(self, filtros: Dict) -> List[int]:
        """Filtra propiedades usando índices."""
        indices_validos = set(range(len(self.propiedades)))
        
        # Filtrar por ciudades
        if filtros.get('ciudades'):
            ciudades_indices = set()
            for ciudad in filtros['ciudades']:
                ciudades_indices.update(self.indices['ciudad'].get(ciudad, []))
            indices_validos = indices_validos.intersection(ciudades_indices)
        elif filtros.get('ciudad'):
            ciudad_indices = set(self.indices['ciudad'].get(filtros['ciudad'], []))
            indices_validos = indices_validos.intersection(ciudad_indices)
        
        # Filtrar por tipos de propiedad
        if filtros.get('tipos'):
            tipos_indices = set()
            for tipo in filtros['tipos']:
                tipos_indices.update(self.indices['tipo_propiedad'].get(tipo, []))
            indices_validos = indices_validos.intersection(tipos_indices)
        elif filtros.get('tipo_propiedad'):
            tipo_indices = set(self.indices['tipo_propiedad'].get(filtros['tipo_propiedad'], []))
            indices_validos = indices_validos.intersection(tipo_indices)
        
        # Filtrar por operaciones
        if filtros.get('operaciones'):
            operaciones_indices = set()
            for operacion in filtros['operaciones']:
                operaciones_indices.update(self.indices['tipo_operacion'].get(operacion, []))
            indices_validos = indices_validos.intersection(operaciones_indices)
        elif filtros.get('tipo_operacion'):
            op_indices = set(self.indices['tipo_operacion'].get(filtros['tipo_operacion'], []))
            indices_validos = indices_validos.intersection(op_indices)
        
        # Filtrar por precio
        if filtros.get('precio_min') or filtros.get('precio_max'):
            try:
                precio_min = float(filtros.get('precio_min', 0))
                precio_max = float(filtros.get('precio_max', float('inf')))
            except (ValueError, TypeError):
                precio_min = 0
                precio_max = float('inf')
            
            precio_indices = set()
            for i in indices_validos:
                prop = self.propiedades[i]
                precio_obj = prop.get('propiedad', {}).get('precio', {})
                
                # Manejar diferentes formatos de precio
                if isinstance(precio_obj, dict):
                    precio = precio_obj.get('valor', 0)
                elif isinstance(precio_obj, (int, float)):
                    precio = precio_obj
                else:
                    precio = 0
                
                # Asegurar que el precio sea numérico
                try:
                    if isinstance(precio, str):
                        precio = float(precio.replace(',', '').replace('$', ''))
                    else:
                        precio = float(precio) if precio else 0
                except (ValueError, TypeError):
                    precio = 0
                
                if precio_min <= precio <= precio_max:
                    precio_indices.add(i)
            indices_validos = indices_validos.intersection(precio_indices)
        
        # Filtrar por amenidades
        if filtros.get('amenidades'):
            amenidades_indices = set()
            for i in indices_validos:
                prop = self.propiedades[i]
                amenidades_prop = prop.get('amenidades', {})
                tiene_amenidades = True
                for amenidad in filtros['amenidades']:
                    if amenidad == 'alberca':
                        if not amenidades_prop.get('alberca', {}).get('presente', False):
                            tiene_amenidades = False
                            break
                    elif amenidad == 'jardin':
                        if not amenidades_prop.get('jardin', {}).get('presente', False):
                            tiene_amenidades = False
                            break
                    elif amenidad == 'seguridad':
                        desc = prop.get('descripcion_original', '').lower()
                        if 'seguridad' not in desc and 'vigilancia' not in desc:
                            tiene_amenidades = False
                            break
                    elif amenidad == 'area_comun':
                        desc = prop.get('descripcion_original', '').lower()
                        if 'área común' not in desc and 'areas comunes' not in desc:
                            tiene_amenidades = False
                            break
                
                if tiene_amenidades:
                    amenidades_indices.add(i)
            indices_validos = indices_validos.intersection(amenidades_indices)
        
        # Filtrar por características arquitectónicas
        if filtros.get('arquitectura'):
            arq_indices = set()
            for i in indices_validos:
                prop = self.propiedades[i]
                desc = prop.get('descripcion_original', '').lower()
                
                tiene_caracteristicas = True
                for arq in filtros['arquitectura']:
                    if 'recámara' in arq.lower():
                        match = re.search(r'(\d+)', arq)
                        if match:
                            num_deseado = int(match.group(1))
                            recamaras_patterns = [
                                r'(\d+)\s*(?:recámara|recamara|habitacion|dormitorio)',
                                r'(\d+)\s*(?:rec|hab|dorm)',
                                r'(\d+)\s*(?:bedroom|room)'
                            ]
                            encontrado = False
                            for pattern in recamaras_patterns:
                                recamaras_match = re.search(pattern, desc)
                                if recamaras_match:
                                    num_recamaras = int(recamaras_match.group(1))
                                    if num_recamaras == num_deseado:
                                        encontrado = True
                                    break
                            if not encontrado:
                                tiene_caracteristicas = False
                                break
                    elif 'baño' in arq.lower():
                        match = re.search(r'(\d+)', arq)
                        if match:
                            num_deseado = int(match.group(1))
                            banos_patterns = [
                                r'(\d+)\s*(?:baño|bano|bathroom)',
                                r'(\d+)\s*(?:bath|wc)'
                            ]
                            encontrado = False
                            for pattern in banos_patterns:
                                banos_match = re.search(pattern, desc)
                                if banos_match:
                                    num_banos = int(banos_match.group(1))
                                    if num_banos == num_deseado:
                                        encontrado = True
                                    break
                            if not encontrado:
                                tiene_caracteristicas = False
                                break
                    elif 'estacionamiento' in arq.lower():
                        match = re.search(r'(\d+)', arq)
                        if match:
                            num_deseado = int(match.group(1))
                            estac_patterns = [
                                r'(\d+)\s*(?:estacionamiento|cochera|garage|auto)',
                                r'(\d+)\s*(?:parking|car)'
                            ]
                            encontrado = False
                            for pattern in estac_patterns:
                                estac_match = re.search(pattern, desc)
                                if estac_match:
                                    num_estac = int(estac_match.group(1))
                                    if num_estac == num_deseado:
                                        encontrado = True
                                    break
                            if not encontrado:
                                tiene_caracteristicas = False
                                break
                    elif arq == '🏠 Un Nivel':
                        if not any(termino in desc for termino in ['un nivel', 'una planta', 'todo en planta baja', 'sin escaleras']):
                            tiene_caracteristicas = False
                            break
                    elif arq == '🛏️ Recámara en PB':
                        if not any(termino in desc for termino in ['recamara en planta baja', 'recámara pb', 'habitacion planta baja', 'dormitorio pb']):
                            tiene_caracteristicas = False
                            break
                    elif arq == '💧 Cisterna':
                        if not any(termino in desc for termino in ['cisterna', 'deposito de agua', 'tanque de agua', 'almacenamiento agua']):
                            tiene_caracteristicas = False
                            break
                
                if tiene_caracteristicas:
                    arq_indices.add(i)
            indices_validos = indices_validos.intersection(arq_indices)
        
        # Filtrar por documentación legal
        if filtros.get('legal'):
            legal_indices = set()
            for i in indices_validos:
                prop = self.propiedades[i]
                legal_info = prop.get('legal', {})
                
                tiene_documentacion = False
                for doc_tipo in filtros['legal']:
                    if doc_tipo == 'escrituras' and legal_info.get('escrituras', False):
                        tiene_documentacion = True
                        break
                    elif doc_tipo == 'cesion' and legal_info.get('cesion_derechos', False):
                        tiene_documentacion = True
                        break
                
                if tiene_documentacion:
                    legal_indices.add(i)
            
            indices_validos = indices_validos.intersection(legal_indices)
        
        # Filtrar por búsqueda de texto
        if filtros.get('busqueda'):
            termino_busqueda = filtros['busqueda'].lower()
            busqueda_indices = set()
            
            for i in indices_validos:
                prop = self.propiedades[i]
                descripcion = prop.get('datos_originales', {}).get('descripcion', '').lower()
                direccion_completa = prop.get('datos_originales', {}).get('ubicacion', {}).get('direccion_completa', '').lower()
                
                if termino_busqueda in descripcion or termino_busqueda in direccion_completa:
                    busqueda_indices.add(i)
            
            indices_validos = indices_validos.intersection(busqueda_indices)
        
        # Filtrar por texto general (parámetro 'q')
        if filtros.get('q'):
            texto_busqueda = filtros['q'].lower()
            texto_indices = set()
            for i in indices_validos:
                prop = self.propiedades[i]
                campos_busqueda = [
                    prop.get('descripcion_original', ''),
                    prop.get('ubicacion', {}).get('direccion_completa', ''),
                    prop.get('ubicacion', {}).get('ciudad', ''),
                    prop.get('propiedad', {}).get('tipo_propiedad', '')
                ]
                texto_completo = ' '.join(campos_busqueda).lower()
                if texto_busqueda in texto_completo:
                    texto_indices.add(i)
            indices_validos = indices_validos.intersection(texto_indices)
        
        return list(indices_validos)
    
    def obtener_propiedad_simplificada(self, indice: int) -> Dict:
        """Obtiene una versión simplificada de la propiedad para listados."""
        prop = self.propiedades[indice]
        
        # --- Precio - nuevo formato ------------------------------------------------------
        precio_obj = {}
        raw_precio = prop.get('datos_originales', {}).get('precio', '')
        
        if isinstance(raw_precio, str) and raw_precio:
            # Limpiar el precio (remover $, comas, espacios, etc.)
            precio_limpio = raw_precio.replace('$', '').replace(',', '').replace(' ', '').replace('.', '')
            try:
                valor = float(precio_limpio)
                precio_obj = {'valor': valor, 'moneda': 'MXN', 'texto': raw_precio}
            except ValueError:
                # Si falla, intentar extraer números usando regex
                numeros = re.findall(r'\d+', raw_precio)
                if numeros:
                    precio_limpio = ''.join(numeros)
                    try:
                        valor = float(precio_limpio)
                        precio_obj = {'valor': valor, 'moneda': 'MXN', 'texto': raw_precio}
                    except ValueError:
                        precio_obj = {'texto': raw_precio}
                else:
                    precio_obj = {'texto': raw_precio}
        elif isinstance(raw_precio, (int, float)):
            precio_obj = {'valor': float(raw_precio), 'moneda': 'MXN', 'texto': str(raw_precio)}
        elif isinstance(raw_precio, dict):
            # Si es un diccionario, intentar extraer el valor
            valor = raw_precio.get('valor', 0)
            if isinstance(valor, str):
                try:
                    valor = float(valor.replace('$', '').replace(',', ''))
                    precio_obj = {'valor': valor, 'moneda': 'MXN', 'texto': str(raw_precio)}
                except (ValueError, AttributeError):
                    precio_obj = {'texto': str(raw_precio)}
            elif isinstance(valor, (int, float)):
                precio_obj = {'valor': float(valor), 'moneda': 'MXN', 'texto': str(raw_precio)}
        # ----------------------------------------------------------------

        # --- Características - nuevo formato ---------------------------------------------
        caracteristicas = prop.get('datos_originales', {}).get('caracteristicas', {})
        if isinstance(caracteristicas, list):
            caracteristicas = {}
        # ----------------------------------------------------------------

        # --- Tipo de propiedad - extraer de descripción --------------------------------
        tipo_prop = 'Sin tipo'  # Default
        descripcion_original = prop.get('datos_originales', {}).get('descripcion', '').lower()
        
        # Determinar tipo de propiedad basado en descripción
        if any(palabra in descripcion_original for palabra in ['casa', 'residencia', 'chalet']):
            tipo_prop = 'Casa'
        elif any(palabra in descripcion_original for palabra in ['departamento', 'depto', 'apartamento']):
            tipo_prop = 'Departamento'
        elif any(palabra in descripcion_original for palabra in ['terreno', 'lote']):
            tipo_prop = 'Terreno'
        elif any(palabra in descripcion_original for palabra in ['local', 'comercial', 'oficina']):
            tipo_prop = 'Comercial'
        # ----------------------------------------------------------------

        return {
            'id': prop.get('datos_originales', {}).get('id'),
            'titulo': prop.get('datos_originales', {}).get('titulo', '')[:100],
            'tipo': tipo_prop,
            'url': prop.get('datos_originales', {}).get('link'),
            'descripcion': prop.get('datos_originales', {}).get('descripcion', ''),
            'descripcion_original': prop.get('datos_originales', {}).get('descripcion', ''),
            'precio': precio_obj,
            'tipo_propiedad': tipo_prop,
            'tipo_operacion': prop.get('tipo_operacion', 'Sin operación'),
            'operacion': prop.get('tipo_operacion', 'Sin operación'),
            'ciudad': prop.get('datos_originales', {}).get('ubicacion', {}).get('ciudad'),
            'colonia': prop.get('datos_originales', {}).get('ubicacion', {}).get('colonia'),
            'ubicacion': prop.get('datos_originales', {}).get('ubicacion', {}),
            'imagen_portada': prop.get('datos_originales', {}).get('imagen_portada', {}),
            'imagenes': prop.get('imagenes', []),
            'caracteristicas': caracteristicas
        }

# REINICIALIZAR COMPLETAMENTE - SOLUCIÓN TEMPORAL  
logger.info("🔄 REINICIALIZANDO PropiedadesManager para reflejar correcciones...")

# Limpiar referencias anteriores
import gc
gc.collect()

# Crear nueva instancia
propiedades_manager = PropiedadesManager('resultados/propiedades_estructuradas.json')

# Verificar datos cargados
logger.info(f"✅ Verificación post-inicialización:")
for op, indices in propiedades_manager.indices['tipo_operacion'].items():
    logger.info(f"   • {op}: {len(indices)} propiedades")

def is_cache_valid(cache_key: str) -> bool:
    """Verifica si el cache sigue vigente."""
    if cache_key not in CACHE_TTL:
        return False
    return datetime.now() < CACHE_TTL[cache_key]

def set_cache(cache_key: str, data):
    """Guarda datos en cache."""
    CACHE[cache_key] = data
    CACHE_TTL[cache_key] = datetime.now() + timedelta(seconds=CACHE_DURATION)

def get_cache(cache_key: str):
    """Obtiene datos del cache."""
    if is_cache_valid(cache_key):
        return CACHE[cache_key]
    return None

def comprimir_respuesta(data) -> Response:
    """Comprime la respuesta JSON - DESACTIVADO PARA DEBUG."""
    # json_str = json.dumps(data, ensure_ascii=False)
    # compressed = gzip.compress(json_str.encode('utf-8'))
    # 
    # response = Response(compressed)
    # response.headers['Content-Type'] = 'application/json'
    # response.headers['Content-Encoding'] = 'gzip'
    # return response
    return jsonify(data)

def ordenar_por_precio(indices: List[int], orden: str) -> List[int]:
    """Ordena los índices de propiedades por precio."""
    try:
        def obtener_precio(indice):
            try:
                prop = propiedades_manager.propiedades[indice]
                precio_raw = prop.get('datos_originales', {}).get('precio', '0')
                
                if isinstance(precio_raw, str) and precio_raw:
                    # Limpiar el precio (remover $, comas, espacios, etc.)
                    precio_limpio = precio_raw.replace('$', '').replace(',', '').replace(' ', '').replace('.', '')
                    try:
                        return float(precio_limpio)
                    except ValueError:
                        # Si falla, intentar extraer números usando regex
                        numeros = re.findall(r'\d+', precio_raw)
                        if numeros:
                            precio_limpio = ''.join(numeros)
                            try:
                                return float(precio_limpio)
                            except ValueError:
                                return 0
                        else:
                            return 0
                elif isinstance(precio_raw, (int, float)):
                    return float(precio_raw)
                elif isinstance(precio_raw, dict):
                    # Si es un diccionario, intentar extraer el valor
                    valor = precio_raw.get('valor', 0)
                    if isinstance(valor, str):
                        try:
                            return float(valor.replace('$', '').replace(',', ''))
                        except (ValueError, AttributeError):
                            return 0
                    elif isinstance(valor, (int, float)):
                        return float(valor)
                    else:
                        return 0
                else:
                    return 0
            except Exception as e:
                logger.warning(f"Error obteniendo precio para índice {indice}: {e}")
                return 0
        
        if orden == 'mayor_menor':
            return sorted(indices, key=obtener_precio, reverse=True)
        elif orden == 'menor_mayor':
            return sorted(indices, key=obtener_precio, reverse=False)
        else:
            return indices
    except Exception as e:
        logger.error(f"Error al ordenar por precio: {e}")
        return indices

@app.route('/api/propiedades', methods=['GET'])
def obtener_propiedades():
    """Endpoint principal para obtener propiedades con paginación."""
    try:
        # Parámetros de paginación
        pagina = int(request.args.get('pagina', 1))
        por_pagina_param = request.args.get('por_pagina', 20)
        if por_pagina_param == 'all':
            por_pagina = len(propiedades_manager.propiedades)  # Todas las propiedades
        else:
            por_pagina = min(int(por_pagina_param), 500)  # Máximo 500
        
        # Filtros (manejar tanto formatos múltiples como individuales)
        filtros = {}
        
        # Manejar filtros múltiples desde frontend con checkboxes
        if request.args.get('ciudades'):
            filtros['ciudades'] = request.args.get('ciudades').split(',')
        elif request.args.get('ciudad'):
            filtros['ciudad'] = request.args.get('ciudad')
            
        if request.args.get('tipos'):
            filtros['tipos'] = request.args.get('tipos').split(',')
        elif request.args.get('tipo_propiedad'):
            filtros['tipo_propiedad'] = request.args.get('tipo_propiedad')
            
        if request.args.get('operaciones'):
            filtros['operaciones'] = request.args.get('operaciones').split(',')
        elif request.args.get('tipo_operacion'):
            filtros['tipo_operacion'] = request.args.get('tipo_operacion')
        
        # Filtros de precio
        if request.args.get('precio_min'):
            filtros['precio_min'] = request.args.get('precio_min', type=float)
        if request.args.get('precio_max'):
            filtros['precio_max'] = request.args.get('precio_max', type=float)
        
        # Nuevos filtros
        if request.args.get('amenidades'):
            filtros['amenidades'] = request.args.get('amenidades').split(',')
        if request.args.get('arquitectura'):
            filtros['arquitectura'] = request.args.get('arquitectura').split(',')
        if request.args.get('legal'):
            filtros['legal'] = request.args.get('legal').split(',')
        
        # Filtro de búsqueda por texto
        if request.args.get('q'):
            filtros['busqueda'] = request.args.get('q')
        
        # Ordenamiento por precio
        orden_precio = request.args.get('orden_precio')
        
        # Crear clave de cache incluyendo ordenamiento
        cache_key = f"propiedades_{pagina}_{por_pagina}_{orden_precio}_{hash(str(filtros))}"
        
        # Intentar obtener del cache - TEMPORALMENTE DESHABILITADO
        # cached_result = get_cache(cache_key)
        # if cached_result:
        #                     return jsonify(cached_result)
        
        # Filtrar propiedades
        indices_filtrados = propiedades_manager.filtrar_propiedades(filtros)
        
        # Aplicar ordenamiento por precio si se solicita
        if orden_precio:
            indices_filtrados = ordenar_por_precio(indices_filtrados, orden_precio)
        
        total = len(indices_filtrados)
        
        # Calcular paginación
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        indices_pagina = indices_filtrados[inicio:fin]
        
        # Obtener propiedades simplificadas
        propiedades = [
            propiedades_manager.obtener_propiedad_simplificada(i) 
            for i in indices_pagina
        ]
        
        resultado = {
            'propiedades': propiedades,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': (total + por_pagina - 1) // por_pagina,
            'tiene_siguiente': fin < total,
            'tiene_anterior': pagina > 1,
            'paginacion': {
                'pagina': pagina,
                'por_pagina': por_pagina,
                'total_paginas': (total + por_pagina - 1) // por_pagina,
                'tiene_siguiente': fin < total,
                'tiene_anterior': pagina > 1
            },
            'estadisticas': {
                'total': total,
                'mostrando': len(propiedades)
            }
        }
        
        # Guardar en cache
        set_cache(cache_key, resultado)
        
        # Temporalmente sin compresión para debugging
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en obtener_propiedades: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/propiedades/<propiedad_id>', methods=['GET', 'DELETE'])
def manejar_propiedad(propiedad_id: str):
    """Maneja una propiedad específica (obtener o eliminar)."""
    try:
        if request.method == 'GET':
            # Buscar propiedad por ID - nuevo formato
            for prop in propiedades_manager.propiedades:
                if prop.get('datos_originales', {}).get('id') == propiedad_id:
                    return jsonify(prop)
            return jsonify({'error': 'Propiedad no encontrada'}), 404
        elif request.method == 'DELETE':
            # Eliminar propiedad del repositorio usando el nuevo sistema con contactos
            if eliminar_propiedad_con_contactos(propiedad_id):
                return jsonify({'mensaje': 'Propiedad eliminada exitosamente y desasociada de contactos'}), 200
            else:
                return jsonify({'error': 'Propiedad no encontrada'}), 404
    except Exception as e:
        logger.error(f"Error en manejar_propiedad: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# ALIASES SIN /api/ PARA COMPATIBILIDAD CON FRONTEND
@app.route('/propiedades', methods=['GET'])
def obtener_propiedades_alias():
    """Alias del endpoint principal para compatibilidad con frontend."""
    return obtener_propiedades()

@app.route('/estadisticas', methods=['GET'])
def obtener_estadisticas_alias():
    """Alias del endpoint de estadísticas para compatibilidad con frontend."""
    return obtener_estadisticas()

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtiene estadísticas generales del catálogo."""
    try:
        # LECTURA DIRECTA DEL ARCHIVO - BYPASS COMPLETO DE CLASES
        logger.info("🔄 Leyendo archivo directamente...")
        with open('resultados/propiedades_estructuradas.json', 'r', encoding='utf-8') as f:
            datos = json.load(f)
            # Verificar si es directamente una lista o tiene estructura {"propiedades": [...]}
            if isinstance(datos, list):
                propiedades = datos
            else:
                propiedades = datos.get('propiedades', [])
        
        logger.info(f"📊 Archivo leído: {len(propiedades)} propiedades")
        
        # Contar operaciones directamente
        operaciones = {}
        ciudades = {}
        tipos = {}
        rangos_precio = {}
        caracteristicas_numericas = {
            'recamaras': {},
            'banos': {},
            'estacionamientos': {}
        }
        caracteristicas_booleanas = {}
        
        for prop in propiedades:
            # Operaciones - nuevo formato
            op = prop.get('tipo_operacion', 'sin tipo')
            operaciones[op] = operaciones.get(op, 0) + 1
            
            # Ciudades - nuevo formato
            ciudad = prop.get('datos_originales', {}).get('ubicacion', {}).get('ciudad', 'Sin ciudad')
            ciudades[ciudad] = ciudades.get(ciudad, 0) + 1
            
            # Tipos - extraer de características o descripción
            tipo = 'Sin tipo'  # Default
            caracteristicas = prop.get('datos_originales', {}).get('caracteristicas', {})
            descripcion_original = prop.get('datos_originales', {}).get('descripcion', '').lower()
            
            # Determinar tipo de propiedad basado en descripción
            if any(palabra in descripcion_original for palabra in ['casa', 'residencia', 'chalet']):
                tipo = 'Casa'
            elif any(palabra in descripcion_original for palabra in ['departamento', 'depto', 'apartamento']):
                tipo = 'Departamento'
            elif any(palabra in descripcion_original for palabra in ['terreno', 'lote']):
                tipo = 'Terreno'
            elif any(palabra in descripcion_original for palabra in ['local', 'comercial', 'oficina']):
                tipo = 'Comercial'
            
            tipos[tipo] = tipos.get(tipo, 0) + 1
            
            # Rangos de precio - nuevo formato
            precio_raw = prop.get('datos_originales', {}).get('precio', '0')
            precio = 0
            
            if isinstance(precio_raw, str) and precio_raw:
                # Limpiar el precio (remover $, comas, espacios, etc.)
                precio_limpio = precio_raw.replace('$', '').replace(',', '').replace(' ', '').replace('.', '')
                # Manejar formatos como "6980000" o "6.980.000"
                try:
                    precio = float(precio_limpio)
                except ValueError:
                    # Si falla, intentar extraer números usando regex
                    numeros = re.findall(r'\d+', precio_raw)
                    if numeros:
                        precio_limpio = ''.join(numeros)
                        try:
                            precio = float(precio_limpio)
                        except ValueError:
                            precio = 0
                    else:
                        precio = 0
            elif isinstance(precio_raw, (int, float)):
                precio = float(precio_raw)
            elif isinstance(precio_raw, dict):
                # Si es un diccionario, intentar extraer el valor
                precio = precio_raw.get('valor', 0)
                if isinstance(precio, str):
                    try:
                        precio = float(precio.replace('$', '').replace(',', ''))
                    except (ValueError, AttributeError):
                        precio = 0
                elif precio is None:
                    precio = 0
            
            # Asegurar que precio no sea None
            if precio is None:
                precio = 0
            
            if precio < 500000:
                rango = "0-500k"
            elif precio < 1000000:
                rango = "500k-1M"
            elif precio < 2000000:
                rango = "1M-2M"
            elif precio < 5000000:
                rango = "2M-5M"
            else:
                rango = "5M+"
            rangos_precio[rango] = rangos_precio.get(rango, 0) + 1
            
            # Extraer características numéricas de la descripción - nuevo formato
            descripcion = prop.get('datos_originales', {}).get('descripcion', '').lower()
            
            # Buscar recámaras con múltiples patrones
            recamaras_patterns = [
                r'(\d+)\s*(?:recámara|recamara|habitacion|dormitorio)',
                r'(\d+)\s*(?:rec|hab|dorm)',
                r'(\d+)\s*(?:bedroom|room)'
            ]
            for pattern in recamaras_patterns:
                recamaras_match = re.search(pattern, descripcion)
                if recamaras_match:
                    num_recamaras = int(recamaras_match.group(1))
                    if 1 <= num_recamaras <= 10:  # Validar rango razonable
                        key = f"{num_recamaras} Recámara{'s' if num_recamaras > 1 else ''}"
                        caracteristicas_numericas['recamaras'][key] = caracteristicas_numericas['recamaras'].get(key, 0) + 1
                    break
            
            # Buscar baños con múltiples patrones
            banos_patterns = [
                r'(\d+)\s*(?:baño|bano|bathroom)',
                r'(\d+)\s*(?:bath|wc)'
            ]
            for pattern in banos_patterns:
                banos_match = re.search(pattern, descripcion)
                if banos_match:
                    try:
                        num_banos = float(banos_match.group(1))
                        if 1 <= num_banos <= 10:  # Validar rango razonable
                            if num_banos == int(num_banos):
                                key = f"{int(num_banos)} Baño{'s' if num_banos > 1 else ''}"
                            else:
                                key = f"{num_banos} Baños"
                            caracteristicas_numericas['banos'][key] = caracteristicas_numericas['banos'].get(key, 0) + 1
                        break
                    except ValueError:
                        continue
            
            # Buscar estacionamientos con múltiples patrones
            estac_patterns = [
                r'(\d+)\s*(?:estacionamiento|cochera|garage|auto)',
                r'(\d+)\s*(?:parking|car)',
                r'cochera\s*(?:para\s*)?(\d+)',
                r'garage\s*(?:para\s*)?(\d+)'
            ]
            for pattern in estac_patterns:
                estac_match = re.search(pattern, descripcion)
                if estac_match:
                    num_estac = int(estac_match.group(1))
                    if 1 <= num_estac <= 10:  # Validar rango razonable
                        key = f"{num_estac} Estacionamiento{'s' if num_estac > 1 else ''}"
                        caracteristicas_numericas['estacionamientos'][key] = caracteristicas_numericas['estacionamientos'].get(key, 0) + 1
                    break
            
            # Características booleanas reales - buscar en descripción para verificar si realmente las tiene
            descripcion_completa = prop.get('datos_originales', {}).get('descripcion', '').lower()
            
            # Verificar un nivel - buscar indicios reales
            if any(termino in descripcion_completa for termino in ['un nivel', 'una planta', 'todo en planta baja', 'sin escaleras']):
                caracteristicas_booleanas['un_nivel'] = caracteristicas_booleanas.get('un_nivel', 0) + 1
            
            # Verificar recámara en planta baja
            if any(termino in descripcion_completa for termino in ['recamara en planta baja', 'recámara pb', 'habitacion planta baja', 'dormitorio pb']):
                caracteristicas_booleanas['recamara_en_pb'] = caracteristicas_booleanas.get('recamara_en_pb', 0) + 1
            
            # Verificar cisterna
            if any(termino in descripcion_completa for termino in ['cisterna', 'deposito de agua', 'tanque de agua', 'almacenamiento agua']):
                caracteristicas_booleanas['cisterna'] = caracteristicas_booleanas.get('cisterna', 0) + 1
        
        # Combinar características numéricas y booleanas
        caracteristicas_finales = {}
        
        # Agregar características numéricas SOLAMENTE si tienen valores
        for categoria, valores in caracteristicas_numericas.items():
            if valores:  # Solo agregar si realmente tiene datos
                caracteristicas_finales.update(valores)
        
        # Agregar características booleanas REALES (detectadas por descripción)
        for carac, count in caracteristicas_booleanas.items():
            if count > 0:  # Solo agregar si realmente se encontraron
                # Reformatear nombres para que sean más descriptivos
                if carac == 'un_nivel':
                    caracteristicas_finales['🏠 Un Nivel'] = count
                elif carac == 'recamara_en_pb':
                    caracteristicas_finales['🛏️ Recámara en PB'] = count
                elif carac == 'cisterna':
                    caracteristicas_finales['💧 Cisterna'] = count
        
        logger.info("📊 Distribución calculada directamente:")
        for op, count in operaciones.items():
            logger.info(f"   • {op}: {count}")
        
        stats = {
            'total': len(propiedades),
            'total_propiedades': len(propiedades),
            'por_ciudad': ciudades,
            'por_tipo': tipos,
            'por_operacion': operaciones,
            'por_tipo_operacion': operaciones,  # Alias para compatibilidad
            'por_rango_precio': rangos_precio,
            'por_caracteristica': caracteristicas_finales,
            # Estructura de filtros para el frontend
            'filtros': {
                'operaciones': operaciones,
                'ciudades': ciudades,
                'tipos': tipos,
                'amenidades': caracteristicas_finales,
                'caracteristicas': caracteristicas_finales,
                'legal': {}  # Placeholder para documentación legal
            }
        }
        
        return jsonify(stats)
        
    except Exception as e:
        logger.error(f"Error en obtener_estadisticas: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/buscar', methods=['GET'])
def buscar_propiedades():
    """Búsqueda de texto en propiedades."""
    try:
        termino = request.args.get('q', '').lower()
        if not termino or len(termino) < 2:
            return jsonify({'error': 'Término de búsqueda muy corto'}), 400
        
        pagina = int(request.args.get('pagina', 1))
        por_pagina_param = request.args.get('por_pagina', 20)
        if por_pagina_param == 'all':
            por_pagina = len(propiedades_manager.propiedades)
        else:
            por_pagina = min(int(por_pagina_param), 500)
        
        # Buscar en descripciones y direcciones completas - nuevo formato
        resultados = []
        for i, prop in enumerate(propiedades_manager.propiedades):
            descripcion = prop.get('datos_originales', {}).get('descripcion', '').lower()
            direccion_completa = prop.get('datos_originales', {}).get('ubicacion', {}).get('direccion_completa', '').lower()
            titulo = prop.get('datos_originales', {}).get('titulo', '').lower()
            
            if termino in descripcion or termino in direccion_completa or termino in titulo:
                resultados.append(i)
        
        # Paginar resultados
        total = len(resultados)
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        indices_pagina = resultados[inicio:fin]
        
        propiedades = [
            propiedades_manager.obtener_propiedad_simplificada(i) 
            for i in indices_pagina
        ]
        
        resultado = {
            'propiedades': propiedades,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': (total + por_pagina - 1) // por_pagina,
            'termino': termino
        }
        
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en buscar_propiedades: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/Imagen_no_disponible.jpg')
def servir_imagen_defecto():
    """Sirve la imagen por defecto."""
    try:
        imagen_default = 'Imagen_no_disponible.jpg'
        if os.path.exists(imagen_default):
            return send_file(imagen_default)
        else:
            logger.warning("Imagen por defecto no encontrada")
            return '', 404
    except Exception as e:
        logger.error(f"Error sirviendo imagen por defecto: {e}")
        return '', 404

@app.route('/resultados/<path:filename>')
def servir_imagen(filename):
    """Sirve imágenes desde el directorio de resultados."""
    try:
        archivo_path = os.path.join('resultados', filename)
        if os.path.exists(archivo_path):
            return send_file(archivo_path)
        else:
            # Redirigir a imagen por defecto
            imagen_default = 'Imagen_no_disponible.jpg'
            if os.path.exists(imagen_default):
                return send_file(imagen_default)
            else:
                logger.warning(f"Imagen no encontrada: {filename}")
                return '', 404
    except Exception as e:
        logger.error(f"Error sirviendo imagen {filename}: {e}")
        return '', 404

@app.route('/api/estadisticas-debug', methods=['GET'])
def obtener_estadisticas_debug():
    """DEBUG: Lee directamente el archivo sin cache ni clases."""
    try:
        import json
        with open('resultados/propiedades_estructuradas.json', 'r', encoding='utf-8') as f:
            datos = json.load(f)
            # Verificar si es directamente una lista o tiene estructura {"propiedades": [...]}
            if isinstance(datos, list):
                propiedades = datos
            else:
                propiedades = datos.get('propiedades', [])
        
        # Contar operaciones directamente - nuevo formato
        operaciones = {}
        for prop in propiedades:
            op = prop.get('tipo_operacion', 'sin tipo')
            operaciones[op] = operaciones.get(op, 0) + 1
        
        return jsonify({
            'total_propiedades': len(propiedades),
            'por_operacion': operaciones,
            'debug': 'Lectura directa del archivo'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de salud del servicio."""
    return jsonify({
        'status': 'healthy',
        'version': VERSION_INFO['version'],
        'build': VERSION_INFO['build'],
        'propiedades_cargadas': len(propiedades_manager.propiedades),
        'timestamp': datetime.now().isoformat(),
        'uptime': 'Sistema funcionando correctamente'
    })

@app.route('/api/version', methods=['GET'])
def obtener_version():
    """Endpoint para obtener información de versión completa."""
    return jsonify(VERSION_INFO)

@app.route('/api/changelog', methods=['GET'])
def obtener_changelog():
    """Endpoint para obtener historial de cambios."""
    return jsonify({
        'changelog': VERSION_INFO['changelog'],
        'version_actual': VERSION_INFO['version'],
        'total_versiones': len(VERSION_INFO['changelog'])
    })

@app.route('/frontend_desarrollo.html')
def servir_frontend():
    """Sirve el archivo HTML del frontend"""
    try:
        return send_file('frontend_desarrollo.html', mimetype='text/html')
    except FileNotFoundError:
        # Si no encuentra el archivo principal, usar el backup
        try:
            with open('temp_frontend_content.html', 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html'}
        except Exception as e:
            logger.error(f"Error sirviendo frontend desde backup: {e}")
            return f"Error sirviendo frontend: {str(e)}", 500
    except Exception as e:
        logger.error(f"Error sirviendo frontend: {e}")
        return f"Error sirviendo frontend: {str(e)}", 500

@app.route('/frontend_FUNCIONAL.html')
def servir_frontend_funcional():
    """Sirve el frontend funcional"""
    try:
        return send_file('frontend_FUNCIONAL.html', mimetype='text/html')
    except FileNotFoundError:
        return "Frontend funcional no encontrado", 404
    except Exception as e:
        logger.error(f"Error sirviendo frontend funcional: {e}")
        return f"Error sirviendo frontend funcional: {str(e)}", 500

@app.route('/')
def index():
    """Sirve el frontend completo embebido"""
    try:
        # Servir el frontend embebido directamente
        return """<!DOCTYPE html>
<html lang=\"es\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>Sistema Inmobiliario AWS - Catálogo Completo</title>
    <style>
        :root {
            --primary: #2563eb;
            --secondary: #64748b;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --light: #f8fafc;
            --dark: #1e293b;
            --border: #e2e8f0;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", system-ui, sans-serif;
            background: var(--light);
            color: var(--dark);
            line-height: 1.6;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 1rem;
        }

        /* Header */
        .header {
            background: var(--primary);
            color: white;
            padding: 1rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: rgba(255,255,255,0.1);
            border-radius: 6px;
            font-size: 0.9rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* Layout principal */
        .main-layout {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 2rem;
            margin-top: 2rem;
            min-height: calc(100vh - 140px);
            align-items: start;
        }

        /* Panel de filtros */
        .filters-panel {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            height: fit-content;
        }

        .filter-group {
            margin-bottom: 1.5rem;
        }

        .filter-group label {
            display: block;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--dark);
        }

        .filter-group select,
        .filter-group input {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 0.9rem;
        }

        .btn {
            background: var(--primary);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: background 0.2s;
            width: 100%;
        }

        .btn:hover {
            background: #1d4ed8;
        }

        /* Grid de propiedades */
        .properties-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1.5rem;
        }

        .property-card {
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .property-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .property-image {
            width: 100%;
            height: 200px;
            object-fit: cover;
            background: #f0f0f0;
        }

        .property-content {
            padding: 1rem;
        }

        .property-price {
            font-size: 1.25rem;
            font-weight: bold;
            color: var(--primary);
            margin-bottom: 0.5rem;
        }

        .property-location {
            color: var(--secondary);
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }

        .property-description {
            font-size: 0.9rem;
            line-height: 1.4;
            color: var(--dark);
            display: -webkit-box;
            -webkit-line-clamp: 3;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }

        /* Loading y estados */
        .loading {
            text-align: center;
            padding: 2rem;
            color: var(--secondary);
        }

        .error {
            background: #fee2e2;
            color: #dc2626;
            padding: 1rem;
            border-radius: 6px;
            margin: 1rem 0;
        }

        /* Paginación */
        .pagination {
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin: 2rem 0;
        }

        .pagination button {
            padding: 0.5rem 1rem;
            border: 1px solid var(--border);
            background: white;
            border-radius: 4px;
            cursor: pointer;
        }

        .pagination button.active {
            background: var(--primary);
            color: white;
            border-color: var(--primary);
        }

        .pagination button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .main-layout {
                grid-template-columns: 1fr;
                gap: 1rem;
            }
            
            .properties-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class=\"header\">
        <div class=\"container\">
            <h1>🏠 Sistema Inmobiliario AWS</h1>
            <div class=\"status-indicator\">
                <div class=\"status-dot\"></div>
                <span id=\"status-text\">Cargando sistema...</span>
            </div>
        </div>
    </div>

    <div class=\"container\">
        <div class=\"main-layout\">
            <!-- Panel de filtros -->
            <div class=\"filters-panel\">
                <h3>🔍 Filtros</h3>
                
                <div class=\"filter-group\">
                    <label for=\"operacion\">Tipo de Operación</label>
                    <select id=\"operacion\">
                        <option value=\"\">Todas</option>
                        <option value=\"venta\">Venta</option>
                        <option value=\"renta\">Renta</option>
                    </select>
                </div>

                <div class=\"filter-group\">
                    <label for=\"precio-min\">Precio Mínimo</label>
                    <input type=\"number\" id=\"precio-min\" placeholder=\"Ej: 1000000\">
                </div>

                <div class=\"filter-group\">
                    <label for=\"precio-max\">Precio Máximo</label>
                    <input type=\"number\" id=\"precio-max\" placeholder=\"Ej: 5000000\">
                </div>

                <div class=\"filter-group\">
                    <label for=\"ciudad\">Ciudad</label>
                    <select id=\"ciudad\">
                        <option value=\"\">Todas las ciudades</option>
                    </select>
                </div>

                <button class=\"btn\" onclick=\"aplicarFiltros()\">Aplicar Filtros</button>
                <button class=\"btn\" onclick=\"limpiarFiltros()\" style=\"background: var(--secondary); margin-top: 0.5rem;\">Limpiar</button>
            </div>

            <!-- Contenido principal -->
            <div class=\"content\">
                <div id=\"loading\" class=\"loading\">
                    <p>🔄 Cargando propiedades...</p>
                </div>

                <div id=\"error\" class=\"error\" style=\"display: none;\">
                    <p>❌ Error cargando propiedades. <button onclick=\"cargarPropiedades()\">Reintentar</button></p>
                </div>

                <div id=\"properties-container\">
                    <div class=\"properties-grid\" id=\"properties-grid\">
                        <!-- Las propiedades se cargarán aquí -->
                    </div>
                </div>

                <div class=\"pagination\" id=\"pagination\">
                    <!-- La paginación se generará aquí -->
                </div>
            </div>
        </div>
    </div>

    <script>
        // Variables globales
        let propiedades = [];
        let propiedadesFiltradas = [];
        let paginaActual = 1;
        const propiedadesPorPagina = 24;

        // Inicializar aplicación
        document.addEventListener('DOMContentLoaded', function() {
            verificarEstado();
            cargarPropiedades();
            cargarCiudades();
        });

        // Verificar estado del sistema
        async function verificarEstado() {
            try {
                const response = await fetch('/health');
                const data = await response.json();
                
                if (data.propiedades) {
                    document.getElementById('status-text').textContent = 
                        `✅ Sistema funcionando - ${data.propiedades} propiedades`;
                }
            } catch (error) {
                document.getElementById('status-text').textContent = '⚠️ Verificando estado...';
            }
        }

        // Cargar propiedades
        async function cargarPropiedades(pagina = 1) {
            try {
                document.getElementById('loading').style.display = 'block';
                document.getElementById('error').style.display = 'none';
                
                const response = await fetch(`/api/propiedades?pagina=${pagina}&por_pagina=${propiedadesPorPagina}`);
                const data = await response.json();
                
                if (data.propiedades) {
                    propiedades = data.propiedades;
                    propiedadesFiltradas = [...propiedades];
                    mostrarPropiedades();
                    generarPaginacion(data.total_paginas, pagina);
                    
                    document.getElementById('loading').style.display = 'none';
                } else {
                    throw new Error('No se pudieron cargar las propiedades');
                }
            } catch (error) {
                console.error('Error cargando propiedades:', error);
                document.getElementById('loading').style.display = 'none';
                document.getElementById('error').style.display = 'block';
            }
        }

        // Mostrar propiedades en el grid
        function mostrarPropiedades() {
            const grid = document.getElementById('properties-grid');
            
            if (propiedadesFiltradas.length === 0) {
                grid.innerHTML = '<div class=\"loading\">No se encontraron propiedades con los filtros aplicados.</div>';
                return;
            }

            grid.innerHTML = propiedadesFiltradas.map(propiedad => {
                const precio = propiedad.propiedad?.precio?.formato || 'Precio por consultar';
                const ubicacion = propiedad.ubicacion?.direccion_completa || 'Ubicación no disponible';
                const descripcion = propiedad.descripcion_original || 'Sin descripción';
                const imagen = propiedad.imagen_portada?.ruta_relativa 
                    ? `/resultados/${propiedad.imagen_portada.ruta_relativa}`
                    : '/Imagen_no_disponible.jpg';

                return `
                    <div class=\"property-card\">
                        <img src=\"${imagen}\" alt=\"Propiedad\" class=\"property-image\" 
                             onerror=\"this.src='/Imagen_no_disponible.jpg'\">
                        <div class=\"property-content\">
                            <div class=\"property-price\">${precio}</div>
                            <div class=\"property-location\">📍 ${ubicacion}</div>
                            <div class=\"property-description\">${descripcion}</div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Cargar ciudades para el filtro
        async function cargarCiudades() {
            try {
                const response = await fetch('/api/estadisticas');
                const data = await response.json();
                
                if (data.ciudades) {
                    const select = document.getElementById('ciudad');
                    Object.keys(data.ciudades).forEach(ciudad => {
                        const option = document.createElement('option');
                        option.value = ciudad;
                        option.textContent = `${ciudad} (${data.ciudades[ciudad]})`;
                        select.appendChild(option);
                    });
                }
            } catch (error) {
                console.error('Error cargando ciudades:', error);
            }
        }

        // Aplicar filtros
        function aplicarFiltros() {
            const operacion = document.getElementById('operacion').value;
            const precioMin = parseFloat(document.getElementById('precio-min').value) || 0;
            const precioMax = parseFloat(document.getElementById('precio-max').value) || Infinity;
            const ciudad = document.getElementById('ciudad').value;

            propiedadesFiltradas = propiedades.filter(propiedad => {
                // Filtro por operación
                if (operacion && propiedad.operacion !== operacion) {
                    return false;
                }

                // Filtro por precio
                const precio = propiedad.propiedad?.precio?.valor || 0;
                if (precio < precioMin || precio > precioMax) {
                    return false;
                }

                // Filtro por ciudad
                if (ciudad && propiedad.ubicacion?.ciudad !== ciudad) {
                    return false;
                }

                return true;
            });

            mostrarPropiedades();
        }

        // Limpiar filtros
        function limpiarFiltros() {
            document.getElementById('operacion').value = '';
            document.getElementById('precio-min').value = '';
            document.getElementById('precio-max').value = '';
            document.getElementById('ciudad').value = '';
            
            propiedadesFiltradas = [...propiedades];
            mostrarPropiedades();
        }

        // Generar paginación
        function generarPaginacion(totalPaginas, paginaActual) {
            const pagination = document.getElementById('pagination');
            
            if (totalPaginas <= 1) {
                pagination.innerHTML = '';
                return;
            }

            let html = '';
            
            // Botón anterior
            html += `<button onclick=\"cargarPropiedades(${paginaActual - 1})\" 
                     ${paginaActual <= 1 ? 'disabled' : ''}>‹ Anterior</button>`;
            
            // Páginas
            const inicio = Math.max(1, paginaActual - 2);
            const fin = Math.min(totalPaginas, paginaActual + 2);
            
            for (let i = inicio; i <= fin; i++) {
                html += `<button onclick=\"cargarPropiedades(${i})\" 
                         ${i === paginaActual ? 'class=\"active\"' : ''}>${i}</button>`;
            }
            
            // Botón siguiente
            html += `<button onclick=\"cargarPropiedades(${paginaActual + 1})\" 
                     ${paginaActual >= totalPaginas ? 'disabled' : ''}>Siguiente ›</button>`;
            
            pagination.innerHTML = html;
        }
    </script>
</body>
</html> """, 200, {'Content-Type': 'text/html'}
    except Exception as e:
        logger.error(f"Error sirviendo página: {e}")
        return "Error interno del servidor", 500

# ============================================================================
# SISTEMA DE CONTACTOS INDEPENDIENTE - FASE 1
# ============================================================================

class ContactosManager:
    def __init__(self, db_path: str = 'contactos_vendedores.db'):
        """Inicializa el gestor de contactos con base de datos SQLite."""
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Crea las tablas necesarias para contactos."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS contactos (
                        id TEXT PRIMARY KEY,
                        nombre TEXT NOT NULL,
                        telefono TEXT,
                        email TEXT,
                        perfil_facebook TEXT,
                        whatsapp TEXT,
                        comision_porcentaje REAL,
                        notas TEXT,
                        calificacion INTEGER DEFAULT 0,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        activo BOOLEAN DEFAULT 1
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS propiedades_contactos (
                        propiedad_id TEXT,
                        contacto_id TEXT,
                        fecha_asociacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (propiedad_id, contacto_id),
                        FOREIGN KEY (contacto_id) REFERENCES contactos (id)
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS interacciones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contacto_id TEXT,
                        tipo_interaccion TEXT,
                        descripcion TEXT,
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (contacto_id) REFERENCES contactos (id)
                    )
                ''')
                
                logger.info("Base de datos de contactos inicializada")
        except Exception as e:
            logger.error(f"Error inicializando base de datos de contactos: {e}")
    
    def crear_contacto(self, datos_contacto: Dict) -> Dict:
        """Crea un nuevo contacto."""
        try:
            # Generar ID único basado en teléfono o nombre
            telefono = datos_contacto.get('telefono', '').replace(' ', '').replace('-', '')
            contacto_id = f"vendor_{telefono}" if telefono else f"vendor_{hash(datos_contacto.get('nombre', ''))}"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO contactos 
                    (id, nombre, telefono, email, perfil_facebook, whatsapp, comision_porcentaje, notas, calificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    contacto_id,
                    datos_contacto.get('nombre', ''),
                    datos_contacto.get('telefono', ''),
                    datos_contacto.get('email', ''),
                    datos_contacto.get('perfil_facebook', ''),
                    datos_contacto.get('whatsapp', ''),
                    datos_contacto.get('comision_porcentaje', 0),
                    datos_contacto.get('notas', ''),
                    datos_contacto.get('calificacion', 0)
                ))
                
                logger.info(f"Contacto creado: {contacto_id}")
                return {"id": contacto_id, "mensaje": "Contacto creado exitosamente"}
                
        except Exception as e:
            logger.error(f"Error creando contacto: {e}")
            return {"error": str(e)}
    
    def obtener_contacto(self, contacto_id: str) -> Optional[Dict]:
        """Obtiene un contacto específico."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('SELECT * FROM contactos WHERE id = ?', (contacto_id,))
                row = cursor.fetchone()
                
                if row:
                    contacto = dict(row)
                    # Obtener propiedades asociadas
                    cursor = conn.execute('''
                        SELECT propiedad_id FROM propiedades_contactos 
                        WHERE contacto_id = ?
                    ''', (contacto_id,))
                    contacto['propiedades_asociadas'] = [r[0] for r in cursor.fetchall()]
                    return contacto
                return None
                
        except Exception as e:
            logger.error(f"Error obteniendo contacto: {e}")
            return None
    
    def listar_contactos(self) -> List[Dict]:
        """Lista todos los contactos activos."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT c.*, COUNT(pc.propiedad_id) as total_propiedades
                    FROM contactos c
                    LEFT JOIN propiedades_contactos pc ON c.id = pc.contacto_id
                    WHERE c.activo = 1
                    GROUP BY c.id
                    ORDER BY c.fecha_actualizacion DESC
                ''')
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error listando contactos: {e}")
            return []
    
    def actualizar_contacto(self, contacto_id: str, datos: Dict) -> Dict:
        """Actualiza un contacto existente."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Construir query dinámico
                campos = []
                valores = []
                for campo, valor in datos.items():
                    if campo != 'id':  # No actualizar ID
                        campos.append(f"{campo} = ?")
                        valores.append(valor)
                
                if campos:
                    campos.append("fecha_actualizacion = CURRENT_TIMESTAMP")
                    valores.append(contacto_id)
                    
                    query = f"UPDATE contactos SET {', '.join(campos)} WHERE id = ?"
                    conn.execute(query, valores)
                    
                    return {"mensaje": "Contacto actualizado exitosamente"}
                return {"error": "No hay campos para actualizar"}
                
        except Exception as e:
            logger.error(f"Error actualizando contacto: {e}")
            return {"error": str(e)}
    
    def asociar_propiedad(self, propiedad_id: str, contacto_id: str) -> Dict:
        """Asocia una propiedad con un contacto."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR IGNORE INTO propiedades_contactos (propiedad_id, contacto_id)
                    VALUES (?, ?)
                ''', (propiedad_id, contacto_id))
                
                return {"mensaje": "Propiedad asociada exitosamente"}
                
        except Exception as e:
            logger.error(f"Error asociando propiedad: {e}")
            return {"error": str(e)}
    
    def desasociar_propiedad(self, propiedad_id: str, contacto_id: str = None) -> Dict:
        """Desasocia una propiedad de un contacto (cuando se borra la propiedad)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                if contacto_id:
                    conn.execute('''
                        DELETE FROM propiedades_contactos 
                        WHERE propiedad_id = ? AND contacto_id = ?
                    ''', (propiedad_id, contacto_id))
                else:
                    # Desasociar de todos los contactos
                    conn.execute('''
                        DELETE FROM propiedades_contactos WHERE propiedad_id = ?
                    ''', (propiedad_id,))
                
                return {"mensaje": "Propiedad desasociada exitosamente"}
                
        except Exception as e:
            logger.error(f"Error desasociando propiedad: {e}")
            return {"error": str(e)}
    
    def registrar_interaccion(self, contacto_id: str, tipo: str, descripcion: str) -> Dict:
        """Registra una interacción con un contacto."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO interacciones (contacto_id, tipo_interaccion, descripcion)
                    VALUES (?, ?, ?)
                ''', (contacto_id, tipo, descripcion))
                
                return {"mensaje": "Interacción registrada"}
                
        except Exception as e:
            logger.error(f"Error registrando interacción: {e}")
            return {"error": str(e)}

# Inicializar el gestor de contactos
contactos_manager = ContactosManager()

# ============================================================================
# ENDPOINTS DE CONTACTOS
# ============================================================================

@app.route('/api/contactos', methods=['GET', 'POST'])
def manejar_contactos():
    """Maneja la lista y creación de contactos."""
    try:
        if request.method == 'GET':
            contactos = contactos_manager.listar_contactos()
            return jsonify(contactos)
            
        elif request.method == 'POST':
            datos = request.json
            resultado = contactos_manager.crear_contacto(datos)
            if 'error' in resultado:
                return jsonify(resultado), 400
            return jsonify(resultado), 201
            
    except Exception as e:
        logger.error(f"Error en manejar_contactos: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/contactos/<contacto_id>', methods=['GET', 'PUT', 'DELETE'])
def manejar_contacto_individual(contacto_id: str):
    """Maneja operaciones sobre un contacto específico."""
    try:
        if request.method == 'GET':
            contacto = contactos_manager.obtener_contacto(contacto_id)
            if contacto:
                return jsonify(contacto)
            return jsonify({'error': 'Contacto no encontrado'}), 404
            
        elif request.method == 'PUT':
            datos = request.json
            resultado = contactos_manager.actualizar_contacto(contacto_id, datos)
            if 'error' in resultado:
                return jsonify(resultado), 400
            return jsonify(resultado)
            
        elif request.method == 'DELETE':
            # Marcar como inactivo en lugar de eliminar
            resultado = contactos_manager.actualizar_contacto(contacto_id, {'activo': 0})
            if 'error' in resultado:
                return jsonify(resultado), 400
            return jsonify({'mensaje': 'Contacto desactivado exitosamente'})
            
    except Exception as e:
        logger.error(f"Error en manejar_contacto_individual: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/contactos/<contacto_id>/propiedades', methods=['POST', 'DELETE'])
def manejar_asociaciones_propiedad(contacto_id: str):
    """Maneja asociaciones entre contactos y propiedades."""
    try:
        datos = request.json
        propiedad_id = datos.get('propiedad_id')
        
        if not propiedad_id:
            return jsonify({'error': 'propiedad_id requerido'}), 400
            
        if request.method == 'POST':
            resultado = contactos_manager.asociar_propiedad(propiedad_id, contacto_id)
        else:  # DELETE
            resultado = contactos_manager.desasociar_propiedad(propiedad_id, contacto_id)
            
        if 'error' in resultado:
            return jsonify(resultado), 400
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error en manejar_asociaciones_propiedad: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/contactos/<contacto_id>/interacciones', methods=['GET', 'POST'])
def manejar_interacciones(contacto_id: str):
    """Maneja interacciones con contactos."""
    try:
        if request.method == 'GET':
            with sqlite3.connect(contactos_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT * FROM interacciones 
                    WHERE contacto_id = ? 
                    ORDER BY fecha DESC
                ''', (contacto_id,))
                interacciones = [dict(row) for row in cursor.fetchall()]
                return jsonify(interacciones)
                
        elif request.method == 'POST':
            datos = request.json
            resultado = contactos_manager.registrar_interaccion(
                contacto_id,
                datos.get('tipo', 'general'),
                datos.get('descripcion', '')
            )
            if 'error' in resultado:
                return jsonify(resultado), 400
            return jsonify(resultado), 201
            
    except Exception as e:
        logger.error(f"Error en manejar_interacciones: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# ============================================================================
# MODIFICACIÓN DEL ENDPOINT DE ELIMINACIÓN DE PROPIEDADES
# ============================================================================

# Actualizar la función manejar_propiedad para desasociar contactos
def eliminar_propiedad_con_contactos(propiedad_id: str):
    """Elimina propiedad y desasocia contactos."""
    # Desasociar de todos los contactos
    contactos_manager.desasociar_propiedad(propiedad_id)
    
    # Resto del código de eliminación original...
    propiedades_originales = len(propiedades_manager.propiedades)
    
    # Buscar y eliminar la propiedad
    propiedades_manager.propiedades = [
        prop for prop in propiedades_manager.propiedades 
        if prop.get('id') != propiedad_id
    ]
    
    if len(propiedades_manager.propiedades) < propiedades_originales:
        # Recrear índices después de la eliminación
        propiedades_manager.crear_indices()
        
        # Guardar cambios en el archivo JSON
        try:
            import json
            with open('resultados/propiedades_estructuradas.json', 'r+', encoding='utf-8') as f:
                datos = json.load(f)
                if isinstance(datos, dict) and 'propiedades' in datos:
                    datos['propiedades'] = [
                        prop for prop in datos['propiedades']
                        if prop.get('id') != propiedad_id
                    ]
                else:
                    datos = [prop for prop in datos if prop.get('id') != propiedad_id]
                
                f.seek(0)
                json.dump(datos, f, ensure_ascii=False, indent=2)
                f.truncate()
            
            logger.info(f"Propiedad {propiedad_id} eliminada del repositorio y desasociada de contactos")
            return True
            
        except Exception as e:
            logger.error(f"Error guardando cambios: {e}")
            # Recargar datos originales en caso de error
            propiedades_manager.cargar_datos()
            propiedades_manager.crear_indices()
            return False
    return False

# ============================================================================
# SISTEMA COLABORATIVO - FASE 2
# ============================================================================

class UsuariosManager:
    def __init__(self, db_path: str = 'sistema_colaborativo.db'):
        """Inicializa el gestor de usuarios y equipos."""
        self.db_path = db_path
        self.secret_key = "inmobiliaria_colaborativa_2024"  # En producción usar variable de entorno
        self.init_database()
    
    def init_database(self):
        """Crea las tablas para el sistema colaborativo."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Tabla de usuarios
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id TEXT PRIMARY KEY,
                        nombre TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password_hash TEXT NOT NULL,
                        telefono TEXT,
                        rol TEXT DEFAULT 'asesor',
                        equipo_id TEXT,
                        activo BOOLEAN DEFAULT 1,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ultimo_acceso TIMESTAMP,
                        configuracion JSON DEFAULT '{}',
                        avatar_url TEXT
                    )
                ''')
                
                # Tabla de equipos
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS equipos (
                        id TEXT PRIMARY KEY,
                        nombre TEXT NOT NULL,
                        descripcion TEXT,
                        lider_id TEXT,
                        configuracion JSON DEFAULT '{}',
                        activo BOOLEAN DEFAULT 1,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (lider_id) REFERENCES usuarios (id)
                    )
                ''')
                
                # Tabla de favoritos compartidos
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS favoritos_equipo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        propiedad_id TEXT NOT NULL,
                        equipo_id TEXT NOT NULL,
                        usuario_id TEXT NOT NULL,
                        comentario TEXT,
                        prioridad INTEGER DEFAULT 3,
                        fecha_agregado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        tags TEXT DEFAULT '[]',
                        FOREIGN KEY (equipo_id) REFERENCES equipos (id),
                        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                    )
                ''')
                
                # Tabla de notificaciones
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS notificaciones (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario_id TEXT NOT NULL,
                        tipo TEXT NOT NULL,
                        titulo TEXT NOT NULL,
                        mensaje TEXT NOT NULL,
                        datos JSON DEFAULT '{}',
                        leida BOOLEAN DEFAULT 0,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                    )
                ''')
                
                # Tabla de sesiones de usuario
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS sesiones (
                        token TEXT PRIMARY KEY,
                        usuario_id TEXT NOT NULL,
                        fecha_expiracion TIMESTAMP NOT NULL,
                        activa BOOLEAN DEFAULT 1,
                        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                    )
                ''')
                
                # Tabla de actividad del equipo
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS actividad_equipo (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        equipo_id TEXT NOT NULL,
                        usuario_id TEXT NOT NULL,
                        accion TEXT NOT NULL,
                        descripcion TEXT,
                        datos JSON DEFAULT '{}',
                        fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (equipo_id) REFERENCES equipos (id),
                        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
                    )
                ''')
                
                logger.info("Base de datos colaborativa inicializada")
        except Exception as e:
            logger.error(f"Error inicializando base de datos colaborativa: {e}")
    
    def hash_password(self, password: str) -> str:
        """Genera hash seguro de contraseña."""
        return hashlib.pbkdf2_hmac('sha256', password.encode(), b'salt_inmobiliaria', 100000).hex()
    
    def verificar_password(self, password: str, hash_guardado: str) -> bool:
        """Verifica contraseña contra hash."""
        return self.hash_password(password) == hash_guardado
    
    def generar_token(self, usuario_id: str) -> str:
        """Genera token JWT para autenticación."""
        payload = {
            'usuario_id': usuario_id,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verificar_token(self, token: str) -> Optional[str]:
        """Verifica token JWT y retorna usuario_id."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload['usuario_id']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def crear_usuario(self, datos: Dict) -> Dict:
        """Crea un nuevo usuario."""
        try:
            usuario_id = f"user_{secrets.token_hex(8)}"
            password_hash = self.hash_password(datos['password'])
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO usuarios (id, nombre, email, password_hash, telefono, rol, equipo_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    usuario_id,
                    datos['nombre'],
                    datos['email'],
                    password_hash,
                    datos.get('telefono', ''),
                    datos.get('rol', 'asesor'),
                    datos.get('equipo_id', None)
                ))
                
                return {"id": usuario_id, "mensaje": "Usuario creado exitosamente"}
        except sqlite3.IntegrityError:
            return {"error": "Email ya registrado"}
        except Exception as e:
            logger.error(f"Error creando usuario: {e}")
            return {"error": str(e)}
    
    def autenticar_usuario(self, email: str, password: str) -> Dict:
        """Autentica usuario y genera token."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT u.*, e.nombre as equipo_nombre 
                    FROM usuarios u 
                    LEFT JOIN equipos e ON u.equipo_id = e.id 
                    WHERE u.email = ? AND u.activo = 1
                ''', (email,))
                usuario = cursor.fetchone()
                
                if usuario and self.verificar_password(password, usuario['password_hash']):
                    # Actualizar último acceso
                    conn.execute('''
                        UPDATE usuarios SET ultimo_acceso = CURRENT_TIMESTAMP 
                        WHERE id = ?
                    ''', (usuario['id'],))
                    
                    # Generar token
                    token = self.generar_token(usuario['id'])
                    
                    # Guardar sesión
                    conn.execute('''
                        INSERT INTO sesiones (token, usuario_id, fecha_expiracion)
                        VALUES (?, ?, ?)
                    ''', (token, usuario['id'], datetime.utcnow() + timedelta(hours=24)))
                    
                    return {
                        "token": token,
                        "usuario": {
                            "id": usuario['id'],
                            "nombre": usuario['nombre'],
                            "email": usuario['email'],
                            "rol": usuario['rol'],
                            "equipo_id": usuario['equipo_id'],
                            "equipo_nombre": usuario['equipo_nombre']
                        }
                    }
                return {"error": "Credenciales inválidas"}
        except Exception as e:
            logger.error(f"Error autenticando usuario: {e}")
            return {"error": str(e)}
    
    def obtener_usuario_por_token(self, token: str) -> Optional[Dict]:
        """Obtiene información del usuario por token."""
        usuario_id = self.verificar_token(token)
        if not usuario_id:
            return None
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT u.*, e.nombre as equipo_nombre 
                    FROM usuarios u 
                    LEFT JOIN equipos e ON u.equipo_id = e.id 
                    WHERE u.id = ? AND u.activo = 1
                ''', (usuario_id,))
                usuario = cursor.fetchone()
                
                if usuario:
                    return dict(usuario)
                return None
        except Exception as e:
            logger.error(f"Error obteniendo usuario: {e}")
            return None

    def actualizar_usuario(self, usuario_id: str, datos: Dict) -> Dict:
        """Actualiza datos de un usuario."""
        try:
            campos_actualizables = ['nombre', 'email', 'telefono', 'configuracion']
            campos_sql = []
            valores = []
            
            for campo in campos_actualizables:
                if campo in datos:
                    if campo == 'configuracion':
                        campos_sql.append(f"{campo} = ?")
                        valores.append(json.dumps(datos[campo]))
                    else:
                        campos_sql.append(f"{campo} = ?")
                        valores.append(datos[campo])
            
            if not campos_sql:
                return {"error": "No hay campos válidos para actualizar"}
            
            valores.append(usuario_id)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(f'''
                    UPDATE usuarios 
                    SET {", ".join(campos_sql)}
                    WHERE id = ? AND activo = 1
                ''', valores)
                
                if conn.total_changes == 0:
                    return {"error": "Usuario no encontrado o inactivo"}
                
                return {"mensaje": "Usuario actualizado exitosamente"}
                
        except sqlite3.IntegrityError as e:
            if "email" in str(e):
                return {"error": "Email ya registrado por otro usuario"}
            return {"error": "Error de integridad de datos"}
        except Exception as e:
            logger.error(f"Error actualizando usuario: {e}")
            return {"error": str(e)}

    def cambiar_password(self, usuario_id: str, password_actual: str, password_nueva: str) -> Dict:
        """Cambia la contraseña de un usuario."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verificar password actual
                cursor = conn.execute('''
                    SELECT password_hash FROM usuarios WHERE id = ? AND activo = 1
                ''', (usuario_id,))
                
                row = cursor.fetchone()
                if not row:
                    return {"error": "Usuario no encontrado"}
                
                if not self.verificar_password(password_actual, row[0]):
                    return {"error": "Contraseña actual incorrecta"}
                
                # Actualizar password
                password_hash = self.hash_password(password_nueva)
                conn.execute('''
                    UPDATE usuarios SET password_hash = ? WHERE id = ?
                ''', (password_hash, usuario_id))
                
                return {"mensaje": "Contraseña cambiada exitosamente"}
                
        except Exception as e:
            logger.error(f"Error cambiando contraseña: {e}")
            return {"error": str(e)}

    def eliminar_usuario(self, usuario_id: str, usuario_solicitante_id: str) -> Dict:
        """Elimina un usuario (marcado como inactivo)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Verificar que el usuario solicitante tenga permisos
                cursor = conn.execute('''
                    SELECT rol FROM usuarios WHERE id = ? AND activo = 1
                ''', (usuario_solicitante_id,))
                
                row = cursor.fetchone()
                if not row:
                    return {"error": "Usuario solicitante no encontrado"}
                
                # Solo admins o el mismo usuario puede eliminar
                if row[0] != 'admin' and usuario_solicitante_id != usuario_id:
                    return {"error": "Sin permisos para eliminar este usuario"}
                
                # Marcar como inactivo en lugar de eliminar físicamente
                conn.execute('''
                    UPDATE usuarios SET activo = 0 WHERE id = ?
                ''', (usuario_id,))
                
                if conn.total_changes == 0:
                    return {"error": "Usuario no encontrado"}
                
                return {"mensaje": "Usuario eliminado exitosamente"}
                
        except Exception as e:
            logger.error(f"Error eliminando usuario: {e}")
            return {"error": str(e)}

    def generar_token_recuperacion(self, email: str) -> Dict:
        """Genera token para recuperación de contraseña."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT id, nombre FROM usuarios WHERE email = ? AND activo = 1
                ''', (email,))
                
                row = cursor.fetchone()
                if not row:
                    return {"error": "Email no encontrado"}
                
                # Generar token temporal (válido por 1 hora)
                token_data = {
                    'usuario_id': row[0],
                    'tipo': 'recuperacion',
                    'exp': datetime.utcnow() + timedelta(hours=1)
                }
                
                token = jwt.encode(token_data, self.secret_key, algorithm='HS256')
                
                return {
                    "mensaje": "Token de recuperación generado",
                    "token": token,
                    "usuario_id": row[0],
                    "nombre": row[1]
                }
                
        except Exception as e:
            logger.error(f"Error generando token de recuperación: {e}")
            return {"error": str(e)}

    def restablecer_password(self, token: str, password_nueva: str) -> Dict:
        """Restablece contraseña usando token de recuperación."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            if payload.get('tipo') != 'recuperacion':
                return {"error": "Token inválido"}
            
            usuario_id = payload.get('usuario_id')
            password_hash = self.hash_password(password_nueva)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE usuarios SET password_hash = ? WHERE id = ? AND activo = 1
                ''', (password_hash, usuario_id))
                
                if conn.total_changes == 0:
                    return {"error": "Usuario no encontrado"}
                
                return {"mensaje": "Contraseña restablecida exitosamente"}
                
        except jwt.ExpiredSignatureError:
            return {"error": "Token expirado"}
        except jwt.InvalidTokenError:
            return {"error": "Token inválido"}
        except Exception as e:
            logger.error(f"Error restableciendo contraseña: {e}")
            return {"error": str(e)}
    
    def crear_equipo(self, datos: Dict, lider_id: str) -> Dict:
        """Crea un nuevo equipo."""
        try:
            equipo_id = f"team_{secrets.token_hex(8)}"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO equipos (id, nombre, descripcion, lider_id)
                    VALUES (?, ?, ?, ?)
                ''', (equipo_id, datos['nombre'], datos.get('descripcion', ''), lider_id))
                
                # Agregar líder al equipo
                conn.execute('''
                    UPDATE usuarios SET equipo_id = ? WHERE id = ?
                ''', (equipo_id, lider_id))
                
                return {"id": equipo_id, "mensaje": "Equipo creado exitosamente"}
        except Exception as e:
            logger.error(f"Error creando equipo: {e}")
            return {"error": str(e)}
    
    def agregar_favorito_equipo(self, propiedad_id: str, equipo_id: str, usuario_id: str, datos: Dict) -> Dict:
        """Agrega propiedad a favoritos del equipo."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO favoritos_equipo (propiedad_id, equipo_id, usuario_id, comentario, prioridad, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    propiedad_id,
                    equipo_id,
                    usuario_id,
                    datos.get('comentario', ''),
                    datos.get('prioridad', 3),
                    json.dumps(datos.get('tags', []))
                ))
                
                # Crear notificación para el equipo
                self.crear_notificacion_equipo(
                    equipo_id,
                    usuario_id,
                    "favorito_agregado",
                    f"Nueva propiedad en favoritos del equipo",
                    {"propiedad_id": propiedad_id}
                )
                
                return {"mensaje": "Favorito agregado al equipo"}
        except Exception as e:
            logger.error(f"Error agregando favorito: {e}")
            return {"error": str(e)}
    
    def crear_notificacion_equipo(self, equipo_id: str, emisor_id: str, tipo: str, titulo: str, datos: Dict):
        """Crea notificaciones para todos los miembros del equipo."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Obtener miembros del equipo (excepto el emisor)
                cursor = conn.execute('''
                    SELECT id FROM usuarios WHERE equipo_id = ? AND id != ? AND activo = 1
                ''', (equipo_id, emisor_id))
                
                miembros = [row[0] for row in cursor.fetchall()]
                
                # Crear notificación para cada miembro
                for miembro_id in miembros:
                    conn.execute('''
                        INSERT INTO notificaciones (usuario_id, tipo, titulo, mensaje, datos)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        miembro_id,
                        tipo,
                        titulo,
                        f"Por {emisor_id}",
                        json.dumps(datos)
                    ))
        except Exception as e:
            logger.error(f"Error creando notificaciones: {e}")

# Inicializar gestor de usuarios
usuarios_manager = UsuariosManager()

# Decorador para rutas que requieren autenticación
def requiere_auth(f):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token requerido'}), 401
            
        token = auth_header.split(' ')[1]
        usuario = usuarios_manager.obtener_usuario_por_token(token)
        if not usuario:
            return jsonify({'error': 'Token inválido'}), 401
            
        request.usuario_actual = usuario
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

# ============================================================================
# ENDPOINTS COLABORATIVOS
# ============================================================================

@app.route('/api/auth/registro', methods=['POST'])
def registro_usuario():
    """Registra un nuevo usuario."""
    try:
        datos = request.json
        resultado = usuarios_manager.crear_usuario(datos)
        
        if 'error' in resultado:
            return jsonify(resultado), 400
        return jsonify(resultado), 201
    except Exception as e:
        logger.error(f"Error en registro: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/auth/login', methods=['POST'])
def login_usuario():
    """Autentica usuario."""
    try:
        datos = request.json
        resultado = usuarios_manager.autenticar_usuario(datos['email'], datos['password'])
        
        if 'error' in resultado:
            return jsonify(resultado), 401
        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"Error en login: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/auth/perfil', methods=['GET', 'PUT'])
@requiere_auth
def obtener_perfil():
    """Obtiene o actualiza perfil del usuario actual."""
    try:
        if request.method == 'GET':
            return jsonify(request.usuario_actual)
        
        elif request.method == 'PUT':
            datos = request.json
            resultado = usuarios_manager.actualizar_usuario(
                request.usuario_actual['id'], 
                datos
            )
            
            if 'error' in resultado:
                return jsonify(resultado), 400
            return jsonify(resultado)
            
    except Exception as e:
        logger.error(f"Error en perfil: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/auth/cambiar-password', methods=['POST'])
@requiere_auth
def cambiar_password():
    """Cambia la contraseña del usuario actual."""
    try:
        datos = request.json
        password_actual = datos.get('password_actual')
        password_nueva = datos.get('password_nueva')
        
        if not password_actual or not password_nueva:
            return jsonify({'error': 'password_actual y password_nueva son requeridos'}), 400
        
        resultado = usuarios_manager.cambiar_password(
            request.usuario_actual['id'],
            password_actual,
            password_nueva
        )
        
        if 'error' in resultado:
            return jsonify(resultado), 400
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error cambiando contraseña: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/auth/recuperar-password', methods=['POST'])
def recuperar_password():
    """Genera token para recuperación de contraseña."""
    try:
        datos = request.json
        email = datos.get('email')
        
        if not email:
            return jsonify({'error': 'Email es requerido'}), 400
        
        resultado = usuarios_manager.generar_token_recuperacion(email)
        
        if 'error' in resultado:
            return jsonify(resultado), 400
        
        # En producción, aquí enviarías el token por email
        # Por ahora, devolvemos el token en la respuesta (NO HACER EN PRODUCCIÓN)
        return jsonify({
            'mensaje': 'Token de recuperación generado',
            'token_recuperacion': resultado['token']  # Solo para desarrollo
        })
        
    except Exception as e:
        logger.error(f"Error recuperando contraseña: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/auth/restablecer-password', methods=['POST'])
def restablecer_password():
    """Restablece contraseña usando token de recuperación."""
    try:
        datos = request.json
        token = datos.get('token')
        password_nueva = datos.get('password_nueva')
        
        if not token or not password_nueva:
            return jsonify({'error': 'token y password_nueva son requeridos'}), 400
        
        resultado = usuarios_manager.restablecer_password(token, password_nueva)
        
        if 'error' in resultado:
            return jsonify(resultado), 400
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error restableciendo contraseña: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/usuarios', methods=['GET'])
@requiere_auth
def listar_usuarios():
    """Lista todos los usuarios (solo administradores)."""
    try:
        if request.usuario_actual['rol'] != 'administrador':
            return jsonify({'error': 'Acceso denegado. Solo administradores.'}), 403
            
        with sqlite3.connect(usuarios_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT u.*, e.nombre as equipo_nombre 
                FROM usuarios u 
                LEFT JOIN equipos e ON u.equipo_id = e.id 
                ORDER BY u.fecha_creacion DESC
            ''')
            usuarios = [dict(row) for row in cursor.fetchall()]
            
        return jsonify(usuarios)
        
    except Exception as e:
        logger.error(f"Error listando usuarios: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/usuarios/<usuario_id>', methods=['DELETE'])
@requiere_auth
def eliminar_usuario(usuario_id: str):
    """Elimina un usuario (requiere permisos)."""
    try:
        resultado = usuarios_manager.eliminar_usuario(
            usuario_id,
            request.usuario_actual['id']
        )
        
        if 'error' in resultado:
            return jsonify(resultado), 400
        return jsonify(resultado)
        
    except Exception as e:
        logger.error(f"Error eliminando usuario: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/equipos', methods=['GET', 'POST'])
@requiere_auth
def manejar_equipos():
    """Maneja equipos."""
    try:
        if request.method == 'GET':
            # Listar equipos
            with sqlite3.connect(usuarios_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT e.*, u.nombre as lider_nombre,
                           COUNT(miembros.id) as total_miembros
                    FROM equipos e
                    LEFT JOIN usuarios u ON e.lider_id = u.id
                    LEFT JOIN usuarios miembros ON e.id = miembros.equipo_id
                    WHERE e.activo = 1
                    GROUP BY e.id
                    ORDER BY e.fecha_creacion DESC
                ''')
                equipos = [dict(row) for row in cursor.fetchall()]
                return jsonify(equipos)
                
        elif request.method == 'POST':
            # Crear equipo
            datos = request.json
            resultado = usuarios_manager.crear_equipo(datos, request.usuario_actual['id'])
            
            if 'error' in resultado:
                return jsonify(resultado), 400
            return jsonify(resultado), 201
            
    except Exception as e:
        logger.error(f"Error en manejar_equipos: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/favoritos-equipo', methods=['GET', 'POST'])
@requiere_auth
def manejar_favoritos_equipo():
    """Maneja favoritos del equipo."""
    try:
        if request.method == 'GET':
            equipo_id = request.usuario_actual.get('equipo_id')
            if not equipo_id:
                return jsonify([])
                
            with sqlite3.connect(usuarios_manager.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('''
                    SELECT f.*, u.nombre as agregado_por
                    FROM favoritos_equipo f
                    LEFT JOIN usuarios u ON f.usuario_id = u.id
                    WHERE f.equipo_id = ?
                    ORDER BY f.fecha_agregado DESC
                ''', (equipo_id,))
                
                favoritos = [dict(row) for row in cursor.fetchall()]
                return jsonify(favoritos)
                
        elif request.method == 'POST':
            datos = request.json
            equipo_id = request.usuario_actual.get('equipo_id')
            
            if not equipo_id:
                return jsonify({'error': 'Usuario no pertenece a un equipo'}), 400
                
            resultado = usuarios_manager.agregar_favorito_equipo(
                datos['propiedad_id'],
                equipo_id,
                request.usuario_actual['id'],
                datos
            )
            
            if 'error' in resultado:
                return jsonify(resultado), 400
            return jsonify(resultado), 201
            
    except Exception as e:
        logger.error(f"Error en favoritos equipo: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/notificaciones', methods=['GET'])
@requiere_auth
def obtener_notificaciones():
    """Obtiene notificaciones del usuario."""
    try:
        with sqlite3.connect(usuarios_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute('''
                SELECT * FROM notificaciones 
                WHERE usuario_id = ? 
                ORDER BY fecha_creacion DESC 
                LIMIT 50
            ''', (request.usuario_actual['id'],))
            
            notificaciones = [dict(row) for row in cursor.fetchall()]
            return jsonify(notificaciones)
            
    except Exception as e:
        logger.error(f"Error obteniendo notificaciones: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/dashboard-equipo', methods=['GET'])
@requiere_auth
def dashboard_equipo():
    """Obtiene métricas del dashboard del equipo."""
    try:
        equipo_id = request.usuario_actual.get('equipo_id')
        if not equipo_id:
            return jsonify({'error': 'Usuario no pertenece a un equipo'}), 400
            
        with sqlite3.connect(usuarios_manager.db_path) as conn:
            # Miembros del equipo
            cursor = conn.execute('''
                SELECT COUNT(*) as total FROM usuarios WHERE equipo_id = ? AND activo = 1
            ''', (equipo_id,))
            total_miembros = cursor.fetchone()[0]
            
            # Favoritos del equipo
            cursor = conn.execute('''
                SELECT COUNT(*) as total FROM favoritos_equipo WHERE equipo_id = ?
            ''', (equipo_id,))
            total_favoritos = cursor.fetchone()[0]
            
            # Actividad reciente
            cursor = conn.execute('''
                SELECT a.*, u.nombre as usuario_nombre
                FROM actividad_equipo a
                LEFT JOIN usuarios u ON a.usuario_id = u.id
                WHERE a.equipo_id = ?
                ORDER BY a.fecha DESC
                LIMIT 10
            ''', (equipo_id,))
            conn.row_factory = sqlite3.Row
            actividad_reciente = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({
                'total_miembros': total_miembros,
                'total_favoritos': total_favoritos,
                'actividad_reciente': actividad_reciente
            })
            
    except Exception as e:
        logger.error(f"Error en dashboard equipo: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

# ============================================================================
# ENDPOINTS DE WHATSAPP
# ============================================================================

@app.route('/api/whatsapp/enviar-propiedad', methods=['POST'])
def enviar_propiedad_whatsapp():
    """Envía una propiedad específica por WhatsApp."""
    try:
        if not WHATSAPP_DISPONIBLE:
            return jsonify({
                'error': 'Módulo de WhatsApp no disponible',
                'solucion': 'Instalar dependencias: pip install requests'
            }), 400
        
        datos = request.json
        propiedad_id = datos.get('propiedad_id')
        numero_destino = datos.get('numero_destino')
        
        if not propiedad_id or not numero_destino:
            return jsonify({
                'error': 'propiedad_id y numero_destino son requeridos'
            }), 400
        
        # Validar formato del número
        if not numero_destino.startswith('+'):
            numero_destino = f"+52{numero_destino}"
        
        # Buscar propiedad
        propiedad = None
        for prop in propiedades_manager.propiedades:
            if prop.get('id') == propiedad_id:
                propiedad = prop
                break
        
        if not propiedad:
            return jsonify({
                'success': False,
                'error': f'Propiedad {propiedad_id} no encontrada'
            }), 404
        

        
        # Obtener datos del asesor
        datos_asesor = None
        
        # Verificar si hay usuario autenticado
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            usuario = usuarios_manager.obtener_usuario_por_token(token)
            if usuario:
                # Usuario logueado - usar sus datos
                datos_asesor = {
                    'nombre': usuario.get('nombre'),
                    'telefono': usuario.get('telefono', ''),
                    'mensaje_opcional': f"Te ayudo a encontrar tu hogar ideal. ¡Contáctame!"
                }
        
        # Si no hay usuario logueado, obtener datos del formulario
        if not datos_asesor:
            datos_asesor = {
                'nombre': datos.get('asesor_nombre', ''),
                'telefono': datos.get('asesor_telefono', ''),
                'mensaje_opcional': datos.get('asesor_mensaje', '')
            }
        
        # Enviar propiedad con datos del asesor
        resultado = enviar_propiedad_por_whatsapp(
            propiedad=propiedad, 
            numero_destino=numero_destino, 
            whatsapp_api=None, 
            datos_asesor=datos_asesor
        )
        
        if resultado.get('success'):
            return jsonify({
                'success': True,
                'mensaje': 'Propiedad enviada exitosamente por WhatsApp',
                'resultado': resultado,
                'asesor_incluido': bool(datos_asesor and datos_asesor.get('nombre'))
        }), 200
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('error', 'Error desconocido'),
                'resultado': resultado
            }), 400
        
    except Exception as e:
        logger.error(f"Error enviando propiedad por WhatsApp: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/whatsapp/enviar-multiples', methods=['POST'])
def enviar_multiples_propiedades_whatsapp():
    """Envía múltiples propiedades por WhatsApp."""
    try:
        if not WHATSAPP_DISPONIBLE:
            return jsonify({
                'error': 'Módulo de WhatsApp no disponible'
            }), 400
        
        datos = request.json
        filtros = datos.get('filtros', {})
        numero_destino = datos.get('numero_destino')
        max_propiedades = datos.get('max_propiedades', 5)
        
        if not numero_destino:
            return jsonify({'error': 'numero_destino requerido'}), 400
        
        # Validar formato del número
        if not numero_destino.startswith('+'):
            numero_destino = f"+52{numero_destino}"
        
        # Filtrar propiedades según criterios
        indices_filtrados = propiedades_manager.filtrar_propiedades(filtros)
        propiedades_filtradas = [
            propiedades_manager.propiedades[i] for i in indices_filtrados[:max_propiedades]
        ]
        
        # Enviar por WhatsApp
        api = WhatsAppAPI()
        resultado = api.enviar_multiples_propiedades(
            propiedades_filtradas, 
            numero_destino, 
            max_propiedades
        )
        
        return jsonify({
            'success': resultado.get('success', False),
            'mensaje': f"Proceso completado. {resultado.get('enviadas', 0)} propiedades enviadas",
            'resultado': resultado
        }), 200
        
    except Exception as e:
        logger.error(f"Error enviando múltiples propiedades: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/whatsapp/test', methods=['POST'])
def test_whatsapp():
    """Prueba la configuración de WhatsApp."""
    try:
        datos = request.json
        numero_destino = datos.get('numero_destino', '+521234567890')
        
        # Validar formato del número
        if not numero_destino.startswith('+'):
            numero_destino = f"+52{numero_destino}"
        
        api = WhatsAppAPI()
        
        # Mensaje de prueba
        mensaje_test = """🏠 *PRUEBA del Sistema Inmobiliario*

✅ La integración con WhatsApp está funcionando correctamente.

📱 *Características disponibles:*
• Envío de propiedades individuales
• Envío masivo con filtros
• Imágenes de portada
• Descripciones formateadas

¿Listo para usar el sistema? 🚀"""
        
        resultado = api.enviar_mensaje_texto(numero_destino, mensaje_test)
        
        if resultado.get('success'):
            return jsonify({
                'success': True,
                'mensaje': 'Mensaje de prueba enviado exitosamente',
                'configuracion': {
                    'whatsapp_disponible': WHATSAPP_DISPONIBLE,
                    'token_configurado': bool(api.token),
                    'phone_id_configurado': bool(api.phone_number_id),
                    'modo_simulacion': not (api.token and api.phone_number_id)
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': resultado.get('error'),
                'configuracion': {
                    'whatsapp_disponible': WHATSAPP_DISPONIBLE,
                    'token_configurado': bool(api.token),
                    'phone_id_configurado': bool(api.phone_number_id),
                    'modo_simulacion': not (api.token and api.phone_number_id)
                }
            }), 400
            
    except Exception as e:
        logger.error(f"Error en test de WhatsApp: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/whatsapp/configuracion', methods=['GET'])
def obtener_configuracion_whatsapp():
    """Obtiene la configuración actual de WhatsApp."""
    try:
        if not WHATSAPP_DISPONIBLE:
            return jsonify({
                'disponible': False,
                'error': 'Módulo WhatsApp no importado'
            })
        
        api = WhatsAppAPI()
        
        return jsonify({
            'disponible': True,
            'configurado': bool(api.token and api.phone_number_id),
            'token_presente': bool(api.token),
            'phone_id_presente': bool(api.phone_number_id),
            'modo_simulacion': not (api.token and api.phone_number_id),
            'instrucciones': {
                'paso_1': 'Obtener WhatsApp Business API token',
                'paso_2': 'Configurar variables de entorno',
                'comando_1': 'export WHATSAPP_TOKEN="tu_token"',
                'comando_2': 'export PHONE_NUMBER_ID="tu_phone_id"'
            }
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo configuración WhatsApp: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/whatsapp/configurar', methods=['POST'])
@requiere_auth
def configurar_whatsapp():
    """Configura los tokens de WhatsApp Business API (solo administradores)."""
    try:
        # Verificar que sea administrador
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Token de autorización requerido'}), 401
        
        token = auth_header.split(' ')[1]
        usuario = usuarios_manager.obtener_usuario_por_token(token)
        
        if not usuario or usuario.get('rol') != 'administrador':
            return jsonify({'error': 'Solo administradores pueden configurar WhatsApp'}), 403
        
        datos = request.json
        whatsapp_token = datos.get('token', '').strip()
        phone_number_id = datos.get('phone_number_id', '').strip()
        
        if not whatsapp_token or not phone_number_id:
            return jsonify({'error': 'Token y Phone Number ID son requeridos'}), 400
        
        # Validar formato básico del token
        if not whatsapp_token.startswith('EAA'):
            return jsonify({'error': 'Token de WhatsApp Business inválido (debe empezar con EAA)'}), 400
        
        # Validar que phone_number_id sea numérico
        if not phone_number_id.isdigit():
            return jsonify({'error': 'Phone Number ID debe ser numérico'}), 400
        
        # Guardar configuración en variables de entorno temporales
        # NOTA: En producción esto debería guardarse de forma más segura
        import os
        os.environ['WHATSAPP_TOKEN'] = whatsapp_token
        os.environ['PHONE_NUMBER_ID'] = phone_number_id
        
        # Probar la configuración
        api = WhatsAppAPI(token=whatsapp_token, phone_id=phone_number_id)
        
        if api.esta_configurado():
            logger.info(f"✅ WhatsApp configurado por {usuario.get('nombre')} ({usuario.get('email')})")
            return jsonify({
                'success': True,
                'mensaje': 'Configuración de WhatsApp guardada exitosamente',
                'configurado': True,
                'modo_simulacion': False
            }), 200
        else:
            return jsonify({'error': 'Error al validar la configuración'}), 400
        
    except Exception as e:
        logger.error(f"Error configurando WhatsApp: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/caracteristicas-debug', methods=['GET'])
def debug_caracteristicas():
    """DEBUG: Probar extracción de características numéricas."""
    try:
        with open('resultados/propiedades_estructuradas.json', 'r', encoding='utf-8') as f:
            propiedades = json.load(f)
        
        # Contadores
        caracteristicas_numericas = {
            'recamaras': {},
            'banos': {},
            'estacionamientos': {}
        }
        caracteristicas_booleanas = {}
        
        # Analizar primeras 100 propiedades
        for prop in propiedades[:100]:
            descripcion = prop.get('descripcion_original', '').lower()
            
            # Buscar recámaras
            recamaras_patterns = [
                r'(\d+)\s*(?:recámara|recamara|habitacion|dormitorio)',
                r'(\d+)\s*(?:rec|hab|dorm)',
                r'(\d+)\s*(?:bedroom|room)'
            ]
            for pattern in recamaras_patterns:
                recamaras_match = re.search(pattern, descripcion)
                if recamaras_match:
                    num_recamaras = int(recamaras_match.group(1))
                    if 1 <= num_recamaras <= 10:
                        key = f"{num_recamaras} Recámara{'s' if num_recamaras > 1 else ''}"
                        caracteristicas_numericas['recamaras'][key] = caracteristicas_numericas['recamaras'].get(key, 0) + 1
                    break
            
            # Buscar baños
            banos_patterns = [
                r'(\d+)\s*(?:baño|bano|bathroom)',
                r'(\d+)\s*(?:bath|wc)'
            ]
            for pattern in banos_patterns:
                banos_match = re.search(pattern, descripcion)
                if banos_match:
                    num_banos = int(banos_match.group(1))
                    if 1 <= num_banos <= 10:
                        key = f"{num_banos} Baño{'s' if num_banos > 1 else ''}"
                        caracteristicas_numericas['banos'][key] = caracteristicas_numericas['banos'].get(key, 0) + 1
                    break
            
            # Buscar estacionamientos
            estac_patterns = [
                r'(\d+)\s*(?:estacionamiento|cochera|garage|auto)',
                r'(\d+)\s*(?:parking|car)',
                r'cochera\s*(?:para\s*)?(\d+)',
                r'garage\s*(?:para\s*)?(\d+)'
            ]
            for pattern in estac_patterns:
                estac_match = re.search(pattern, descripcion)
                if estac_match:
                    num_estac = int(estac_match.group(1))
                    if 1 <= num_estac <= 10:
                        key = f"{num_estac} Estacionamiento{'s' if num_estac > 1 else ''}"
                        caracteristicas_numericas['estacionamientos'][key] = caracteristicas_numericas['estacionamientos'].get(key, 0) + 1
                    break
            
            # Características booleanas reales - buscar en descripción
            descripcion_completa = prop.get('descripcion_original', '').lower()
            
            # Verificar un nivel
            if any(termino in descripcion_completa for termino in ['un nivel', 'una planta', 'todo en planta baja', 'sin escaleras']):
                caracteristicas_booleanas['un_nivel'] = caracteristicas_booleanas.get('un_nivel', 0) + 1
            
            # Verificar recámara en planta baja
            if any(termino in descripcion_completa for termino in ['recamara en planta baja', 'recámara pb', 'habitacion planta baja', 'dormitorio pb']):
                caracteristicas_booleanas['recamara_en_pb'] = caracteristicas_booleanas.get('recamara_en_pb', 0) + 1
            
            # Verificar cisterna
            if any(termino in descripcion_completa for termino in ['cisterna', 'deposito de agua', 'tanque de agua', 'almacenamiento agua']):
                caracteristicas_booleanas['cisterna'] = caracteristicas_booleanas.get('cisterna', 0) + 1
        
        # Combinar
        caracteristicas_finales = {}
        for categoria, valores in caracteristicas_numericas.items():
            caracteristicas_finales.update(valores)
        caracteristicas_finales.update(caracteristicas_booleanas)
        
        return jsonify({
            'debug': 'Extracción de características (primeras 100 propiedades)',
            'caracteristicas_numericas': caracteristicas_numericas,
            'caracteristicas_booleanas': caracteristicas_booleanas,
            'caracteristicas_finales': caracteristicas_finales
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/download-frontend', methods=['POST'])
def download_frontend_from_s3():
    """Descarga el frontend desde S3"""
    try:
        data = request.get_json() or {}
        s3_key = data.get('s3_key', 'temp_frontend_content.html')
        
        # Descargar desde S3
        import boto3
        s3 = boto3.client('s3')
        bucket = 'sistema-inmobiliario-datos-1749417070'
        
        s3.download_file(bucket, s3_key, 'temp_frontend_content.html')
        
        logger.info(f"Frontend descargado desde S3: {s3_key}")
        return jsonify({"mensaje": "Frontend descargado exitosamente"})
        
    except Exception as e:
        logger.error(f"Error descargando frontend: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/update-server', methods=['POST'])
def update_server_from_s3():
    """Actualiza el servidor descargando nueva versión desde S3 y reiniciando"""
    try:
        data = request.get_json() or {}
        s3_key = data.get('s3_key', 'api_server_optimizado.py')
        
        # Descargar desde S3
        import boto3
        import os
        import subprocess
        import threading
        
        s3 = boto3.client('s3')
        bucket = 'sistema-inmobiliario-datos-1749417070'
        
        # Descargar nueva versión
        s3.download_file(bucket, s3_key, 'api_server_optimizado_new.py')
        
        logger.info(f"Nueva versión descargada desde S3: {s3_key}")
        
        # Función para reiniciar el servidor en un hilo separado
        def restart_server():
            import time
            time.sleep(2)  # Dar tiempo para que responda
            try:
                # Reemplazar archivo actual
                os.rename('api_server_optimizado_new.py', 'api_server_optimizado.py')
                # Reiniciar proceso
                os.system('pkill -f python3 && nohup python3 api_server_optimizado.py > server.log 2>&1 &')
            except Exception as e:
                logger.error(f"Error reiniciando servidor: {e}")
        
        # Iniciar reinicio en hilo separado
        thread = threading.Thread(target=restart_server)
        thread.daemon = True
        thread.start()
        
        return jsonify({"mensaje": "Actualización iniciada, servidor reiniciando..."})
        
    except Exception as e:
        logger.error(f"Error actualizando servidor: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug-propiedades', methods=['GET'])
def debug_propiedades():
    """Debug temporal para verificar estructura de propiedades."""
    try:
        # Obtener primera propiedad directamente
        prop = propiedades_manager.propiedades[0]
        
        return jsonify({
            'archivo_usado': 'resultados/propiedades_estructuradas.json',
            'total_propiedades': len(propiedades_manager.propiedades),
            'primera_propiedad': {
                'id': prop.get('id'),
                'caracteristicas_raw': prop.get('caracteristicas'),
                'caracteristicas_type': type(prop.get('caracteristicas')).__name__,
                'keys_propiedad': list(prop.keys())
            },
            'metodo_simplificado': propiedades_manager.obtener_propiedad_simplificada(0)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/frontend_tarjetas.html')
def servir_frontend_tarjetas():
    """Sirve el nuevo frontend con tarjetas dinámicas"""
    try:
        return send_file('frontend_tarjetas_dinamicas.html', mimetype='text/html')
    except FileNotFoundError:
        return "Frontend de tarjetas no encontrado", 404
    except Exception as e:
        logger.error(f"Error sirviendo frontend tarjetas: {e}")
        return f"Error sirviendo frontend tarjetas: {str(e)}", 500

@app.route('/frontend_tarjetas_dinamicas.html')
def servir_frontend_tarjetas_alias():
    """Alias directo para servir el mismo frontend dinámico (evita 404 si se accede al nombre del archivo)"""
    try:
        return send_file('frontend_tarjetas_dinamicas.html', mimetype='text/html')
    except FileNotFoundError:
        return "Frontend de tarjetas no encontrado", 404
    except Exception as e:
        logger.error(f"Error sirviendo frontend tarjetas (alias): {e}")
        return f"Error sirviendo frontend tarjetas: {str(e)}", 500

if __name__ == '__main__':
    # Inicializar sistema de prevención
    preventor = None
    if SISTEMA_PREVENCION_DISPONIBLE:
        try:
            preventor = PreventorCorrupciones()
            preventor.iniciar_monitoreo()
            logger.info("🛡️  Sistema de prevención de corrupciones activado")
        except Exception as e:
            logger.warning(f"No se pudo iniciar sistema de prevención: {e}")
    
    try:
        # Configuración para desarrollo
        app.run(host='0.0.0.0', port=5001, debug=False)
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
        if preventor:
            preventor.detener_monitoreo()
    except Exception as e:
        logger.error(f"Error iniciando servidor: {e}")
        if preventor:
            preventor.detener_monitoreo() 

# Frontend HTML embebido
FRONTEND_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sistema Inmobiliario - 4,270 Propiedades</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .stats {
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        
        .stat-card {
            background: rgba(255,255,255,0.9);
            padding: 20px;
            border-radius: 15px;
            text-align: center;
            min-width: 150px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
        }
        
        .controls {
            background: rgba(255,255,255,0.95);
            padding: 25px;
            border-radius: 15px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        }
        
        .search-container {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        
        .search-box {
            flex: 1;
            min-width: 250px;
            padding: 12px 20px;
            border: 2px solid #e1e5e9;
            border-radius: 25px;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        
        .search-box:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .filter-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        
        .filter-group {
            display: flex;
            flex-direction: column;
        }
        
        .filter-group label {
            font-weight: 600;
            margin-bottom: 5px;
            color: #555;
        }
        
        .filter-select {
            padding: 10px;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s ease;
        }
        
        .filter-select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .properties-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .property-card {
            background: white;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .property-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 45px rgba(0,0,0,0.15);
        }
        
        .property-image {
            width: 100%;
            height: 200px;
            background: linear-gradient(45deg, #f0f2f5, #e1e5e9);
            display: flex;
            align-items: center;
            justify-content: center;
            color: #666;
            font-size: 14px;
        }
        
        .property-content {
            padding: 20px;
        }
        
        .property-price {
            font-size: 1.5rem;
            font-weight: bold;
            color: #27ae60;
            margin-bottom: 10px;
        }
        
        .property-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 10px;
            color: #333;
            line-height: 1.4;
        }
        
        .property-location {
            color: #666;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .property-features {
            display: flex;
            gap: 15px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        
        .feature {
            background: #f8f9fa;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            color: #555;
        }
        
        .property-type {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 5px 12px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: 500;
        }
        
        .pagination {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 30px;
        }
        
        .pagination button {
            padding: 10px 15px;
            border: none;
            background: rgba(255,255,255,0.9);
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .pagination button:hover {
            background: #667eea;
            color: white;
        }
        
        .pagination button.active {
            background: #667eea;
            color: white;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            color: white;
            font-size: 1.2rem;
        }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            overflow-y: auto;
        }
        
        .modal-content {
            background: white;
            margin: 50px auto;
            padding: 30px;
            border-radius: 15px;
            max-width: 800px;
            position: relative;
        }
        
        .modal-close {
            position: absolute;
            top: 15px;
            right: 20px;
            font-size: 30px;
            cursor: pointer;
            color: #999;
        }
        
        .modal-close:hover {
            color: #333;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .stats {
                gap: 15px;
            }
            
            .search-container {
                flex-direction: column;
            }
            
            .properties-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏠 Sistema Inmobiliario</h1>
            <p>Encuentra tu propiedad ideal entre miles de opciones</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="totalProperties">4,270</div>
                <div>Propiedades</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="totalCities">50+</div>
                <div>Ciudades</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="avgPrice">$2.5M</div>
                <div>Precio Promedio</div>
            </div>
        </div>
        
        <div class="controls">
            <div class="search-container">
                <input type="text" id="searchBox" class="search-box" placeholder="🔍 Buscar por ubicación, precio, características...">
            </div>
            
            <div class="filter-container">
                <div class="filter-group">
                    <label for="cityFilter">Ciudad</label>
                    <select id="cityFilter" class="filter-select">
                        <option value="">Todas las ciudades</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <label for="typeFilter">Tipo de Propiedad</label>
                    <select id="typeFilter" class="filter-select">
                        <option value="">Todos los tipos</option>
                        <option value="Casa">Casa</option>
                        <option value="Departamento">Departamento</option>
                        <option value="Terreno">Terreno</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <label for="operationFilter">Operación</label>
                    <select id="operationFilter" class="filter-select">
                        <option value="">Todas</option>
                        <option value="venta">Venta</option>
                        <option value="renta">Renta</option>
                    </select>
                </div>
                
                <div class="filter-group">
                    <label for="priceFilter">Rango de Precio</label>
                    <select id="priceFilter" class="filter-select">
                        <option value="">Todos los precios</option>
                        <option value="0-500000">Hasta $500,000</option>
                        <option value="500000-1000000">$500,000 - $1,000,000</option>
                        <option value="1000000-2000000">$1,000,000 - $2,000,000</option>
                        <option value="2000000-5000000">$2,000,000 - $5,000,000</option>
                        <option value="5000000-999999999">Más de $5,000,000</option>
                    </select>
                </div>
            </div>
        </div>
        
        <div id="loadingMessage" class="loading">
            Cargando propiedades...
        </div>
        
        <div id="propertyGrid" class="properties-grid" style="display: none;">
        </div>
        
        <div id="pagination" class="pagination" style="display: none;">
        </div>
    </div>
    
    <!-- Modal para detalles de propiedad -->
    <div id="propertyModal" class="modal">
        <div class="modal-content">
            <span class="modal-close">&times;</span>
            <div id="modalContent">
            </div>
        </div>
    </div>
    
    <script>
        let allProperties = [];
        let filteredProperties = [];
        let currentPage = 1;
        const propertiesPerPage = 12;
        
        // Cargar propiedades al iniciar
        async function loadProperties() {
            try {
                const response = await fetch('/api/propiedades?limite=5000');
                const data = await response.json();
                allProperties = data.propiedades || [];
                filteredProperties = [...allProperties];
                
                updateStats();
                populateFilters();
                displayProperties();
                
                document.getElementById('loadingMessage').style.display = 'none';
                document.getElementById('propertyGrid').style.display = 'grid';
                document.getElementById('pagination').style.display = 'flex';
                
            } catch (error) {
                console.error('Error cargando propiedades:', error);
                document.getElementById('loadingMessage').innerHTML = 'Error cargando propiedades. Intenta recargar la página.';
            }
        }
        
        // Actualizar estadísticas
        function updateStats() {
            document.getElementById('totalProperties').textContent = allProperties.length.toLocaleString();
            
            const cities = [...new Set(allProperties.map(p => p.ubicacion?.ciudad).filter(Boolean))];
            document.getElementById('totalCities').textContent = cities.length + '+';
            
            const prices = allProperties.map(p => p.propiedad?.precio?.valor).filter(p => p && p > 0);
            const avgPrice = prices.length > 0 ? prices.reduce((a, b) => a + b, 0) / prices.length : 0;
            document.getElementById('avgPrice').textContent = '$' + (avgPrice / 1000000).toFixed(1) + 'M';
        }
        
        // Poblar filtros
        function populateFilters() {
            const cities = [...new Set(allProperties.map(p => p.ubicacion?.ciudad).filter(Boolean))].sort();
            const cityFilter = document.getElementById('cityFilter');
            
            cities.forEach(city => {
                const option = document.createElement('option');
                option.value = city;
                option.textContent = city;
                cityFilter.appendChild(option);
            });
        }
        
        // Mostrar propiedades
        function displayProperties() {
            const grid = document.getElementById('propertyGrid');
            const startIndex = (currentPage - 1) * propertiesPerPage;
            const endIndex = startIndex + propertiesPerPage;
            const pageProperties = filteredProperties.slice(startIndex, endIndex);
            
            grid.innerHTML = pageProperties.map(property => createPropertyCard(property)).join('');
            updatePagination();
        }
        
        // Crear tarjeta de propiedad
        function createPropertyCard(property) {
            const precio = property.propiedad?.precio?.formato || 'Precio no disponible';
            const titulo = property.titulo || 'Sin título';
            const ciudad = property.ubicacion?.ciudad || 'Ubicación no disponible';
            const estado = property.ubicacion?.estado || '';
            const tipo = property.propiedad?.tipo_propiedad || 'Propiedad';
            const operacion = property.operacion || 'No especificado';
            
            const recamaras = property.datos_originales?.caracteristicas?.recamaras;
            const banos = property.datos_originales?.caracteristicas?.banos;
            const superficie = property.datos_originales?.caracteristicas?.superficie_m2;
            
            let features = [];
            if (recamaras) features.push(`${recamaras} rec.`);
            if (banos) features.push(`${banos} baños`);
            if (superficie) features.push(`${superficie} m²`);
            
            return `
                <div class="property-card" onclick="showPropertyDetails('${property.id}')">
                    <div class="property-image">
                        📷 Imagen no disponible
                    </div>
                    <div class="property-content">
                        <div class="property-price">${precio}</div>
                        <div class="property-title">${titulo}</div>
                        <div class="property-location">
                            📍 ${ciudad}${estado ? ', ' + estado : ''}
                        </div>
                        <div class="property-features">
                            ${features.map(f => `<span class="feature">${f}</span>`).join('')}
                        </div>
                        <div class="property-type">${tipo} - ${operacion}</div>
                    </div>
                </div>
            `;
        }
        
        // Mostrar detalles de propiedad
        function showPropertyDetails(propertyId) {
            const property = allProperties.find(p => p.id === propertyId);
            if (!property) return;
            
            const modalContent = document.getElementById('modalContent');
            const precio = property.propiedad?.precio?.formato || 'Precio no disponible';
            const descripcion = property.descripcion_original || 'Sin descripción disponible';
            
            modalContent.innerHTML = `
                <h2>${property.titulo || 'Propiedad'}</h2>
                <div style="margin: 20px 0;">
                    <div style="font-size: 1.5rem; color: #27ae60; font-weight: bold;">${precio}</div>
                    <div style="color: #666; margin: 10px 0;">
                        📍 ${property.ubicacion?.direccion_completa || 'Ubicación no disponible'}
                    </div>
                    <div style="margin: 10px 0;">
                        <span style="background: #667eea; color: white; padding: 5px 10px; border-radius: 15px; font-size: 12px;">
                            ${property.propiedad?.tipo_propiedad || 'Propiedad'} - ${property.operacion || 'No especificado'}
                        </span>
                    </div>
                </div>
                
                <h3>Descripción</h3>
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; white-space: pre-wrap;">${descripcion}</div>
                
                ${property.datos_originales?.caracteristicas ? `
                <h3>Características</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 15px 0;">
                    ${Object.entries(property.datos_originales.caracteristicas)
                        .filter(([key, value]) => value !== null && value !== undefined && value !== '')
                        .map(([key, value]) => `
                            <div style="background: #f8f9fa; padding: 10px; border-radius: 5px;">
                                <strong>${key.replace(/_/g, ' ')}:</strong> ${value}
                            </div>
                        `).join('')}
                </div>
                ` : ''}
                
                ${property.link ? `
                <div style="margin-top: 20px;">
                    <a href="${property.link}" target="_blank" style="background: #667eea; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                        Ver en Facebook Marketplace
                    </a>
                </div>
                ` : ''}
            `;
            
            document.getElementById('propertyModal').style.display = 'block';
        }
        
        // Actualizar paginación
        function updatePagination() {
            const totalPages = Math.ceil(filteredProperties.length / propertiesPerPage);
            const pagination = document.getElementById('pagination');
            
            let paginationHTML = '';
            
            if (currentPage > 1) {
                paginationHTML += `<button onclick="changePage(${currentPage - 1})">Anterior</button>`;
            }
            
            const startPage = Math.max(1, currentPage - 2);
            const endPage = Math.min(totalPages, currentPage + 2);
            
            for (let i = startPage; i <= endPage; i++) {
                paginationHTML += `<button onclick="changePage(${i})" ${i === currentPage ? 'class="active"' : ''}>${i}</button>`;
            }
            
            if (currentPage < totalPages) {
                paginationHTML += `<button onclick="changePage(${currentPage + 1})">Siguiente</button>`;
            }
            
            pagination.innerHTML = paginationHTML;
        }
        
        // Cambiar página
        function changePage(page) {
            currentPage = page;
            displayProperties();
            window.scrollTo(0, 0);
        }
        
        // Aplicar filtros
        function applyFilters() {
            const searchTerm = document.getElementById('searchBox').value.toLowerCase();
            const cityFilter = document.getElementById('cityFilter').value;
            const typeFilter = document.getElementById('typeFilter').value;
            const operationFilter = document.getElementById('operationFilter').value;
            const priceFilter = document.getElementById('priceFilter').value;
            
            filteredProperties = allProperties.filter(property => {
                // Filtro de búsqueda
                if (searchTerm) {
                    const searchableText = [
                        property.titulo,
                        property.descripcion_original,
                        property.ubicacion?.ciudad,
                        property.ubicacion?.estado,
                        property.ubicacion?.direccion_completa,
                        property.propiedad?.precio?.formato
                    ].join(' ').toLowerCase();
                    
                    if (!searchableText.includes(searchTerm)) return false;
                }
                
                // Filtro de ciudad
                if (cityFilter && property.ubicacion?.ciudad !== cityFilter) return false;
                
                // Filtro de tipo
                if (typeFilter && property.propiedad?.tipo_propiedad !== typeFilter) return false;
                
                // Filtro de operación
                if (operationFilter && property.operacion !== operationFilter) return false;
                
                // Filtro de precio
                if (priceFilter) {
                    const [min, max] = priceFilter.split('-').map(Number);
                    const precio = property.propiedad?.precio?.valor || 0;
                    if (precio < min || precio > max) return false;
                }
                
                return true;
            });
            
            currentPage = 1;
            displayProperties();
        }
        
        // Event listeners
        document.getElementById('searchBox').addEventListener('input', applyFilters);
        document.getElementById('cityFilter').addEventListener('change', applyFilters);
        document.getElementById('typeFilter').addEventListener('change', applyFilters);
        document.getElementById('operationFilter').addEventListener('change', applyFilters);
        document.getElementById('priceFilter').addEventListener('change', applyFilters);
        
        // Cerrar modal
        document.querySelector('.modal-close').addEventListener('click', function() {
            document.getElementById('propertyModal').style.display = 'none';
        });
        
        window.addEventListener('click', function(event) {
            if (event.target === document.getElementById('propertyModal')) {
                document.getElementById('propertyModal').style.display = 'none';
            }
        });
        
        // Cargar propiedades al iniciar
        loadProperties();
    </script>
</body>
</html>"""

# Inicializar servidor
if __name__ == "__main__":
    print("🚀 Iniciando Servidor Inmobiliario Completo")
    print("📊 Propiedades disponibles via API")
    print("🌐 Frontend disponible en: http://0.0.0.0:5001")
    print("="*60)
    app.run(host='0.0.0.0', port=5001, debug=False)
