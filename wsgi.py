#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏠 WSGI Ultra-Robusto para DigitalOcean
Versión con debug completo y múltiples fallbacks
"""

import os
import sys
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - WSGI - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Agregar directorio actual al path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

logger.info(f"🔧 WSGI iniciando...")
logger.info(f"📁 Directorio actual: {current_dir}")
logger.info(f"🐍 Python path: {sys.path[:3]}")
logger.info(f"🌍 Variables de entorno PORT: {os.environ.get('PORT', 'No definido')}")

# Intentar importar aplicación
application = None

try:
    logger.info("🎯 Intentando cargar api_server_digitalocean...")
    from api_server_digitalocean import app as application
    logger.info("✅ api_server_digitalocean cargado exitosamente")
except ImportError as e:
    logger.warning(f"⚠️ Error cargando api_server_digitalocean: {e}")
    try:
        logger.info("🎯 Intentando cargar api_server_optimizado...")
        from api_server_optimizado import app as application
        logger.info("✅ api_server_optimizado cargado exitosamente")
    except ImportError as e2:
        logger.error(f"❌ Error cargando api_server_optimizado: {e2}")
        logger.info("🎯 Creando servidor mínimo de emergencia...")
        
        # Último recurso: servidor mínimo con Flask
        from flask import Flask, jsonify
        application = Flask(__name__)
        
        @application.route('/')
        def index():
            return jsonify({
                'status': 'emergency_server',
                'message': 'Servidor mínimo funcionando',
                'port': os.environ.get('PORT', '8080'),
                'error': f'Servidores principales no disponibles: {e}, {e2}'
            })
        
        @application.route('/health')
        def health():
            return jsonify({
                'status': 'healthy_minimal',
                'server': 'emergency'
            })
        
        @application.route('/api/propiedades')
        def propiedades():
            return jsonify({
                'propiedades': [],
                'mensaje': 'Servidor de emergencia - Sin datos disponibles'
            })
        
        logger.warning("⚠️ Servidor mínimo creado como último recurso")

if application is None:
    logger.error("❌ FALLO CRÍTICO: No se pudo crear ninguna aplicación")
    raise RuntimeError("No se pudo inicializar la aplicación")

logger.info("🚀 WSGI listo para servir")

# Para debugging en local
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    logger.info(f"🏃‍♂️ Ejecutando en modo local en puerto {port}")
    application.run(host='0.0.0.0', port=port, debug=False) 