#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏠 Sistema Inmobiliario - Servidor DigitalOcean
Versión específica para deployment en DigitalOcean
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Flask imports
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuración de Flask
app = Flask(__name__)
CORS(app, origins=["*"])

# Variables globales para DigitalOcean
propiedades_data = None
propiedades_indices = None

def cargar_propiedades():
    """Carga las propiedades desde el archivo JSON"""
    global propiedades_data, propiedades_indices
    
    try:
        # Lista de posibles ubicaciones del archivo
        posibles_archivos = [
            "resultados/propiedades_estructuradas.json",
            "./resultados/propiedades_estructuradas.json", 
            "/workspace/resultados/propiedades_estructuradas.json",
            "propiedades_estructuradas.json",
            "./propiedades_estructuradas.json"
        ]
        
        archivo_json = None
        for archivo in posibles_archivos:
            if os.path.exists(archivo):
                archivo_json = archivo
                break
                
        if not archivo_json:
            logger.error(f"❌ No se encontró el archivo en ninguna ubicación")
            logger.error(f"Directorio actual: {os.getcwd()}")
            logger.error(f"Archivos en directorio actual: {os.listdir('.')}")
            # Crear datos mínimos de ejemplo
            propiedades_data = [
                {
                    'id': 'demo_001',
                    'titulo': 'Casa de ejemplo - DigitalOcean',
                    'propiedad': {
                        'precio': {'texto': '$1,000,000'},
                        'tipo_operacion': 'venta'
                    },
                    'ubicacion': {'direccion_completa': 'Ejemplo, Ciudad'},
                    'imagen': '/Imagen_no_disponible.jpg'
                }
            ]
            propiedades_indices = [0]
            logger.warning("⚠️ Usando datos de ejemplo")
            return True
        
        logger.info(f"🔄 Cargando propiedades desde: {archivo_json}")
        
        with open(archivo_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Manejar diferentes estructuras de datos
        if isinstance(data, list):
            # Si es directamente un array de propiedades
            propiedades_data = data
        elif isinstance(data, dict) and 'propiedades' in data:
            # Si es un objeto con campo 'propiedades'
            propiedades_data = data['propiedades']
        else:
            logger.error("❌ Estructura de datos inválida")
            return False
        propiedades_indices = list(range(len(propiedades_data)))
        
        logger.info(f"✅ Cargadas {len(propiedades_data)} propiedades exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error cargando propiedades: {e}")
        logger.error(f"Directorio actual: {os.getcwd()}")
        return False

def obtener_estadisticas():
    """Calcula estadísticas de las propiedades"""
    if not propiedades_data:
        return {'error': 'Datos no cargados'}
        
    try:
        stats = {
            'total': len(propiedades_data),
            'venta': 0,
            'renta': 0,
            'desconocido': 0
        }
        
        for prop in propiedades_data:
            # Extraer tipo de operación según la estructura real
            propiedad_info = prop.get('propiedad', {})
            tipo_op = propiedad_info.get('tipo_operacion', '').lower()
            
            if 'venta' in tipo_op:
                stats['venta'] += 1
            elif 'renta' in tipo_op:
                stats['renta'] += 1
            else:
                stats['desconocido'] += 1
                
        return stats
        
    except Exception as e:
        logger.error(f"Error calculando estadísticas: {e}")
        return {'error': str(e)}

@app.route('/health', methods=['GET'])
def health_check():
    """Health check para DigitalOcean"""
    try:
        if propiedades_data is None:
            return jsonify({
                'status': 'unhealthy',
                'reason': 'Datos no cargados'
            }), 503
            
        return jsonify({
            'status': 'healthy',
            'propiedades_cargadas': len(propiedades_data),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'reason': str(e)
        }), 503

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check para DigitalOcean"""
    try:
        if propiedades_data is None or len(propiedades_data) == 0:
            return jsonify({
                'status': 'not_ready',
                'reason': 'Datos no disponibles'
            }), 503
            
        return jsonify({
            'status': 'ready',
            'propiedades': len(propiedades_data),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error en readiness check: {e}")
        return jsonify({
            'status': 'not_ready',
            'reason': str(e)
        }), 503

@app.route('/api/propiedades', methods=['GET'])
def obtener_propiedades():
    """Obtiene lista paginada de propiedades"""
    try:
        if not propiedades_data:
            return jsonify({'error': 'Datos no disponibles'}), 503
            
        # Parámetros de paginación
        pagina = int(request.args.get('pagina', 1))
        por_pagina = min(int(request.args.get('por_pagina', 24)), 100)
        
        # Calcular índices
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        
        # Obtener propiedades de la página
        propiedades_pagina = propiedades_data[inicio:fin]
        
        # Simplificar datos para respuesta
        propiedades_simplificadas = []
        for i, prop in enumerate(propiedades_pagina, inicio):
            # Extraer datos según la estructura real
            precio_info = prop.get('propiedad', {}).get('precio', {})
            precio = precio_info.get('texto', 'Por consultar')
            
            ubicacion_info = prop.get('ubicacion', {})
            if isinstance(ubicacion_info, dict):
                ubicacion = ubicacion_info.get('direccion_completa', 'Sin ubicación')
            else:
                ubicacion = str(ubicacion_info) if ubicacion_info else 'Sin ubicación'
            
            prop_simple = {
                'id': prop.get('id', f'prop_{i}'),
                'titulo': prop.get('titulo', 'Sin título'),
                'precio': precio,
                'ubicacion': ubicacion,
                'tipo_operacion': prop.get('propiedad', {}).get('tipo_operacion', 'desconocido'),
                'imagen': prop.get('imagen', '/Imagen_no_disponible.jpg')
            }
            propiedades_simplificadas.append(prop_simple)
        
        return jsonify({
            'propiedades': propiedades_simplificadas,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total': len(propiedades_data),
            'total_paginas': (len(propiedades_data) + por_pagina - 1) // por_pagina
        }), 200
        
    except Exception as e:
        logger.error(f"Error obteniendo propiedades: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/estadisticas', methods=['GET'])
def api_estadisticas():
    """API de estadísticas"""
    try:
        stats = obtener_estadisticas()
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Error en estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/buscar', methods=['GET'])
def buscar_propiedades():
    """Búsqueda simple de propiedades"""
    try:
        if not propiedades_data:
            return jsonify({'error': 'Datos no disponibles'}), 503
            
        query = request.args.get('q', '').lower()
        if not query:
            return jsonify({'propiedades': [], 'total': 0}), 200
            
        # Búsqueda simple
        resultados = []
        for prop in propiedades_data:
            titulo = prop.get('titulo', '').lower()
            
            ubicacion_info = prop.get('ubicacion', {})
            if isinstance(ubicacion_info, dict):
                ubicacion = ubicacion_info.get('direccion_completa', '').lower()
            else:
                ubicacion = str(ubicacion_info).lower() if ubicacion_info else ''
            
            if query in titulo or query in ubicacion:
                # Extraer datos según estructura real
                precio_info = prop.get('propiedad', {}).get('precio', {})
                precio = precio_info.get('texto', 'Por consultar')
                
                prop_simple = {
                    'id': prop.get('id'),
                    'titulo': prop.get('titulo'),
                    'precio': precio,
                    'ubicacion': ubicacion_info.get('direccion_completa', '') if isinstance(ubicacion_info, dict) else str(ubicacion_info),
                    'tipo_operacion': prop.get('propiedad', {}).get('tipo_operacion', 'desconocido')
                }
                resultados.append(prop_simple)
                
                if len(resultados) >= 50:  # Limitar resultados
                    break
        
        return jsonify({
            'propiedades': resultados,
            'total': len(resultados),
            'query': query
        }), 200
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    """Página principal"""
    return jsonify({
        'message': '🏠 Sistema Inmobiliario DigitalOcean',
        'status': 'running',
        'propiedades': len(propiedades_data) if propiedades_data else 0,
        'endpoints': [
            '/health',
            '/ready', 
            '/api/propiedades',
            '/api/estadisticas',
            '/api/buscar'
        ]
    })

# Manejo de errores globales
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint no encontrado'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Error interno del servidor'}), 500

def inicializar_aplicacion():
    """Inicializa la aplicación y carga los datos"""
    logger.info("🚀 Inicializando aplicación...")
    
    # Cargar propiedades
    if cargar_propiedades():
        logger.info("✅ Propiedades cargadas exitosamente")
    else:
        logger.error("❌ Error cargando propiedades")
    
    # Mostrar estadísticas
    stats = obtener_estadisticas()
    logger.info(f"📊 Estadísticas: {stats}")
    
    logger.info("🎯 Aplicación lista para servir")

# Inicializar cuando se importe el módulo
if __name__ == "__main__":
    # Modo desarrollo
    inicializar_aplicacion()
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"🏃‍♂️ Ejecutando en modo desarrollo en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    # Modo producción (WSGI)
    inicializar_aplicacion() 