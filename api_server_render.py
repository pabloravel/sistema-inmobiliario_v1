#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema Inmobiliario - Versión Render.com
Servidor Flask optimizado para deployment en Render
"""

import os
import sys
import json
import logging
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import gzip
from typing import Dict, List, Any
from datetime import datetime
import threading

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Crear aplicación Flask
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Variables globales
propiedades_manager = None
cache_datos = {}

class PropiedadesManager:
    def __init__(self, archivo_json: str):
        self.archivo_json = archivo_json
        self.propiedades = {}
        self.indices = {
            'tipo_operacion': {},
            'precio_rango': {},
            'ciudad': {}
        }
        self.cargar_datos()
        self.crear_indices()

    def cargar_datos(self):
        """Cargar datos desde archivo JSON"""
        try:
            if os.path.exists(self.archivo_json):
                logger.info(f"📁 Intentando cargar: {self.archivo_json}")
                with open(self.archivo_json, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"📊 Tipo de datos cargados: {type(data)}")
                    
                    # Manejar diferentes formatos
                    if isinstance(data, dict):
                        self.propiedades = data.get('propiedades', {})
                    elif isinstance(data, list):
                        # Convertir lista a diccionario si es necesario
                        self.propiedades = {f"prop_{i}": prop for i, prop in enumerate(data)}
                        logger.info("🔄 Convertida lista a diccionario")
                    else:
                        logger.error(f"❌ Formato no reconocido: {type(data)}")
                        self.propiedades = {}
                        
                    logger.info(f"✅ Cargadas {len(self.propiedades)} propiedades desde archivo principal")
            else:
                logger.info(f"❌ Archivo principal no encontrado: {self.archivo_json}")
                # Archivos alternativos
                archivos_alt = ['propiedades.json', 'propiedades_demo.json']
                for archivo_alt in archivos_alt:
                    if os.path.exists(archivo_alt):
                        logger.info(f"📁 Intentando cargar alternativo: {archivo_alt}")
                        with open(archivo_alt, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            logger.info(f"📊 Tipo de datos alternativos: {type(data)}")
                            
                            # Manejar diferentes formatos
                            if isinstance(data, dict):
                                self.propiedades = data.get('propiedades', {})
                            elif isinstance(data, list):
                                # Convertir lista a diccionario si es necesario
                                self.propiedades = {f"prop_{i}": prop for i, prop in enumerate(data)}
                                logger.info("🔄 Convertida lista alternativa a diccionario")
                            else:
                                logger.error(f"❌ Formato alternativo no reconocido: {type(data)}")
                                continue
                                
                            logger.info(f"✅ Cargadas {len(self.propiedades)} propiedades desde {archivo_alt}")
                        break
                else:
                    logger.warning("⚠️ No se encontró ningún archivo de propiedades")
                    self.propiedades = {}
        except Exception as e:
            logger.error(f"💥 Error cargando datos: {e}")
            logger.error(f"📍 Error en línea: {e.__traceback__.tb_lineno if e.__traceback__ else 'desconocida'}")
            self.propiedades = {}

    def crear_indices(self):
        """Crear índices para búsqueda rápida"""
        try:
            logger.info(f"🔍 Creando índices para {len(self.propiedades)} propiedades")
            
            for pid, prop in self.propiedades.items():
                if not isinstance(prop, dict):
                    logger.warning(f"⚠️ Propiedad {pid} no es un diccionario: {type(prop)}")
                    continue
                    
                # Índice por tipo de operación
                tipo_op = prop.get('tipo_operacion', 'desconocido').lower()
                if tipo_op not in self.indices['tipo_operacion']:
                    self.indices['tipo_operacion'][tipo_op] = []
                self.indices['tipo_operacion'][tipo_op].append(pid)
                
                # Índice por ciudad
                ciudad = prop.get('ciudad', 'no_especificada').lower()
                if ciudad not in self.indices['ciudad']:
                    self.indices['ciudad'][ciudad] = []
                self.indices['ciudad'][ciudad].append(pid)
                
            logger.info(f"✅ Índices creados exitosamente: {dict(self.indices['tipo_operacion'])}")
        except Exception as e:
            logger.error(f"💥 Error creando índices: {e}")
            logger.error(f"📍 Error en línea: {e.__traceback__.tb_lineno if e.__traceback__ else 'desconocida'}")

    def obtener_propiedades_paginadas(self, pagina: int = 1, por_pagina: int = 24) -> Dict:
        """Obtener propiedades con paginación"""
        try:
            inicio = (pagina - 1) * por_pagina
            propiedades_lista = list(self.propiedades.items())
            total = len(propiedades_lista)
            
            propiedades_pagina = propiedades_lista[inicio:inicio + por_pagina]
            
            resultado = []
            for pid, prop in propiedades_pagina:
                prop_simple = {
                    'id': pid,
                    'titulo': prop.get('titulo', 'Sin título'),
                    'precio': prop.get('precio', 0),
                    'precio_formateado': prop.get('precio_formateado', 'Consultar'),
                    'tipo_operacion': prop.get('tipo_operacion', 'desconocido'),
                    'ubicacion': prop.get('ubicacion', ''),
                    'imagen': f"/resultados/{prop.get('fecha', '2025-05-30')}/{prop.get('imagen', 'default.jpg')}"
                }
                resultado.append(prop_simple)
            
            return {
                'propiedades': resultado,
                'total': total,
                'pagina': pagina,
                'por_pagina': por_pagina,
                'total_paginas': (total + por_pagina - 1) // por_pagina
            }
        except Exception as e:
            logger.error(f"Error obteniendo propiedades paginadas: {e}")
            return {'propiedades': [], 'total': 0, 'pagina': 1, 'por_pagina': por_pagina, 'total_paginas': 0}

    def obtener_estadisticas(self) -> Dict:
        """Obtener estadísticas generales"""
        try:
            stats = {
                'total': len(self.propiedades),
                'venta': len(self.indices['tipo_operacion'].get('venta', [])),
                'renta': len(self.indices['tipo_operacion'].get('renta', [])),
                'desconocido': len(self.indices['tipo_operacion'].get('desconocido', []))
            }
            return stats
        except Exception as e:
            logger.error(f"Error calculando estadísticas: {e}")
            return {'total': 0, 'venta': 0, 'renta': 0, 'desconocido': 0}

# Inicializar manager
def inicializar_manager():
    global propiedades_manager
    if propiedades_manager is None:
        # Buscar archivo en múltiples ubicaciones
        archivos_posibles = [
            'propiedades_estructuradas.json',  # Directorio raíz
            'resultados/propiedades_estructuradas.json',  # Subdirectorio
            'propiedades.json',  # Alternativo en raíz
            'propiedades_demo.json'  # Demo como último recurso
        ]
        
        archivo_encontrado = None
        for archivo in archivos_posibles:
            if os.path.exists(archivo):
                archivo_encontrado = archivo
                logger.info(f"📁 Archivo encontrado: {archivo}")
                break
        
        if not archivo_encontrado:
            archivo_encontrado = 'propiedades_demo.json'  # Fallback
            logger.warning("⚠️ Usando archivo demo como fallback")
            
        propiedades_manager = PropiedadesManager(archivo_encontrado)
        logger.info("🏠 Sistema inmobiliario inicializado para Render")

# Rutas API
@app.route('/health', methods=['GET'])
def health_check():
    """Health check para Render"""
    try:
        stats = propiedades_manager.obtener_estadisticas() if propiedades_manager else {'total': 0}
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'propiedades': stats['total'],
            'platform': 'render'
        })
    except Exception as e:
        logger.error(f"Error en health check: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check para Render"""
    return jsonify({'status': 'ready', 'timestamp': datetime.now().isoformat()})

@app.route('/api/propiedades', methods=['GET'])
def obtener_propiedades():
    """Obtener propiedades con paginación"""
    try:
        pagina = int(request.args.get('pagina', 1))
        por_pagina = int(request.args.get('por_pagina', 24))
        
        if not propiedades_manager:
            inicializar_manager()
            
        resultado = propiedades_manager.obtener_propiedades_paginadas(pagina, por_pagina)
        
        # Comprimir respuesta si es grande
        response_data = json.dumps(resultado, ensure_ascii=False)
        if len(response_data) > 1000:
            response = Response(
                gzip.compress(response_data.encode('utf-8')),
                mimetype='application/json',
                headers={'Content-Encoding': 'gzip'}
            )
        else:
            response = jsonify(resultado)
            
        return response
    except Exception as e:
        logger.error(f"Error obteniendo propiedades: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/estadisticas', methods=['GET'])
def obtener_estadisticas():
    """Obtener estadísticas del sistema"""
    try:
        if not propiedades_manager:
            inicializar_manager()
            
        stats = propiedades_manager.obtener_estadisticas()
        logger.info(f"📊 Estadísticas: {stats}")
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/api/propiedades/<propiedad_id>', methods=['GET'])
def obtener_propiedad_detalle(propiedad_id: str):
    """Obtener detalle de una propiedad específica"""
    try:
        if not propiedades_manager:
            inicializar_manager()
            
        propiedad = propiedades_manager.propiedades.get(propiedad_id)
        if not propiedad:
            return jsonify({'error': 'Propiedad no encontrada'}), 404
            
        return jsonify(propiedad)
    except Exception as e:
        logger.error(f"Error obteniendo detalle de propiedad: {e}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/resultados/<path:filename>')
def servir_imagen(filename):
    """Servir imágenes de propiedades"""
    try:
        directorio = os.path.join(os.getcwd(), 'resultados')
        return send_from_directory(directorio, filename)
    except Exception as e:
        logger.error(f"Error sirviendo imagen {filename}: {e}")
        # Imagen por defecto
        return send_from_directory('resultados', 'imagen_no_disponible.jpg'), 404

@app.route('/frontend_desarrollo.html')
def servir_frontend():
    """Servir frontend de desarrollo"""
    try:
        return send_from_directory('.', 'frontend_desarrollo.html')
    except Exception as e:
        logger.error(f"Error sirviendo frontend: {e}")
        return "Frontend no disponible", 404

@app.route('/')
def index():
    """Página principal"""
    return '''
    <h1>🏠 Sistema Inmobiliario</h1>
    <p>Sistema corriendo en <strong>Render.com</strong></p>
    <ul>
        <li><a href="/health">Health Check</a></li>
        <li><a href="/api/estadisticas">Estadísticas</a></li>
        <li><a href="/api/propiedades">API Propiedades</a></li>
        <li><a href="/frontend_desarrollo.html">Frontend</a></li>
    </ul>
    '''

# Inicialización al arrancar
if __name__ == '__main__':
    # Inicializar manager
    inicializar_manager()
    
    # Configurar puerto
    port = int(os.environ.get('PORT', 5001))
    
    logger.info(f"🚀 Iniciando servidor en puerto {port} para Render")
    
    # Ejecutar aplicación
    app.run(host='0.0.0.0', port=port, debug=False)
else:
    # Para gunicorn
    inicializar_manager()

# Variable para export de gunicorn
application = app 