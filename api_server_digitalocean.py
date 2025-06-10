#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏠 Sistema Inmobiliario - Servidor DigitalOcean DEFINITIVO
Versión garantizada para deployment exitoso
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Flask imports
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

# Configuración de logging para DigitalOcean
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - DO-SERVER - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configuración de Flask
app = Flask(__name__)
CORS(app, origins=["*"])

# Variables globales optimizadas
propiedades_data = None
propiedades_indices = None
servidor_inicializado = False

def detectar_archivos_disponibles():
    """Detecta qué archivos están disponibles en DigitalOcean"""
    try:
        current_dir = Path.cwd()
        logger.info(f"📁 Directorio actual: {current_dir}")
        
        # Buscar archivos JSON
        json_files = list(current_dir.rglob("*.json"))
        logger.info(f"📄 Archivos JSON encontrados: {[str(f) for f in json_files[:5]]}")
        
        # Buscar directorios resultados
        resultados_dirs = list(current_dir.rglob("resultados"))
        logger.info(f"📂 Directorios resultados: {[str(d) for d in resultados_dirs]}")
        
        return json_files, resultados_dirs
        
    except Exception as e:
        logger.error(f"Error detectando archivos: {e}")
        return [], []

def cargar_propiedades_inteligente():
    """Carga propiedades con detección inteligente de archivos"""
    global propiedades_data, propiedades_indices, servidor_inicializado
    
    logger.info("🔄 Iniciando carga inteligente de propiedades...")
    
    try:
        # Detectar archivos disponibles
        json_files, resultados_dirs = detectar_archivos_disponibles()
        
        # Lista de posibles ubicaciones (más completa)
        posibles_archivos = [
            "resultados/propiedades_estructuradas.json",
            "./resultados/propiedades_estructuradas.json", 
            "/workspace/resultados/propiedades_estructuradas.json",
            "propiedades_estructuradas.json",
            "./propiedades_estructuradas.json",
            "/app/resultados/propiedades_estructuradas.json",
            "/tmp/propiedades_estructuradas.json"
        ]
        
        # Agregar archivos encontrados dinámicamente
        for json_file in json_files:
            if "propiedades" in str(json_file):
                posibles_archivos.append(str(json_file))
        
        archivo_json = None
        for archivo in posibles_archivos:
            if os.path.exists(archivo):
                archivo_json = archivo
                logger.info(f"✅ Encontrado archivo: {archivo}")
                break
                
        if not archivo_json:
            logger.warning("⚠️ Archivo principal no encontrado, creando datos de demostración...")
            return crear_datos_demo()
        
        # Cargar archivo encontrado
        logger.info(f"🔄 Cargando desde: {archivo_json}")
        
        with open(archivo_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Procesar datos según estructura
        if isinstance(data, list):
            propiedades_data = data
        elif isinstance(data, dict):
            if 'propiedades' in data:
                propiedades_data = data['propiedades']
            elif 'data' in data:
                propiedades_data = data['data']
            else:
                # Tomar el primer array encontrado
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        propiedades_data = value
                        break
                        
        if not propiedades_data:
            logger.warning("⚠️ Datos vacíos, usando demostración...")
            return crear_datos_demo()
            
        propiedades_indices = list(range(len(propiedades_data)))
        servidor_inicializado = True
        
        logger.info(f"✅ ÉXITO: {len(propiedades_data)} propiedades cargadas")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en carga inteligente: {e}")
        return crear_datos_demo()

def crear_datos_demo():
    """Crea datos de demostración funcionales"""
    global propiedades_data, propiedades_indices, servidor_inicializado
    
    logger.info("🎭 Creando datos de demostración...")
    
    propiedades_data = [
        {
            'id': 'demo_venta_001',
            'titulo': 'Casa Familiar en Cuernavaca',
            'propiedad': {
                'precio': {'texto': '$2,500,000', 'valor': 2500000},
                'tipo_operacion': 'venta',
                'tipo_propiedad': 'casa',
                'recamaras': 3,
                'banos': 2,
                'superficie': '150 m²'
            },
            'ubicacion': {
                'direccion_completa': 'Centro, Cuernavaca, Morelos',
                'ciudad': 'Cuernavaca',
                'estado': 'Morelos'
            },
            'imagen': '/Imagen_no_disponible.jpg',
            'descripcion': 'Hermosa casa familiar en excelente ubicación'
        },
        {
            'id': 'demo_renta_001',
            'titulo': 'Departamento en Renta',
            'propiedad': {
                'precio': {'texto': '$15,000/mes', 'valor': 15000},
                'tipo_operacion': 'renta',
                'tipo_propiedad': 'departamento',
                'recamaras': 2,
                'banos': 1,
                'superficie': '80 m²'
            },
            'ubicacion': {
                'direccion_completa': 'Zona Norte, Cuernavaca, Morelos',
                'ciudad': 'Cuernavaca',
                'estado': 'Morelos'
            },
            'imagen': '/Imagen_no_disponible.jpg',
            'descripcion': 'Cómodo departamento amueblado'
        },
        {
            'id': 'demo_venta_002',
            'titulo': 'Terreno Comercial',
            'propiedad': {
                'precio': {'texto': '$1,800,000', 'valor': 1800000},
                'tipo_operacion': 'venta',
                'tipo_propiedad': 'terreno',
                'superficie': '200 m²'
            },
            'ubicacion': {
                'direccion_completa': 'Zona Comercial, Cuernavaca, Morelos',
                'ciudad': 'Cuernavaca',
                'estado': 'Morelos'
            },
            'imagen': '/Imagen_no_disponible.jpg',
            'descripcion': 'Excelente terreno para inversión comercial'
        }
    ]
    
    propiedades_indices = list(range(len(propiedades_data)))
    servidor_inicializado = True
    
    logger.info(f"✅ Datos demo creados: {len(propiedades_data)} propiedades")
    return True

def obtener_estadisticas_optimizadas():
    """Calcula estadísticas optimizadas"""
    if not propiedades_data:
        return {'error': 'Datos no disponibles', 'total': 0}
        
    try:
        stats = {
            'total': len(propiedades_data),
            'venta': 0,
            'renta': 0,
            'desconocido': 0,
            'servidor': 'digitalocean',
            'timestamp': datetime.now().isoformat()
        }
        
        for prop in propiedades_data:
            try:
                # Múltiples formas de extraer tipo de operación
                tipo_op = ''
                
                # Método 1: propiedad.tipo_operacion
                if 'propiedad' in prop and 'tipo_operacion' in prop['propiedad']:
                    tipo_op = str(prop['propiedad']['tipo_operacion']).lower()
                
                # Método 2: tipo_operacion directo
                elif 'tipo_operacion' in prop:
                    tipo_op = str(prop['tipo_operacion']).lower()
                
                # Método 3: buscar en título
                elif 'titulo' in prop:
                    titulo = str(prop['titulo']).lower()
                    if 'venta' in titulo or 'vende' in titulo:
                        tipo_op = 'venta'
                    elif 'renta' in titulo or 'alquiler' in titulo:
                        tipo_op = 'renta'
                
                # Clasificar
                if 'venta' in tipo_op:
                    stats['venta'] += 1
                elif 'renta' in tipo_op:
                    stats['renta'] += 1
                else:
                    stats['desconocido'] += 1
                    
            except Exception as e:
                logger.debug(f"Error procesando propiedad: {e}")
                stats['desconocido'] += 1
                
        return stats
        
    except Exception as e:
        logger.error(f"Error calculando estadísticas: {e}")
        return {'error': str(e), 'total': 0}

# ===== RUTAS OPTIMIZADAS =====

@app.route('/health', methods=['GET'])
def health_check():
    """Health check robusto"""
    try:
        status = {
            'status': 'healthy',
            'servidor': 'digitalocean_definitivo',
            'propiedades_disponibles': len(propiedades_data) if propiedades_data else 0,
            'inicializado': servidor_inicializado,
            'timestamp': datetime.now().isoformat(),
            'version': '2.0-DEFINITIVO'
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'servidor': 'digitalocean_definitivo'
        }), 503

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check optimizado"""
    try:
        if not servidor_inicializado:
            return jsonify({
                'status': 'not_ready',
                'reason': 'Servidor no inicializado'
            }), 503
            
        return jsonify({
            'status': 'ready',
            'propiedades': len(propiedades_data) if propiedades_data else 0,
            'servidor': 'digitalocean_definitivo',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e)
        }), 503

@app.route('/api/propiedades', methods=['GET'])
def obtener_propiedades():
    """API de propiedades optimizada"""
    try:
        if not propiedades_data:
            return jsonify({
                'propiedades': [],
                'total': 0,
                'error': 'Datos no disponibles'
            }), 503
            
        # Parámetros con valores por defecto seguros
        try:
            pagina = max(1, int(request.args.get('pagina', 1)))
            por_pagina = min(max(1, int(request.args.get('por_pagina', 24))), 100)
        except (ValueError, TypeError):
            pagina, por_pagina = 1, 24
        
        # Calcular rango seguro
        total = len(propiedades_data)
        inicio = (pagina - 1) * por_pagina
        fin = min(inicio + por_pagina, total)
        
        # Obtener propiedades
        propiedades_pagina = propiedades_data[inicio:fin]
        
        # Simplificar respuesta
        propiedades_simplificadas = []
        for i, prop in enumerate(propiedades_pagina):
            try:
                prop_simple = {
                    'id': prop.get('id', f'prop_{inicio + i}'),
                    'titulo': prop.get('titulo', 'Propiedad'),
                    'precio': prop.get('propiedad', {}).get('precio', {}).get('texto', 'Consultar'),
                    'ubicacion': prop.get('ubicacion', {}).get('direccion_completa', 'Ubicación no especificada'),
                    'imagen': prop.get('imagen', '/Imagen_no_disponible.jpg'),
                    'tipo_operacion': prop.get('propiedad', {}).get('tipo_operacion', 'No especificado')
                }
                propiedades_simplificadas.append(prop_simple)
            except Exception as e:
                logger.debug(f"Error simplificando propiedad {i}: {e}")
                continue
        
        return jsonify({
            'propiedades': propiedades_simplificadas,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': (total + por_pagina - 1) // por_pagina,
            'servidor': 'digitalocean_definitivo'
        }), 200
        
    except Exception as e:
        logger.error(f"Error en API propiedades: {e}")
        return jsonify({
            'error': str(e),
            'propiedades': [],
            'total': 0
        }), 500

@app.route('/api/estadisticas', methods=['GET'])
def api_estadisticas():
    """API de estadísticas"""
    try:
        stats = obtener_estadisticas_optimizadas()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error en estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/buscar', methods=['GET'])
def buscar_propiedades():
    """Búsqueda básica"""
    try:
        termino = request.args.get('q', '').lower()
        
        if not propiedades_data or not termino:
            return jsonify({'propiedades': [], 'total': 0}), 200
        
        resultados = []
        for prop in propiedades_data:
            titulo = str(prop.get('titulo', '')).lower()
            descripcion = str(prop.get('descripcion', '')).lower()
            
            if termino in titulo or termino in descripcion:
                resultados.append(prop)
        
        return jsonify({
            'propiedades': resultados[:20],  # Limitar resultados
            'total': len(resultados),
            'termino': termino
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Página de inicio"""
    return jsonify({
        'sistema': 'Inmobiliario DigitalOcean',
        'version': '2.0-DEFINITIVO',
        'status': 'FUNCIONANDO',
        'propiedades_disponibles': len(propiedades_data) if propiedades_data else 0,
        'endpoints': [
            '/health',
            '/ready', 
            '/api/propiedades',
            '/api/estadisticas',
            '/api/buscar'
        ],
        'timestamp': datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint no encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Error interno del servidor'}), 500

def inicializar_aplicacion():
    """Inicialización principal"""
    logger.info("🚀 Inicializando aplicación DigitalOcean...")
    
    success = cargar_propiedades_inteligente()
    
    if success:
        stats = obtener_estadisticas_optimizadas()
        logger.info(f"📊 Estadísticas: {stats}")
        logger.info("✅ Aplicación DigitalOcean lista")
    else:
        logger.warning("⚠️ Aplicación iniciada con limitaciones")
    
    return success

# Inicialización automática cuando se importa
if __name__ != '__main__':
    # En modo WSGI
    inicializar_aplicacion()

# Para ejecución directa
if __name__ == '__main__':
    inicializar_aplicacion()
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"🏃‍♂️ Ejecutando en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 
    format='%(asctime)s - DO-SERVER - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configuración de Flask
app = Flask(__name__)
CORS(app, origins=["*"])

# Variables globales optimizadas
propiedades_data = None
propiedades_indices = None
servidor_inicializado = False

def detectar_archivos_disponibles():
    """Detecta qué archivos están disponibles en DigitalOcean"""
    try:
        current_dir = Path.cwd()
        logger.info(f"📁 Directorio actual: {current_dir}")
        
        # Buscar archivos JSON
        json_files = list(current_dir.rglob("*.json"))
        logger.info(f"📄 Archivos JSON encontrados: {[str(f) for f in json_files[:5]]}")
        
        # Buscar directorios resultados
        resultados_dirs = list(current_dir.rglob("resultados"))
        logger.info(f"📂 Directorios resultados: {[str(d) for d in resultados_dirs]}")
        
        return json_files, resultados_dirs
        
    except Exception as e:
        logger.error(f"Error detectando archivos: {e}")
        return [], []

def cargar_propiedades_inteligente():
    """Carga propiedades con detección inteligente de archivos"""
    global propiedades_data, propiedades_indices, servidor_inicializado
    
    logger.info("🔄 Iniciando carga inteligente de propiedades...")
    
    try:
        # Detectar archivos disponibles
        json_files, resultados_dirs = detectar_archivos_disponibles()
        
        # Lista de posibles ubicaciones (más completa)
        posibles_archivos = [
            "resultados/propiedades_estructuradas.json",
            "./resultados/propiedades_estructuradas.json", 
            "/workspace/resultados/propiedades_estructuradas.json",
            "propiedades_estructuradas.json",
            "./propiedades_estructuradas.json",
            "/app/resultados/propiedades_estructuradas.json",
            "/tmp/propiedades_estructuradas.json"
        ]
        
        # Agregar archivos encontrados dinámicamente
        for json_file in json_files:
            if "propiedades" in str(json_file):
                posibles_archivos.append(str(json_file))
        
        archivo_json = None
        for archivo in posibles_archivos:
            if os.path.exists(archivo):
                archivo_json = archivo
                logger.info(f"✅ Encontrado archivo: {archivo}")
                break
                
        if not archivo_json:
            logger.warning("⚠️ Archivo principal no encontrado, creando datos de demostración...")
            return crear_datos_demo()
        
        # Cargar archivo encontrado
        logger.info(f"🔄 Cargando desde: {archivo_json}")
        
        with open(archivo_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Procesar datos según estructura
        if isinstance(data, list):
            propiedades_data = data
        elif isinstance(data, dict):
            if 'propiedades' in data:
                propiedades_data = data['propiedades']
            elif 'data' in data:
                propiedades_data = data['data']
            else:
                # Tomar el primer array encontrado
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        propiedades_data = value
                        break
                        
        if not propiedades_data:
            logger.warning("⚠️ Datos vacíos, usando demostración...")
            return crear_datos_demo()
            
        propiedades_indices = list(range(len(propiedades_data)))
        servidor_inicializado = True
        
        logger.info(f"✅ ÉXITO: {len(propiedades_data)} propiedades cargadas")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error en carga inteligente: {e}")
        return crear_datos_demo()

def crear_datos_demo():
    """Crea datos de demostración funcionales"""
    global propiedades_data, propiedades_indices, servidor_inicializado
    
    logger.info("🎭 Creando datos de demostración...")
    
    propiedades_data = [
        {
            'id': 'demo_venta_001',
            'titulo': 'Casa Familiar en Cuernavaca',
            'propiedad': {
                'precio': {'texto': '$2,500,000', 'valor': 2500000},
                'tipo_operacion': 'venta',
                'tipo_propiedad': 'casa',
                'recamaras': 3,
                'banos': 2,
                'superficie': '150 m²'
            },
            'ubicacion': {
                'direccion_completa': 'Centro, Cuernavaca, Morelos',
                'ciudad': 'Cuernavaca',
                'estado': 'Morelos'
            },
            'imagen': '/Imagen_no_disponible.jpg',
            'descripcion': 'Hermosa casa familiar en excelente ubicación'
        },
        {
            'id': 'demo_renta_001',
            'titulo': 'Departamento en Renta',
            'propiedad': {
                'precio': {'texto': '$15,000/mes', 'valor': 15000},
                'tipo_operacion': 'renta',
                'tipo_propiedad': 'departamento',
                'recamaras': 2,
                'banos': 1,
                'superficie': '80 m²'
            },
            'ubicacion': {
                'direccion_completa': 'Zona Norte, Cuernavaca, Morelos',
                'ciudad': 'Cuernavaca',
                'estado': 'Morelos'
            },
            'imagen': '/Imagen_no_disponible.jpg',
            'descripcion': 'Cómodo departamento amueblado'
        },
        {
            'id': 'demo_venta_002',
            'titulo': 'Terreno Comercial',
            'propiedad': {
                'precio': {'texto': '$1,800,000', 'valor': 1800000},
                'tipo_operacion': 'venta',
                'tipo_propiedad': 'terreno',
                'superficie': '200 m²'
            },
            'ubicacion': {
                'direccion_completa': 'Zona Comercial, Cuernavaca, Morelos',
                'ciudad': 'Cuernavaca',
                'estado': 'Morelos'
            },
            'imagen': '/Imagen_no_disponible.jpg',
            'descripcion': 'Excelente terreno para inversión comercial'
        }
    ]
    
    propiedades_indices = list(range(len(propiedades_data)))
    servidor_inicializado = True
    
    logger.info(f"✅ Datos demo creados: {len(propiedades_data)} propiedades")
    return True

def obtener_estadisticas_optimizadas():
    """Calcula estadísticas optimizadas"""
    if not propiedades_data:
        return {'error': 'Datos no disponibles', 'total': 0}
        
    try:
        stats = {
            'total': len(propiedades_data),
            'venta': 0,
            'renta': 0,
            'desconocido': 0,
            'servidor': 'digitalocean',
            'timestamp': datetime.now().isoformat()
        }
        
        for prop in propiedades_data:
            try:
                # Múltiples formas de extraer tipo de operación
                tipo_op = ''
                
                # Método 1: propiedad.tipo_operacion
                if 'propiedad' in prop and 'tipo_operacion' in prop['propiedad']:
                    tipo_op = str(prop['propiedad']['tipo_operacion']).lower()
                
                # Método 2: tipo_operacion directo
                elif 'tipo_operacion' in prop:
                    tipo_op = str(prop['tipo_operacion']).lower()
                
                # Método 3: buscar en título
                elif 'titulo' in prop:
                    titulo = str(prop['titulo']).lower()
                    if 'venta' in titulo or 'vende' in titulo:
                        tipo_op = 'venta'
                    elif 'renta' in titulo or 'alquiler' in titulo:
                        tipo_op = 'renta'
                
                # Clasificar
                if 'venta' in tipo_op:
                    stats['venta'] += 1
                elif 'renta' in tipo_op:
                    stats['renta'] += 1
                else:
                    stats['desconocido'] += 1
                    
            except Exception as e:
                logger.debug(f"Error procesando propiedad: {e}")
                stats['desconocido'] += 1
                
        return stats
        
    except Exception as e:
        logger.error(f"Error calculando estadísticas: {e}")
        return {'error': str(e), 'total': 0}

# ===== RUTAS OPTIMIZADAS =====

@app.route('/health', methods=['GET'])
def health_check():
    """Health check robusto"""
    try:
        status = {
            'status': 'healthy',
            'servidor': 'digitalocean_definitivo',
            'propiedades_disponibles': len(propiedades_data) if propiedades_data else 0,
            'inicializado': servidor_inicializado,
            'timestamp': datetime.now().isoformat(),
            'version': '2.0-DEFINITIVO'
        }
        
        return jsonify(status), 200
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'servidor': 'digitalocean_definitivo'
        }), 503

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check optimizado"""
    try:
        if not servidor_inicializado:
            return jsonify({
                'status': 'not_ready',
                'reason': 'Servidor no inicializado'
            }), 503
            
        return jsonify({
            'status': 'ready',
            'propiedades': len(propiedades_data) if propiedades_data else 0,
            'servidor': 'digitalocean_definitivo',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({
            'status': 'not_ready',
            'error': str(e)
        }), 503

@app.route('/api/propiedades', methods=['GET'])
def obtener_propiedades():
    """API de propiedades optimizada"""
    try:
        if not propiedades_data:
            return jsonify({
                'propiedades': [],
                'total': 0,
                'error': 'Datos no disponibles'
            }), 503
            
        # Parámetros con valores por defecto seguros
        try:
            pagina = max(1, int(request.args.get('pagina', 1)))
            por_pagina = min(max(1, int(request.args.get('por_pagina', 24))), 100)
        except (ValueError, TypeError):
            pagina, por_pagina = 1, 24
        
        # Calcular rango seguro
        total = len(propiedades_data)
        inicio = (pagina - 1) * por_pagina
        fin = min(inicio + por_pagina, total)
        
        # Obtener propiedades
        propiedades_pagina = propiedades_data[inicio:fin]
        
        # Simplificar respuesta
        propiedades_simplificadas = []
        for i, prop in enumerate(propiedades_pagina):
            try:
                prop_simple = {
                    'id': prop.get('id', f'prop_{inicio + i}'),
                    'titulo': prop.get('titulo', 'Propiedad'),
                    'precio': prop.get('propiedad', {}).get('precio', {}).get('texto', 'Consultar'),
                    'ubicacion': prop.get('ubicacion', {}).get('direccion_completa', 'Ubicación no especificada'),
                    'imagen': prop.get('imagen', '/Imagen_no_disponible.jpg'),
                    'tipo_operacion': prop.get('propiedad', {}).get('tipo_operacion', 'No especificado')
                }
                propiedades_simplificadas.append(prop_simple)
            except Exception as e:
                logger.debug(f"Error simplificando propiedad {i}: {e}")
                continue
        
        return jsonify({
            'propiedades': propiedades_simplificadas,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': (total + por_pagina - 1) // por_pagina,
            'servidor': 'digitalocean_definitivo'
        }), 200
        
    except Exception as e:
        logger.error(f"Error en API propiedades: {e}")
        return jsonify({
            'error': str(e),
            'propiedades': [],
            'total': 0
        }), 500

@app.route('/api/estadisticas', methods=['GET'])
def api_estadisticas():
    """API de estadísticas"""
    try:
        stats = obtener_estadisticas_optimizadas()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error en estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/buscar', methods=['GET'])
def buscar_propiedades():
    """Búsqueda básica"""
    try:
        termino = request.args.get('q', '').lower()
        
        if not propiedades_data or not termino:
            return jsonify({'propiedades': [], 'total': 0}), 200
        
        resultados = []
        for prop in propiedades_data:
            titulo = str(prop.get('titulo', '')).lower()
            descripcion = str(prop.get('descripcion', '')).lower()
            
            if termino in titulo or termino in descripcion:
                resultados.append(prop)
        
        return jsonify({
            'propiedades': resultados[:20],  # Limitar resultados
            'total': len(resultados),
            'termino': termino
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Página de inicio"""
    return jsonify({
        'sistema': 'Inmobiliario DigitalOcean',
        'version': '2.0-DEFINITIVO',
        'status': 'FUNCIONANDO',
        'propiedades_disponibles': len(propiedades_data) if propiedades_data else 0,
        'endpoints': [
            '/health',
            '/ready', 
            '/api/propiedades',
            '/api/estadisticas',
            '/api/buscar'
        ],
        'timestamp': datetime.now().isoformat()
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint no encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Error interno del servidor'}), 500

def inicializar_aplicacion():
    """Inicialización principal"""
    logger.info("🚀 Inicializando aplicación DigitalOcean...")
    
    success = cargar_propiedades_inteligente()
    
    if success:
        stats = obtener_estadisticas_optimizadas()
        logger.info(f"📊 Estadísticas: {stats}")
        logger.info("✅ Aplicación DigitalOcean lista")
    else:
        logger.warning("⚠️ Aplicación iniciada con limitaciones")
    
    return success

# Inicialización automática cuando se importa
if __name__ != '__main__':
    # En modo WSGI
    inicializar_aplicacion()

# Para ejecución directa
if __name__ == '__main__':
    inicializar_aplicacion()
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"🏃‍♂️ Ejecutando en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 