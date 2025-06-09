#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏠 WSGI Ultra-Simple para DigitalOcean - GARANTIZADO
"""

import os
import sys

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Importar directamente el servidor de DigitalOcean
    from api_server_digitalocean import app as application
    print("✅ DigitalOcean server loaded successfully")
except ImportError:
    try:
        # Fallback al servidor optimizado
        from api_server_optimizado import app as application
        print("✅ Optimized server loaded as fallback")
    except ImportError:
        # Último recurso: servidor mínimo
        from flask import Flask, jsonify
        application = Flask(__name__)
        
        @application.route('/')
        def index():
            return jsonify({
                'status': 'minimal_server',
                'message': 'Basic server running',
                'port': os.environ.get('PORT', '8080')
            })
        
        @application.route('/health')
        def health():
            return jsonify({'status': 'healthy'})
        
        print("⚠️ Minimal server created as last resort")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    application.run(host='0.0.0.0', port=port) 