#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Server Específico para DigitalOcean
Versión simplificada y optimizada para deployment en la nube
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación Flask
app = Flask(__name__)
CORS(app)

# Variables globales
propiedades_data = []
propiedades_indices = {}

def cargar_propiedades():
    """Cargar propiedades desde el archivo JSON"""
    global propiedades_data, propiedades_indices
    
    archivo_json = 'resultados/propiedades_estructuradas.json'
    
    try:
        if not os.path.exists(archivo_json):
            logger.error(f"❌ Archivo no encontrado: {archivo_json}")
            return False
            
        with open(archivo_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if 'propiedades' in data:
            propiedades_data = data['propiedades']
        else:
            propiedades_data = data if isinstance(data, list) else []
            
        # Crear índices básicos
        propiedades_indices = {i: prop for i, prop in enumerate(propiedades_data)}
        
        logger.info(f"✅ Cargadas {len(propiedades_data)} propiedades")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error cargando propiedades: {e}")
        return False

def obtener_estadisticas():
    """Obtener estadísticas básicas"""
    if not propiedades_data:
        return {
            'total': 0,
            'venta': 0,
            'renta': 0,
            'desconocido': 0
        }
    
    stats = {'total': len(propiedades_data), 'venta': 0, 'renta': 0, 'desconocido': 0}
    
    for prop in propiedades_data:
        tipo_op = prop.get('tipo_operacion', '').lower().strip()
        
        # Mapear diferentes variaciones
        if tipo_op in ['venta', 'en venta', 'se vende']:
            stats['venta'] += 1
        elif tipo_op in ['renta', 'en renta', 'se renta', 'alquiler']:
            stats['renta'] += 1
        else:
            stats['desconocido'] += 1
            
    return stats

# ========================================
# RUTAS API
# ========================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check para DigitalOcean"""
    try:
        stats = obtener_estadisticas()
        return jsonify({
            'status': 'healthy',
            'propiedades_cargadas': stats['total'],
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0-digitalocean'
        })
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check para DigitalOcean"""
    try:
        if not propiedades_data:
            return jsonify({
                'status': 'not_ready', 
                'reason': 'Propiedades no cargadas'
            }), 503
            
        return jsonify({
            'status': 'ready',
            'propiedades': len(propiedades_data),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error en readiness check: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/propiedades', methods=['GET'])
def obtener_propiedades():
    """Obtener propiedades con paginación"""
    try:
        pagina = int(request.args.get('pagina', 1))
        por_pagina = int(request.args.get('por_pagina', 24))
        
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        
        propiedades_pagina = propiedades_data[inicio:fin]
        
        return jsonify({
            'propiedades': propiedades_pagina,
            'total': len(propiedades_data),
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': (len(propiedades_data) + por_pagina - 1) // por_pagina
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo propiedades: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/propiedades/<propiedad_id>', methods=['GET'])
def obtener_propiedad_detalle(propiedad_id: str):
    """Obtener detalle de una propiedad específica"""
    try:
        for prop in propiedades_data:
            if str(prop.get('id', '')) == propiedad_id:
                return jsonify(prop)
                
        return jsonify({'error': 'Propiedad no encontrada'}), 404
        
    except Exception as e:
        logger.error(f"Error obteniendo propiedad {propiedad_id}: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas_api():
    """Obtener estadísticas del sistema"""
    try:
        stats = obtener_estadisticas()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/buscar', methods=['GET'])
def buscar_propiedades():
    """Búsqueda básica de propiedades"""
    try:
        termino = request.args.get('q', '').lower()
        if not termino:
            return jsonify({'propiedades': [], 'total': 0})
            
        resultados = []
        for prop in propiedades_data:
            # Buscar en título y descripción
            titulo = str(prop.get('titulo', '')).lower()
            descripcion = str(prop.get('descripcion', '')).lower()
            ubicacion = str(prop.get('ubicacion', '')).lower()
            
            if (termino in titulo or 
                termino in descripcion or 
                termino in ubicacion):
                resultados.append(prop)
                
        return jsonify({
            'propiedades': resultados[:50],  # Limitar a 50 resultados
            'total': len(resultados)
        })
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/frontend_desarrollo.html')
def servir_frontend():
    """Servir frontend básico"""
    try:
        return send_from_directory('.', 'frontend_desarrollo.html')
    except Exception:
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Sistema Inmobiliario</title></head>
        <body>
        <h1>Sistema Inmobiliario DigitalOcean</h1>
        <p>API funcionando correctamente</p>
        <p><a href="/health">Health Check</a></p>
        <p><a href="/api/estadisticas">Estadísticas</a></p>
        </body>
        </html>
        """

@app.route('/resultados/<path:filename>')
def servir_imagen(filename):
    """Servir imágenes"""
    try:
        return send_from_directory('resultados', filename)
    except Exception:
        return jsonify({'error': 'Imagen no encontrada'}), 404

@app.route('/')
def index():
    """Página principal"""
    try:
        stats = obtener_estadisticas()
        return jsonify({
            'mensaje': 'Sistema Inmobiliario DigitalOcean',
            'status': 'activo',
            'propiedades': stats,
            'endpoints': [
                '/health',
                '/ready', 
                '/api/propiedades',
                '/api/estadisticas',
                '/api/buscar',
                '/frontend_desarrollo.html'
            ]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================
# INICIALIZACIÓN
# ========================================

def inicializar_aplicacion():
    """Inicializar la aplicación"""
    logger.info("🚀 Inicializando Sistema Inmobiliario para DigitalOcean...")
    
    # Cargar propiedades
    if cargar_propiedades():
        stats = obtener_estadisticas()
        logger.info(f"✅ Sistema inicializado exitosamente")
        logger.info(f"📊 Propiedades cargadas: {stats}")
        return True
    else:
        logger.error("❌ Error inicializando sistema")
        return False

# Inicializar al importar
if __name__ == "__main__" or True:  # Siempre inicializar
    inicializar_aplicacion()

# Para desarrollo local
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"🌐 Ejecutando en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False) 